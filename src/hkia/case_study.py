"""Case study: Typhoon Noul at HKIA, 24-26 Jul 2026 — hour-by-hour data story + an in-sample model retrospective.

  python -m hkia.case_study [--db data/hkia.db] [--json web/public/data/case_noul.json] [--md reports/case-noul.md]
  python -m hkia.case_study --no-model      # skip the retrospective (no xgboost / models/ available)

**One-off artefact, regenerate by hand.** `web/public/data/case_noul.json` describes five fixed days in July 2026; it is
static history, so it is generated once locally and committed. The ingest cron does NOT write it (unlike the other files in
web/public/data/, which `hkia.export_json` rewrites every 30 min). Re-run this module only if the underlying rows change —
a weather backfill, a schema change, or a new model whose retrospective you want to refresh.

What it builds, from `flights` + `metar_hist` + `tc_signals`:
  hourly       Jul 23 00:00 -> Jul 27 23:00 HKT, one row per clock hour: TC signal in force, departures
               scheduled / departed / cancelled, mean + p90 delay, METAR wind / gust / visibility / flight category
  by_signal    totals per signal level (n, cancel rate, mean delay, % > 15 min) vs a non-typhoon baseline window
  worst        the 10 longest delays of the episode and the cancellation clusters by airline / destination
  recovery     how many hours after the last signal dropped until hourly mean delay came back to the baseline
  retrospective  the shipped model scored over the same flights.

  !! The retrospective is IN-SAMPLE. Live scoring only began 2026-08-17, so no prediction was ever published for these
  flights; 24-26 Jul sits inside the model's **validation** split (2026-07-20 .. 2026-08-02), which was used for early
  stopping and model selection. The numbers below are an illustration of what the model says about these hours, never a
  measurement of skill. Every consumer of this JSON must carry the flag (`retrospective.in_sample`) on the page itself.

Delay convention matches the rest of the repo: delay = actual - scheduled, rows outside [-60, 600] min are dropped from
the aggregates (`n_over_clip` counts them) but the worst-flights table shows them uncapped and flagged, because a 28-hour
delay is the story rather than an outlier.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .airlines import airline_name
from .airports import airport
from .db import DB_PATH, ROOT
from .features import DELAY_MAX, DELAY_MIN

log = logging.getLogger("hkia.case_study")
HKT = "Asia/Hong_Kong"

TC_ID = "202602"                       # HKO tropical-cyclone id of Noul
WINDOW_START = "2026-07-23 00:00"      # HKT, inclusive
WINDOW_END = "2026-07-28 00:00"        # HKT, exclusive (= Jul 27 24:00)
EPISODE_DAYS = ("2026-07-24", "2026-07-26")   # the days a Noul signal was in force
N_WORST = 10
N_CLUSTER = 8                          # rows in each cancellation-cluster table
FLAG_P = 0.5                           # "flagged" = P(delay > 15) above this
RECOVERY_MIN_N = 5                     # an hour needs this many departed flights to count as "recovered"
DEFAULT_JSON = ROOT / "web" / "public" / "data" / "case_noul.json"
DEFAULT_MD = ROOT / "reports" / "case-noul.md"

IN_SAMPLE_NOTE = (
    "In-sample. Live scoring began 2026-08-17, so no prediction was ever published for these flights. The model was "
    "re-run over them after the fact with the same feature builder, and 24-26 Jul falls inside its validation split "
    "(used for early stopping and model selection). Shown for illustration, never as a measurement of skill."
)


# ---------------------------------------------------------------- helpers
def _r(x, nd=1):
    """JSON-safe rounding: NaN/None -> None, numpy -> python."""
    if x is None:
        return None
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), nd)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def _s(v) -> str | None:
    """NaN / NaT / '' -> None, anything else -> str (sqlite NULLs arrive as NaN through pandas)."""
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return None
    s = str(v).strip()
    return s or None


def _hkt(ts) -> str | None:
    if ts is None or ts is pd.NaT or (isinstance(ts, float) and np.isnan(ts)):
        return None
    t = pd.Timestamp(ts)
    if pd.isna(t):
        return None
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return t.tz_convert(HKT).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


# ---------------------------------------------------------------- loading
def load_flights(conn, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Every departure row with HKT scheduled/actual timestamps, delay minutes and a cancelled flag.

    `start`/`end` are tz-aware HKT bounds on the *scheduled* time; None loads the whole table (used for the baseline).
    """
    df = pd.read_sql_query(
        "SELECT date, flight_no, airline, destination, scheduled_ts, actual_ts, status_raw FROM flights", conn)
    df["sched"] = pd.to_datetime(df["scheduled_ts"], utc=True).dt.tz_convert(HKT)
    df["actual"] = pd.to_datetime(df["actual_ts"], utc=True, errors="coerce").dt.tz_convert(HKT)
    df["delay_min"] = (df["actual"] - df["sched"]).dt.total_seconds() / 60
    df["cancelled"] = df["status_raw"].fillna("").str.strip().str.lower().eq("cancelled")
    df["dest"] = df["destination"].fillna("").str.split(",").str[0].str.strip()
    if start is not None:
        df = df[df["sched"] >= start]
    if end is not None:
        df = df[df["sched"] < end]
    return df.sort_values("sched").reset_index(drop=True)


