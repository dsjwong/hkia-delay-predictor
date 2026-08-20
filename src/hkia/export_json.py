"""Export compact JSON snapshots of the db + model artefacts for the static web app (web/public/data/).

  python -m hkia.export_json [--out web/public/data] [--db data/hkia.db]

Written files (all < 1 MB together; gzip is handled by GitHub Pages):
  meta.json                  data_as_of (last ingest), last_score, last_metar, model_version, counts, airline names,
                             IATA->ICAO map (from the db), airport city/country map
  departures_yesterday.json  \\
  departures_today.json       > one HKT day each: every flight with its latest prediction (+ a short prediction history
                             for today/tomorrow as [epoch_s, p, pred_min] triples, and for not-yet-departed flights a
                             `why` array of the top-3 attributions as [direction, one-liner, probability points] rendered
  departures_tomorrow.json   /  from table `explanations` by hkia.explain); names/cities resolve through meta.json
  patterns.json              91-day hour x weekday heatmap, airline table (n >= 50), top-25 destinations, daily series with
                             TC-signal flags, typhoon-day stats, by-hour share for the top-4 airlines
  model.json                 M2 metrics, calibration bins, feature importance, ablation, live evaluation, interpretation,
                             limitations
  weather.json               latest METAR (parsed + raw), HKO warnings, active TC signal

Run by the ingest cron after `hkia.predict` (and by the daily backfill after `hkia.evaluate`); the JSON is committed with the db.
Reads only; never scores. Mirrors the queries of app/data.py so the Streamlit app and the web app show the same numbers.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import explain
from .airlines import AIRLINE_NAMES, IATA_TO_ICAO, airline_name
from .airports import airport, known
from .db import DB_PATH, ROOT
from .evaluate import MIN_N, compute as live_eval_compute

log = logging.getLogger("hkia.export_json")
HKT = dt.timezone(dt.timedelta(hours=8))
HKT_TZ = "Asia/Hong_Kong"
DELAY_MIN, DELAY_MAX = -60, 600  # same outlier clip as hkia.features
HISTORY_DAYS = 91
MAX_PRED_HISTORY = 10            # per flight: first score + the latest 9 (the table keeps ~1/hour); [epoch_s, p, pred_min]
DEFAULT_OUT = ROOT / "web" / "public" / "data"

LIMITATIONS = [
    "Weather = latest observation, not a forecast. Every future flight is scored with the most recent VHHH METAR "
    "(persistence, capped at 3 h of age). A storm forecast for the evening does not move the morning's numbers.",
    "Departures only, no arrivals, no ADS-B in the model. The single strongest real-world predictor, the inbound aircraft "
    "running late, is not a feature yet (the live map shows ADS-B but does not feed the model).",
    "Rolling 91-day window, one season. The data.gov.hk API keeps ~91 days; the training set (May-Aug 2026) has one typhoon "
    "(Noul, 25-26 Jul) in the validation split, so typhoon effects are learned from a handful of days and unconfirmed on test.",
    "Survivorship / churn. Cancelled flights are excluded from the delay label; the schedule for tomorrow can still change.",
    "Staleness. Predictions come from a 30-min cron; between runs they can be up to 30 min old (see 'data as of').",
]


# ---------------------------------------------------------------- helpers
def _conn(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _has(c: sqlite3.Connection, table: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _q(c: sqlite3.Connection, sql: str, params=()) -> pd.DataFrame:
    return pd.read_sql_query(sql, c, params=params)


def _r(x, nd=3):
    """JSON-safe rounding: NaN/None -> None, numpy -> python."""
    if x is None:
        return None
    try:
        if isinstance(x, (float, np.floating)):
            return None if np.isnan(x) else round(float(x), nd)
        if isinstance(x, (np.integer,)):
            return int(x)
    except TypeError:
        pass
    return x


def _iso(ts) -> str | None:
    if ts is None or (isinstance(ts, float) and np.isnan(ts)) or ts is pd.NaT:
        return None
    try:
        t = pd.Timestamp(ts)
    except (ValueError, TypeError):
        return None
    if pd.isna(t):
        return None
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return t.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    path.write_text(txt)
    return len(txt.encode())


# ---------------------------------------------------------------- departures
LATEST_PRED = """
SELECT p.flight_no, p.scheduled_ts, p.p_delay15, p.pred_delay_min, p.scored_at
FROM predictions p
WHERE p.date = ? AND p.scored_at = (SELECT MAX(scored_at) FROM predictions q
                                   WHERE q.date=p.date AND q.flight_no=p.flight_no AND q.scheduled_ts=p.scheduled_ts)
"""


def departures(c: sqlite3.Connection, date: str, with_history: bool) -> dict:
    fl = _q(c, "SELECT flight_no, scheduled_ts, airline, destination, codeshares, terminal, gate, status_raw, estimated_ts, "
               "actual_ts FROM flights WHERE date=? ORDER BY scheduled_ts, flight_no", (date,))
    out = {"date": date, "n": int(len(fl)), "flights": []}
    if fl.empty:
        return out
    has_pred = _has(c, "predictions")
    why = explain.load(c, date)   # (flight_no, scheduled_ts) -> top-3 attributions of the latest score
    pr = _q(c, LATEST_PRED, (date,)) if has_pred else pd.DataFrame(columns=["flight_no", "scheduled_ts", "p_delay15", "pred_delay_min", "scored_at"])
    df = fl.merge(pr, on=["flight_no", "scheduled_ts"], how="left")
    hist: dict[tuple[str, str], list] = {}
    if with_history and has_pred:
        h = _q(c, "SELECT flight_no, scheduled_ts, p_delay15, pred_delay_min, scored_at FROM predictions WHERE date=? "
                  "ORDER BY flight_no, scheduled_ts, scored_at", (date,))
        for (fn, st), g in h.groupby(["flight_no", "scheduled_ts"], sort=False):
            rows = [[int(pd.Timestamp(r.scored_at).timestamp()), _r(r.p_delay15), _r(r.pred_delay_min, 1)] for r in g.itertuples(index=False)]
            if len(rows) > MAX_PRED_HISTORY:
                rows = rows[:1] + rows[-(MAX_PRED_HISTORY - 1):]
            hist[(fn, st)] = rows
    sched = pd.to_datetime(df["scheduled_ts"], utc=True)
    actual = pd.to_datetime(df["actual_ts"], utc=True, errors="coerce")
    delay = ((actual - sched).dt.total_seconds() / 60).round(0)
    cancelled = df["status_raw"].fillna("").str.strip().str.lower().eq("cancelled")
    status = np.where(cancelled, "cancelled", np.where(df["actual_ts"].notna(), "departed", "scheduled"))
    df = df.astype(object).where(pd.notna(df), None)  # NaN -> None for the string columns
    for i, r in enumerate(df.itertuples(index=False)):
        dest = (r.destination or "").split(",")[0].strip()
        d = {  # airline name / destination city come from meta.json (airlines, airports) to keep this file small
            "flight_no": r.flight_no, "airline": r.airline, "dest": dest,
            "sched_ts": _iso(r.scheduled_ts), "est_ts": _iso(r.estimated_ts), "actual_ts": _iso(r.actual_ts),
            "status": str(status[i]), "terminal": r.terminal, "gate": r.gate, "codeshares": r.codeshares or None,
            "delay_min": _r(delay.iloc[i], 0),
            "p": _r(r.p_delay15), "pred_min": _r(r.pred_delay_min, 1), "scored_at": _iso(r.scored_at),
        }
        if r.destination and "," in r.destination:
            d["dest_all"] = r.destination
        # "why this prediction": top-3 local SHAP attributions as [direction, one-liner, probability points].
        # Only for flights that have not left yet — that is what the block is for, and it keeps the file small.
        w = why.get((r.flight_no, r.scheduled_ts)) if d["status"] == "scheduled" else None
        if w:
            d["why"] = explain.compact(w)
        hh = hist.get((r.flight_no, r.scheduled_ts))
        if hh:
            d["history"] = hh
        out["flights"].append(d)
    return out


# ---------------------------------------------------------------- patterns
def history_frame(c: sqlite3.Connection, now: dt.datetime, days: int = HISTORY_DAYS) -> pd.DataFrame:
    since = (now.astimezone(HKT).date() - dt.timedelta(days=days)).isoformat()
    df = _q(c, "SELECT date, flight_no, scheduled_ts, actual_ts, airline, destination FROM flights "
               "WHERE actual_ts IS NOT NULL AND date >= ? AND LOWER(TRIM(COALESCE(status_raw,''))) != 'cancelled'", (since,))
    if df.empty:
        return df
    sched = pd.to_datetime(df["scheduled_ts"], utc=True).dt.tz_convert(HKT_TZ)
    actual = pd.to_datetime(df["actual_ts"], utc=True).dt.tz_convert(HKT_TZ)
    df["delay_min"] = (actual - sched).dt.total_seconds() / 60
    df = df[(df["delay_min"] >= DELAY_MIN) & (df["delay_min"] <= DELAY_MAX)].copy()
    df["delayed15"] = (df["delay_min"] > 15).astype(int)
    df["hour"] = sched.loc[df.index].dt.hour
    df["dow"] = sched.loc[df.index].dt.dayofweek
    df["dest1"] = df["destination"].fillna("").str.split(",").str[0]
    return df


def typhoon_days(c: sqlite3.Connection, h: pd.DataFrame) -> pd.DataFrame:
    per_day = h.groupby("date").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    per_day["signal"] = 0
    per_day["tc_name"] = None
    if _has(c, "tc_signals"):
        tc = _q(c, "SELECT tc_name, signal, start_ts, end_ts FROM tc_signals WHERE signal IN ('1','3','8','9','10') "
                   "AND end_ts >= ? ORDER BY start_ts", (h["date"].min(),))
        for r in tc.itertuples(index=False):
            d0 = pd.Timestamp(r.start_ts).tz_convert(HKT_TZ).date()
            d1 = pd.Timestamp(r.end_ts).tz_convert(HKT_TZ).date()
            for d in pd.date_range(d0, d1, freq="D").date:
                m = per_day["date"] == d.isoformat()
                per_day.loc[m, "signal"] = np.maximum(per_day.loc[m, "signal"], int(r.signal))
                per_day.loc[m, "tc_name"] = r.tc_name
    return per_day


def _grid(h: pd.DataFrame, col: str, nd: int) -> list[list]:
    g = h.pivot_table(index="dow", columns="hour", values=col, aggfunc="mean").reindex(index=range(7), columns=range(24))
    return [[_r(v, nd) for v in row] for row in g.to_numpy()]


def patterns(c: sqlite3.Connection, now: dt.datetime) -> dict:
    h = history_frame(c, now)
    if h.empty:
        return {"summary": None}
    cnt = h.pivot_table(index="dow", columns="hour", values="delay_min", aggfunc="size").reindex(index=range(7), columns=range(24)).fillna(0)
    a = h.groupby("airline").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    a = a[a["n"] >= 50].sort_values("pct15", ascending=False)
    d = h.groupby("dest1").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    d = d.sort_values("n", ascending=False).head(25)
    td = typhoon_days(c, h)
    top4 = h.groupby("airline").size().sort_values(ascending=False).head(4).index.tolist()
    by_hour = {}
    for al in top4:
        s = h[h["airline"] == al].groupby("hour").agg(p=("delayed15", "mean"), n=("delayed15", "size")).reindex(range(24))
        by_hour[al] = {"name": airline_name(al), "pct15": [_r(v) for v in s["p"]], "n": [int(0 if np.isnan(v) else v) for v in s["n"]]}
    sig, no = td[td["signal"] > 0], td[td["signal"] == 0]
    s8 = sig[sig["signal"] >= 8]
    typhoon = None
    if len(sig):
        typhoon = {
            "n_days": int(len(sig)), "n_other": int(len(no)),
            "mean_delay": _r(sig["mean_delay"].mean(), 1), "pct15": _r(sig["pct15"].mean()),
            "mean_delay_other": _r(no["mean_delay"].mean(), 1), "pct15_other": _r(no["pct15"].mean()),
            "names": sorted({str(n) for n in sig["tc_name"].dropna()}),
            "days": [{"date": r.date, "signal": int(r.signal), "tc_name": r.tc_name, "mean_delay": _r(r.mean_delay, 1), "pct15": _r(r.pct15)}
                     for r in sig.itertuples(index=False)],
            "signal8_mean_delay": _r(s8["mean_delay"].mean(), 1) if len(s8) else None,
            "signal8_days": list(s8["date"]),
        }
    return {
        "summary": {"n": int(len(h)), "date_min": h["date"].min(), "date_max": h["date"].max(),
                    "mean_delay": _r(h["delay_min"].mean(), 2), "median_delay": _r(h["delay_min"].median(), 1),
                    "pct15": _r(h["delayed15"].mean(), 4), "n_airlines": int(h["airline"].nunique()), "n_dest": int(h["dest1"].nunique()),
                    "window_days": HISTORY_DAYS},
        "heatmap": {"hours": list(range(24)), "dow": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    "mean_delay": _grid(h, "delay_min", 1), "pct15": _grid(h, "delayed15", 3),
                    "n": [[int(v) for v in row] for row in cnt.to_numpy()]},
        "airlines": [{"code": r.airline, "name": airline_name(r.airline), "n": int(r.n), "mean_delay": _r(r.mean_delay, 1), "pct15": _r(r.pct15)}
                     for r in a.itertuples(index=False)],
        "destinations": [{"code": r.dest1, "city": airport(r.dest1)[0], "country": airport(r.dest1)[1], "n": int(r.n),
                          "mean_delay": _r(r.mean_delay, 1), "pct15": _r(r.pct15)} for r in d.itertuples(index=False)],
        "daily": [{"date": r.date, "n": int(r.n), "mean_delay": _r(r.mean_delay, 1), "pct15": _r(r.pct15),
                   "signal": int(r.signal), "tc_name": r.tc_name} for r in td.itertuples(index=False)],
        "by_hour_top_airlines": by_hour,
        "typhoon": typhoon,
    }


# ---------------------------------------------------------------- model
def calibration_from_report(p: Path) -> list[dict]:
    if not p.exists():
        return []
    m = re.search(r"## Calibration on test.*?\n\n(\|.*?)(?:\n\n|\Z)", p.read_text(), re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines()[2:]:
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows.append({"bin": cells[0], "n": int(cells[1]), "pred_mean": float(cells[2]), "obs_rate": float(cells[3])})
    return rows


def interpretation(p: Path) -> str:
    if not p.exists():
        return ""
    txt = p.read_text()
    i = txt.find("## Interpretation")
    return txt[i:].strip() if i >= 0 else ""


def model(c: sqlite3.Connection, now: dt.datetime, models_dir: Path, reports_dir: Path) -> dict:
    man_p = models_dir / "MANIFEST.json"
    man = json.loads(man_p.read_text()) if man_p.exists() else None
    fi_p = models_dir / "feature_importance.json"
    fi = json.loads(fi_p.read_text()) if fi_p.exists() else None
    try:
        ev = live_eval_compute(c, 7, now=now, models_dir=models_dir)
    except Exception as e:  # noqa: BLE001 — the export must not fail on the optional eval
        ev = {"status": f"error: {e}", "n_matured": 0, "min_n": MIN_N, "window_days": 7}
    out = {
        "manifest": None if man is None else {
            "created_at": man.get("created_at"), "git_sha": man.get("git_sha"), "xgboost": man.get("xgboost"),
            "n_features": len(man.get("features", [])), "features": man.get("features"), "categorical": man.get("categorical"),
            "split": man.get("split"), "metrics": man.get("metrics"), "ablation_test": man.get("ablation_test"),
            "params": man.get("params"), "clf_best_iteration": man.get("clf_best_iteration"), "reg_best_iteration": man.get("reg_best_iteration"),
        },
        "calibration": calibration_from_report(reports_dir / "M2-results.md"),
        "feature_importance": fi,
        "live_eval": ev,
        "interpretation_md": interpretation(reports_dir / "M2-results.md"),
        "limitations": LIMITATIONS,
    }
    return out


# ---------------------------------------------------------------- weather
def weather(c: sqlite3.Connection, now: dt.datetime) -> dict:
    metar = c.execute("SELECT * FROM metar ORDER BY report_time DESC LIMIT 1").fetchone() if _has(c, "metar") else None
    warn = c.execute("SELECT fetched_at, n_warnings, codes, raw_json FROM hko_warnings ORDER BY fetched_at DESC LIMIT 1").fetchone() \
        if _has(c, "hko_warnings") else None
    now_hkt = now.astimezone(HKT).isoformat()
    tc = c.execute("SELECT signal, tc_name, direction, start_ts, end_ts FROM tc_signals WHERE start_ts<=? AND end_ts>=? ORDER BY start_ts DESC",
                   (now_hkt, now_hkt)).fetchall() if _has(c, "tc_signals") else []
    warnings = []
    if warn:
        try:
            for code, w in json.loads(warn["raw_json"]).items():
                warnings.append({"code": code, "name": w.get("name", code), "action": w.get("actionCode", ""),
                                 "issue_time": w.get("issueTime"), "update_time": w.get("updateTime")})
        except (ValueError, AttributeError):
            warnings = [{"code": x, "name": x, "action": ""} for x in (warn["codes"] or "").split(",") if x]
    hko_cur = None
    if _has(c, "hko_current"):
        row = c.execute("SELECT update_time, raw_json FROM hko_current ORDER BY fetched_at DESC LIMIT 1").fetchone()
        if row:
            try:
                js = json.loads(row["raw_json"])
                temps = {d.get("place"): d.get("value") for d in js.get("temperature", {}).get("data", [])}
                hko_cur = {"update_time": row["update_time"], "humidity": (js.get("humidity", {}).get("data") or [{}])[0].get("value"),
                           "temp_airport_c": temps.get("Chek Lap Kok"), "temp_hko_c": temps.get("Hong Kong Observatory"),
                           "uvindex": (js.get("uvindex") or {}).get("data", [{}])[0].get("value") if isinstance(js.get("uvindex"), dict) else None,
                           "rainfall_max_mm": max((d.get("max") or 0) for d in js.get("rainfall", {}).get("data", [])) if js.get("rainfall") else None}
            except (ValueError, AttributeError, IndexError, TypeError):
                hko_cur = {"update_time": row["update_time"]}
    return {
        "metar": None if metar is None else {k: metar[k] for k in metar.keys()},
        "hko_warnings": warnings, "hko_warnings_fetched_at": warn["fetched_at"] if warn else None,
        "tc_active": [dict(r) for r in tc],
        "hko_current": hko_cur,
    }


# ---------------------------------------------------------------- meta
def meta(c: sqlite3.Connection, now: dt.datetime, dates: dict[str, str], counts: dict) -> dict:
    has_pred = _has(c, "predictions")
    last_score = c.execute("SELECT MAX(scored_at) FROM predictions").fetchone()[0] if has_pred else None
    mv = c.execute("SELECT model_version FROM predictions WHERE scored_at=? LIMIT 1", (last_score,)).fetchone() if last_score else None
    df = _q(c, "SELECT flight_no, airline, COUNT(*) n FROM flights WHERE airline IS NOT NULL GROUP BY 1,2")
    i2i = dict(IATA_TO_ICAO)
    if not df.empty:
        df["iata"] = df["flight_no"].str.split().str[0].str.upper()
        df = df.sort_values("n", ascending=False).drop_duplicates("iata")
        i2i.update({str(k): str(v) for k, v in zip(df["iata"], df["airline"])})
    dests = sorted({(r[0] or "").split(",")[0].strip() for r in c.execute("SELECT DISTINCT destination FROM flights")} - {""})
    unmapped = [d for d in dests if not known(d)]
    if unmapped:
        log.info("airports without city mapping: %s", " ".join(unmapped))
    return {
        "generated_at": _iso(now),
        "data_as_of": _iso(c.execute("SELECT MAX(run_at) FROM ingest_log").fetchone()[0]) if _has(c, "ingest_log") else None,
        "flights_fetched_at": _iso(c.execute("SELECT MAX(fetched_at) FROM flights").fetchone()[0]),
        "last_score": _iso(last_score),
        "last_metar": _iso(c.execute("SELECT MAX(report_time) FROM metar").fetchone()[0]) if _has(c, "metar") else None,
        "model_version": mv[0] if mv else None,
        "dates": dates,
        "counts": {
            "flights": int(c.execute("SELECT COUNT(*) FROM flights").fetchone()[0]),
            "date_min": c.execute("SELECT MIN(date) FROM flights").fetchone()[0],
            "date_max": c.execute("SELECT MAX(date) FROM flights").fetchone()[0],
            "predictions": int(c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]) if has_pred else 0,
            **counts,
        },
        "airlines": AIRLINE_NAMES,
        "iata_to_icao": i2i,
        "airports": {d: {"city": airport(d)[0], "country": airport(d)[1]} for d in dests},
        "hkia": {"icao": "VHHH", "iata": "HKG", "lat": 22.308, "lon": 113.918},
        "sources": {"flights": "data.gov.hk / Airport Authority HK flight info API", "weather": "HKO open data + aviationweather.gov METAR",
                    "adsb": "adsb.lol (browser-side, display only)"},
    }


# ---------------------------------------------------------------- main
def export(db_path: Path = DB_PATH, out: Path = DEFAULT_OUT, now: dt.datetime | None = None,
           models_dir: Path = ROOT / "models", reports_dir: Path = ROOT / "reports") -> dict[str, int]:
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(HKT).date()
    dates = {"yesterday": (today - dt.timedelta(days=1)).isoformat(), "today": today.isoformat(), "tomorrow": (today + dt.timedelta(days=1)).isoformat()}
    sizes: dict[str, int] = {}
    with _conn(db_path) as c:
        deps = {k: departures(c, d, with_history=(k != "yesterday")) for k, d in dates.items()}
        for k, d in deps.items():
            sizes[f"departures_{k}.json"] = _dump(out / f"departures_{k}.json", d)
        sizes["patterns.json"] = _dump(out / "patterns.json", patterns(c, now))
        sizes["model.json"] = _dump(out / "model.json", model(c, now, models_dir, reports_dir))
        sizes["weather.json"] = _dump(out / "weather.json", weather(c, now))
        counts = {f"{k}_flights": v["n"] for k, v in deps.items()}
        sizes["meta.json"] = _dump(out / "meta.json", meta(c, now, dates, counts))
    total = sum(sizes.values())
    log.info("wrote %d files, %.0f KB total -> %s", len(sizes), total / 1024, out)
    for k, v in sizes.items():
        log.info("  %-28s %6.1f KB", k, v / 1024)
    if total > 1_000_000:
        log.warning("export is %.0f KB (> 1 MB target)", total / 1024)
    return sizes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stdout)
    if not a.db.exists():
        log.error("db not found: %s", a.db)
        return 1
    export(a.db, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