def load_signals(conn, since: str = "2026-01-01") -> pd.DataFrame:
    """TC signal episodes (the `tc_signals` table also holds HKO's archive back to 1946 — always filter)."""
    tc = pd.read_sql_query(
        "SELECT tc_id, tc_name, signal, direction, start_ts, end_ts FROM tc_signals WHERE start_ts >= ? ORDER BY start_ts",
        conn, params=(since,))
    tc["start"] = pd.to_datetime(tc["start_ts"], utc=True).dt.tz_convert(HKT)
    tc["end"] = pd.to_datetime(tc["end_ts"], utc=True).dt.tz_convert(HKT)
    tc["level"] = pd.to_numeric(tc["signal"], errors="coerce").fillna(0).astype(int)  # "MSN" -> 0
    return tc


def load_metar(conn, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Hourly routine VHHH observations over the window (IEM archive table), indexed by HKT clock hour."""
    m = pd.read_sql_query(
        "SELECT report_time, wspd_kt, wgst_kt, visib_sm, ceiling_ft, flt_cat, wx_string FROM metar_hist "
        "WHERE report_time >= ? AND report_time < ? ORDER BY report_time",
        conn, params=(start.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                      end.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")))
    if m.empty:
        return m.assign(hour=pd.Series(dtype="datetime64[ns, Asia/Hong_Kong]"))
    m["hour"] = pd.to_datetime(m["report_time"], utc=True, format="ISO8601").dt.tz_convert(HKT).dt.floor("h")
    for c in ("wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft"):
        m[c] = pd.to_numeric(m[c], errors="coerce")
    return m.drop_duplicates("hour", keep="last").reset_index(drop=True)


# ---------------------------------------------------------------- signal join
def signal_at(times: pd.Series, tc: pd.DataFrame) -> pd.Series:
    """Highest TC signal in force at each timestamp (0 = none). Half-open intervals [start, end), like hkia.features."""
    out = pd.Series(0, index=times.index, dtype=int)
    for r in tc.itertuples(index=False):
        if r.level <= 0:
            continue                                   # "MSN" strong-monsoon rows are not a TC signal
        active = (times >= r.start) & (times < r.end)
        if active.any():
            out[active] = np.maximum(out[active], r.level)
    return out


def hour_index(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="h", inclusive="left", tz=HKT)


def hourly_timeline(flights: pd.DataFrame, metar: pd.DataFrame, tc: pd.DataFrame,
                    start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """One row per clock hour of [start, end): signal, counts, delay stats, weather.

    Bucketing is by *scheduled* hour — the question is "what happened to the flights that were meant to leave then",
    and the schedule is the one thing that is known in advance. Hours with no scheduled departure survive as zero rows
    so the chart shows the shutdown as a gap rather than closing over it.
    """
    idx = hour_index(start, end)
    f = flights[(flights["sched"] >= start) & (flights["sched"] < end)].copy()
    f["hour"] = f["sched"].dt.floor("h")
    ok = f["delay_min"].between(DELAY_MIN, DELAY_MAX)
    f["delay_clipped"] = f["delay_min"].where(ok)

    g = f.groupby("hour")
    out = pd.DataFrame(index=idx)
    out.index.name = "hour"
    out["n_sched"] = g.size().reindex(idx).fillna(0).astype(int)
    out["n_departed"] = g["actual"].count().reindex(idx).fillna(0).astype(int)
    out["n_cancelled"] = g["cancelled"].sum().reindex(idx).fillna(0).astype(int)
    out["n_labelled"] = g["delay_clipped"].count().reindex(idx).fillna(0).astype(int)
    out["mean_delay"] = g["delay_clipped"].mean().reindex(idx)
    out["p90_delay"] = g["delay_clipped"].quantile(0.9).reindex(idx)
    out["max_delay"] = g["delay_min"].max().reindex(idx)
    out["signal"] = signal_at(pd.Series(idx, index=idx), tc)

    if not metar.empty:
        w = metar.set_index("hour").reindex(idx)
        for c in ("wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "flt_cat", "wx_string"):
            out[c] = w[c]
        out["wgst_kt"] = out["wgst_kt"].fillna(0)       # METAR omits the gust group when there is no gust
    else:
        for c in ("wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "flt_cat", "wx_string"):
            out[c] = np.nan
    return out.reset_index()


# ---------------------------------------------------------------- aggregates
def _totals(f: pd.DataFrame) -> dict:
    ok = f["delay_min"].between(DELAY_MIN, DELAY_MAX)
    d = f.loc[ok, "delay_min"]
    return {
        "n": int(len(f)),
        "n_cancelled": int(f["cancelled"].sum()),
        "cancel_rate": _r(f["cancelled"].mean(), 4) if len(f) else None,
        "n_labelled": int(len(d)),
        "n_over_clip": int((f["delay_min"] > DELAY_MAX).sum()),
        "mean_delay": _r(d.mean()),
        "median_delay": _r(d.median()),
        "p90_delay": _r(d.quantile(0.9)),
        "pct15": _r((d > 15).mean(), 4) if len(d) else None,
    }


def by_signal(flights: pd.DataFrame, tc: pd.DataFrame) -> list[dict]:
    """Totals per TC signal level in force at the *scheduled* time, over the case-study window."""
    f = flights.copy()
    f["signal"] = signal_at(f["sched"], tc)
    return [{"signal": int(s), **_totals(g)} for s, g in f.groupby("signal", sort=True)]


def baseline(all_flights: pd.DataFrame, tc: pd.DataFrame) -> dict:
    """The comparison group: every departure in the db scheduled with no TC signal in force."""
    f = all_flights.copy()
    f["signal"] = signal_at(f["sched"], tc)
    q = f[f["signal"] == 0]
    return {"label": "no TC signal in force", "date_min": q["date"].min(), "date_max": q["date"].max(),
            "n_days": int(q["date"].nunique()), **_totals(q)}


def worst_flights(flights: pd.DataFrame, tc: pd.DataFrame, n: int = N_WORST) -> list[dict]:
    """Longest actual delays of the episode, uncapped (the flights beyond the [-60, 600] clip are the point)."""
    f = flights[flights["delay_min"].notna()].copy()
    f["signal"] = signal_at(f["sched"], tc)
    rows = []
    for r in f.nlargest(n, "delay_min").itertuples(index=False):
        city, _ = airport(r.dest)
        rows.append({"flight_no": r.flight_no, "airline": r.airline, "airline_name": airline_name(r.airline),
                     "dest": r.dest, "dest_city": city, "sched_ts": _hkt(r.sched), "actual_ts": _hkt(r.actual),
                     "delay_min": _r(r.delay_min, 0), "signal": int(r.signal),
                     "over_clip": bool(r.delay_min > DELAY_MAX)})
    return rows


def cancellations(flights: pd.DataFrame, n: int = N_CLUSTER) -> dict:
    """Who lost flights: clusters by operating airline and by destination, plus the per-day totals."""
    c = flights[flights["cancelled"]]
    by_air, by_dest = [], []
    if len(c):
        a = c.groupby("airline").size().sort_values(ascending=False).head(n)
        sched_a = flights.groupby("airline").size()
        by_air = [{"airline": k, "name": airline_name(k), "n_cancelled": int(v), "n_sched": int(sched_a.get(k, 0)),
                   "rate": _r(v / sched_a.get(k, np.nan), 3)} for k, v in a.items()]
        d = c.groupby("dest").size().sort_values(ascending=False).head(n)
        by_dest = [{"dest": k, "city": airport(k)[0], "n_cancelled": int(v)} for k, v in d.items()]
    day = flights.groupby("date").agg(n_sched=("flight_no", "size"), n_cancelled=("cancelled", "sum")).reset_index()
    day["rate"] = day["n_cancelled"] / day["n_sched"]
    return {
        "total": int(flights["cancelled"].sum()),
        "by_airline": by_air, "by_dest": by_dest,
        "by_day": [{"date": r.date, "n_sched": int(r.n_sched), "n_cancelled": int(r.n_cancelled), "rate": _r(r.rate, 3)}
                   for r in day.itertuples(index=False)],
    }


def recovery(hourly: pd.DataFrame, tc: pd.DataFrame, baseline_mean: float,
             min_n: int = RECOVERY_MIN_N) -> dict:
    """Hours between the last signal being lowered and the first hour back at the no-signal baseline.

    Rule: after the all-clear, the first clock hour with at least `min_n` departed flights whose mean delay is at or
    below the no-signal baseline mean. Requiring a busy hour matters — a 03:00 hour with one on-time flight is not a
    recovered airport. `hours_to_recover` is None when the window ends before that happens.
    """
    ep = tc[(tc["level"] > 0) & (tc["tc_id"] == TC_ID)]
    if ep.empty or baseline_mean is None or not np.isfinite(baseline_mean):
        return {"all_clear_ts": None, "recovered_at": None, "hours_to_recover": None,
                "baseline_mean_delay": _r(baseline_mean), "min_n": min_n}
    all_clear = ep["end"].max()
    after = hourly[(hourly["hour"] >= all_clear.floor("h")) & (hourly["n_departed"] >= min_n)
                   & hourly["mean_delay"].notna()]
    hit = after[after["mean_delay"] <= baseline_mean]
    rec = hit["hour"].iloc[0] if len(hit) else None
    return {
        "all_clear_ts": _hkt(all_clear),
        "recovered_at": _hkt(rec),
        "hours_to_recover": _r((rec - all_clear).total_seconds() / 3600, 1) if rec is not None else None,
        "baseline_mean_delay": _r(baseline_mean),
        "min_n": min_n,
        "rule": f"first clock hour after the all-clear with >= {min_n} departed flights whose mean delay is at or below "
                f"the no-signal baseline ({_r(baseline_mean)} min)",
    }


# ---------------------------------------------------------------- retrospective (in-sample)
def retrospective(conn, window: tuple[pd.Timestamp, pd.Timestamp], models_dir: Path) -> dict | None:
    """Score the episode's flights with the shipped model and the shipped feature builder. IN-SAMPLE — see the note.

    Returns None (with a log line) if the model artefacts or xgboost are unavailable, so `--no-model` and a machine
    without requirements-ml.txt both still produce the data half of the case study.
    """
    try:
        from sklearn.metrics import roc_auc_score

        from .features import build_features, load_flights as feat_flights, load_metar as feat_metar, load_tc_signals
        from .predict import load_models
        from .train import to_matrix
    except ImportError as e:
        log.warning("retrospective skipped (imports): %s", e)
        return None
    try:
        models = load_models(models_dir)
    except (FileNotFoundError, OSError, ValueError) as e:
        log.warning("retrospective skipped (models): %s", e)
        return None

    clf, reg, man = models["clf"], models["reg"], models["manifest"]
    # the whole flights table, so congestion + point-in-time rolling features see the same history as at training time
    feat, _ = build_features(feat_flights(conn), feat_metar(conn), load_tc_signals(conn),
                             top_dest=set(clf["cats"]["dest"].categories) - {"OTHER"})
    sched = feat["scheduled_ts"].dt.tz_convert(HKT)
    sel = (sched >= window[0]) & (sched < window[1]) & (feat["cancelled"] == 0) & feat["delay_min"].notna()
    w = feat.loc[sel].reset_index(drop=True)
    if w.empty:
        log.warning("retrospective skipped: no scorable flights in the window")
        return None

    X, _ = to_matrix(w, clf["cats"], clf["features"])
    w["p"] = clf["model"].predict_proba(X)[:, 1]
    Xr, _ = to_matrix(w, reg["cats"], reg["features"])
    w["pred_min"] = reg["model"].predict(Xr)
    w["y"] = (w["delay_min"] > 15).astype(int)

    def block(g: pd.DataFrame) -> dict:
        return {
            "n": int(len(g)),
            "obs_rate": _r(g["y"].mean(), 4),
            "mean_p": _r(g["p"].mean(), 4),
            "pct_flagged": _r((g["p"] > FLAG_P).mean(), 4),
            "auc": _r(roc_auc_score(g["y"], g["p"]), 4) if g["y"].nunique() > 1 else None,
            "brier": _r(np.mean((g["p"] - g["y"]) ** 2), 4),
            "mae": _r(np.abs(g["pred_min"] - g["delay_min"]).mean()),
            "mean_pred_delay": _r(g["pred_min"].mean()),
            "mean_obs_delay": _r(g["delay_min"].mean()),
        }

    split = (man.get("split") or {})
    val = split.get("val", {})
    return {
        "in_sample": True,
        "split_containing_episode": "val",
        "split_dates": {k: [v.get("date_min"), v.get("date_max")] for k, v in split.items()},
        "val_dates": [val.get("date_min"), val.get("date_max")],
        "model_version": models["version"],
        "live_scoring_began": "2026-08-17",
        "flag_threshold": FLAG_P,
        "note": IN_SAMPLE_NOTE,
        "overall": block(w),
        "by_signal": [{"signal": int(s), **block(g)} for s, g in w.groupby("tc_signal", sort=True)],
        "hourly": [{"t": _hkt(h), "n": int(len(g)), "mean_p": _r(g["p"].mean(), 4),
                    "mean_pred_delay": _r(g["pred_min"].mean()), "mean_obs_delay": _r(g["delay_min"].mean())}
                   for h, g in w.groupby(w["scheduled_ts"].dt.tz_convert(HKT).dt.floor("h"), sort=True)],
    }


# ---------------------------------------------------------------- assembly
def _episode_signals(tc: pd.DataFrame) -> list[dict]:
    ep = tc[(tc["tc_id"] == TC_ID) & (tc["level"] > 0)].sort_values("start")
    return [{"signal": int(r.level), "direction": _s(r.direction), "start": _hkt(r.start), "end": _hkt(r.end),
             "hours": _r((r.end - r.start).total_seconds() / 3600, 1)} for r in ep.itertuples(index=False)]


def _other_episodes(tc: pd.DataFrame, flights_min: str, flights_max: str) -> list[dict]:
    """Everything else HKO hoisted inside the flight-data window — mentioned so the page does not imply Noul was alone."""
    out = []
    for (tid, name), g in tc[tc["tc_id"] != TC_ID].groupby(["tc_id", "tc_name"], dropna=False, sort=False):
        s, e = g["start"].min(), g["end"].max()
        if e.strftime("%Y-%m-%d") < flights_min or s.strftime("%Y-%m-%d") > flights_max:
            continue
        lv = int(g["level"].max())
        out.append({"tc_id": tid, "name": _s(name) if lv > 0 else "Strong monsoon signal",
                    "peak_signal": lv, "start": _hkt(s), "end": _hkt(e),
                    "kind": "tc" if lv > 0 else "monsoon"})
    return sorted(out, key=lambda x: x["start"])


def build(conn, now: dt.datetime | None = None, models_dir: Path = ROOT / "models",
          with_model: bool = True) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    start = pd.Timestamp(WINDOW_START, tz=HKT)
    end = pd.Timestamp(WINDOW_END, tz=HKT)

    tc = load_signals(conn)
    all_flights = load_flights(conn)
    win = all_flights[(all_flights["sched"] >= start) & (all_flights["sched"] < end)].reset_index(drop=True)
    metar = load_metar(conn, start, end)
    hourly = hourly_timeline(win, metar, tc, start, end)
    base = baseline(all_flights, tc)

    ep_rows = _episode_signals(tc)
    peak = max((r["signal"] for r in ep_rows), default=0)
    ep_flights = win[win["date"].between(*EPISODE_DAYS)]
    busy = hourly[hourly["n_labelled"] >= 3]
    pk = busy.loc[busy["mean_delay"].idxmax()] if len(busy) and busy["mean_delay"].notna().any() else None
    rec = recovery(hourly, tc, base["mean_delay"])

    retro = retrospective(conn, (start, end), models_dir) if with_model else None
    if with_model and retro is None:
        log.warning("no retrospective in the output (model artefacts unavailable)")

    doc = {
        "generated_at": _hkt(now),
        "regenerate": "python -m hkia.case_study",
        "static": True,
        "note": "One-off artefact describing five fixed days in July 2026. Not written by the ingest cron.",
        "episode": {
            "tc_id": TC_ID, "name": "NOUL", "peak_signal": peak,
            "first_signal": ep_rows[0]["start"] if ep_rows else None,
            "all_clear": ep_rows[-1]["end"] if ep_rows else None,
            "sequence": "→".join(f"T{r['signal']}" for r in ep_rows),
            "signals": ep_rows,
        },
        "window": {"start": _hkt(start), "end": _hkt(end), "tz": HKT,
                   "days": sorted(win["date"].unique().tolist())},
        "other_episodes": _other_episodes(tc, all_flights["date"].min(), all_flights["date"].max()),
        "headline": {
            "peak_signal": peak,
            "n_flights_window": int(len(win)),
            "n_flights_episode": int(len(ep_flights)),
            "n_cancelled_episode": int(ep_flights["cancelled"].sum()),
            "cancel_rate_episode": _r(ep_flights["cancelled"].mean(), 4) if len(ep_flights) else None,
            "peak_hour": _hkt(pk["hour"]) if pk is not None else None,
            "peak_hour_mean_delay": _r(pk["mean_delay"]) if pk is not None else None,
            "peak_hour_n": int(pk["n_labelled"]) if pk is not None else None,
            "peak_gust_kt": _r(hourly["wgst_kt"].max(), 0),
            "min_visib_sm": _r(hourly["visib_sm"].min(), 2),
            "hours_to_recover": rec["hours_to_recover"],
            "n_hours_no_departures": int((hourly["n_departed"] == 0).sum()),
        },
        "hourly": [
            {"t": _hkt(r.hour), "signal": int(r.signal), "n_sched": int(r.n_sched), "n_departed": int(r.n_departed),
             "n_cancelled": int(r.n_cancelled), "n_labelled": int(r.n_labelled),
             "mean_delay": _r(r.mean_delay), "p90_delay": _r(r.p90_delay), "max_delay": _r(r.max_delay, 0),
             "wspd_kt": _r(r.wspd_kt, 0), "wgst_kt": _r(r.wgst_kt, 0), "visib_sm": _r(r.visib_sm, 2),
             "flt_cat": None if pd.isna(r.flt_cat) else str(r.flt_cat),
             "wx": None if pd.isna(r.wx_string) else str(r.wx_string)}
            for r in hourly.itertuples(index=False)
        ],
        "by_signal": by_signal(win, tc),
        "baseline": base,
        "worst_flights": worst_flights(win, tc),
        "cancellations": cancellations(win),
        "recovery": rec,
        "retrospective": retro,
        "clip": {"min": DELAY_MIN, "max": DELAY_MAX,
                 "note": f"delays outside [{DELAY_MIN}, {DELAY_MAX}] min are excluded from every average (same rule as "
                         "the training set); the worst-flights table shows them uncapped and flagged"},
        "sources": {"flights": "data.gov.hk / Airport Authority HK flight information API",
                    "weather": "Iowa State IEM ASOS archive, VHHH hourly METAR",
                    "signals": "Hong Kong Observatory tropical-cyclone warning database"},
    }
    return doc


# ---------------------------------------------------------------- markdown
def _md_table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def _f(v, nd=1, suffix=""):
    return "—" if v is None else f"{v:.{nd}f}{suffix}"


def _p(v):
    return "—" if v is None else f"{v * 100:.1f}%"


def _hm(ts: str | None) -> str:
    """'2026-07-26T19:10:00+08:00' -> '2026-07-26 19:10'."""
    return "—" if not ts else ts[:16].replace("T", " ")


def _recovery_md(rec: dict, h: dict) -> str:
    if rec["recovered_at"]:
        back = f"{_hm(rec['recovered_at'])} HKT, **{rec['hours_to_recover']:.0f} hours later**"
    else:
        back = "not reached inside the window"
    return (f"All-clear at {_hm(rec['all_clear_ts'])} HKT. {rec['rule'][0].upper() + rec['rule'][1:]} — {back}. "
            f"{h['n_hours_no_departures']} clock hours in the window saw no departure at all.")


def to_markdown(d: dict) -> str:
    e, h, b, rec = d["episode"], d["headline"], d["baseline"], d["recovery"]
    L = [f"# Case study — Typhoon {e['name'].title()} at HKIA, {e['first_signal'][:10]} → {e['all_clear'][:10]}", "",
         f"Generated by `python -m hkia.case_study` at {d['generated_at']}. One-off artefact — the ingest cron does not "
         "rewrite it.", "",
         f"Signal sequence **{e['sequence']}**, peak **signal {e['peak_signal']}**. "
         f"{h['n_flights_episode']:,} departures were scheduled over the three signal days; "
         f"**{h['n_cancelled_episode']:,} were cancelled** ({_p(h['cancel_rate_episode'])}). "
         f"The worst hour, {h['peak_hour'][:16].replace('T', ' ')} HKT, averaged **{_f(h['peak_hour_mean_delay'], 0, ' min')}** "
         f"of delay over {h['peak_hour_n']} flights. Peak gust {_f(h['peak_gust_kt'], 0, ' kt')}, "
         f"lowest visibility {_f(h['min_visib_sm'], 2, ' sm')}.", "",
         "## Signal sequence", "",
         _md_table(["signal", "from (HKT)", "to (HKT)", "hours"],
                   [[f"T{s['signal']}" + (f" {s['direction']}" if s['direction'] else ""),
                     s["start"][:16].replace("T", " "), s["end"][:16].replace("T", " "), _f(s["hours"])]
                    for s in e["signals"]]), "",
         "## Totals by signal level in force at the scheduled time", "",
         "Rows are the case-study window only (Jul 23 → 27), so the `none` row is mostly the recovery hours after the "
         "all-clear rather than a normal day — that is why it sits above the baseline underneath it.", "",
         _md_table(["signal", "flights", "cancelled", "cancel rate", "mean delay", "p90", "> 15 min"],
                   [[f"T{r['signal']}" if r["signal"] else "none", f"{r['n']:,}", r["n_cancelled"],
                     _p(r["cancel_rate"]), _f(r["mean_delay"], 1, " min"), _f(r["p90_delay"], 0, " min"), _p(r["pct15"])]
                    for r in d["by_signal"]]
                  + [["**baseline**", f"{b['n']:,}", b["n_cancelled"], _p(b["cancel_rate"]),
                      _f(b["mean_delay"], 1, " min"), _f(b["p90_delay"], 0, " min"), _p(b["pct15"])]]), "",
         f"Baseline = every departure in the database scheduled with no TC signal in force "
         f"({b['n_days']} days, {b['date_min']} → {b['date_max']}).", "",
         "## Recovery", "", _recovery_md(rec, h), "",
         "## Cancellation clusters", "",
         _md_table(["airline", "cancelled", "scheduled", "rate"],
                   [[f"{r['name']} ({r['airline']})", r["n_cancelled"], r["n_sched"], _p(r["rate"])]
                    for r in d["cancellations"]["by_airline"]]), "",
         "## Worst 10 delays", "",
         _md_table(["flight", "airline", "to", "scheduled (HKT)", "actual (HKT)", "delay", "signal"],
                   [[r["flight_no"], r["airline_name"], f"{r['dest_city']} ({r['dest']})",
                     r["sched_ts"][:16].replace("T", " "), r["actual_ts"][:16].replace("T", " "),
                     f"{r['delay_min']:.0f} min" + (" ⚠" if r["over_clip"] else ""), f"T{r['signal']}" if r["signal"] else "none"]
                    for r in d["worst_flights"]]), "",
         "⚠ = beyond the [-60, 600] min clip used for every average in this repo; excluded from the aggregates above.", ""]

    r = d.get("retrospective")
    if r:
        o = r["overall"]
        L += ["## Model retrospective — IN-SAMPLE, illustration only", "",
              f"> {r['note']}", "",
              f"Model `{r['model_version']}`; validation split {r['val_dates'][0]} → {r['val_dates'][1]} contains the "
              f"episode. Scored {o['n']:,} departed flights of the window.", "",
              _md_table(["slice", "n", "observed > 15 min", "mean P", "% flagged (P > 0.5)", "AUC", "Brier",
                         "mean predicted delay", "mean observed delay"],
                        [["all", f"{o['n']:,}", _p(o["obs_rate"]), _f(o["mean_p"], 3), _p(o["pct_flagged"]),
                          _f(o["auc"], 3), _f(o["brier"], 3), _f(o["mean_pred_delay"], 0, " min"),
                          _f(o["mean_obs_delay"], 0, " min")]]
                       + [[f"T{s['signal']}" if s["signal"] else "no signal", f"{s['n']:,}", _p(s["obs_rate"]),
                           _f(s["mean_p"], 3), _p(s["pct_flagged"]), _f(s["auc"], 3), _f(s["brier"], 3),
                           _f(s["mean_pred_delay"], 0, " min"), _f(s["mean_obs_delay"], 0, " min")]
                          for s in r["by_signal"]]), "",
              "Read the last two columns together: the ranking holds up, the magnitude does not. Even with the episode "
              "inside its own validation split, the regression head stays close to a normal day while the airport was "
              "hours behind.", ""]
    else:
        L += ["## Model retrospective", "", "Not generated (model artefacts unavailable at build time).", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- main
def write(doc: dict, json_path: Path, md_path: Path) -> dict[str, int]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(doc, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    json_path.write_text(txt)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md = to_markdown(doc)
    md_path.write_text(md)
    return {str(json_path): len(txt.encode()), str(md_path): len(md.encode())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--models", type=Path, default=ROOT / "models")
    ap.add_argument("--no-model", action="store_true", help="skip the in-sample retrospective")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stdout)
    if not a.db.exists():
        log.error("db not found: %s", a.db)
        return 1
    with _ro(a.db) as conn:
        doc = build(conn, models_dir=a.models, with_model=not a.no_model)
    sizes = write(doc, a.json, a.md)
    for k, v in sizes.items():
        log.info("wrote %-40s %6.1f KB", k, v / 1024)
    if sizes[str(a.json)] > 60_000:
        log.warning("case_noul.json is %.0f KB (> 60 KB target)", sizes[str(a.json)] / 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
