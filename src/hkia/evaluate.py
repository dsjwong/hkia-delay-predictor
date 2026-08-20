"""Live evaluation: predictions vs actuals for flights that have since departed -> reports/live-eval.md.

Usage: python -m hkia.evaluate [--days 7] [--out reports/live-eval.md]

For each departed flight with at least one prediction, take the LAST score before departure (max scored_at with
scored_at <= actual_ts; predictions are only ever written for flights without an actual, so this is the freshest score
the service showed before the plane left). Metrics over the flights that departed in the last `days` days:
AUC / Brier / log loss for P(delay > 15 min), MAE for delay minutes, versus the airline x hour baseline table saved
by hkia.train and the naive rates. Honest about small samples: fewer than MIN_N matured predictions -> "not enough data".

`compute` also produces the slices the "model report card" shows in both front ends (all of them honest about n, and
None rather than a number when a slice has a single class or is empty):
  daily        per HKT departure date: AUC / Brier / MAE for the model and the baseline + n
  lead_buckets how far ahead the last score was written (< 30 min / 30-120 min / 2-12 h / > 12 h): AUC / MAE + n
  calibration  10 equal-width probability bins on the live data: predicted mean vs observed rate
  notable      last 7 days: the 5 most confident correct calls and the 5 biggest misses (|p - outcome|)
  deltas       model minus airline x hour baseline for every headline metric
"""
import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .db import ROOT, connect
from .features import DELAY_MAX, DELAY_MIN

log = logging.getLogger("hkia.evaluate")
MIN_N = 100
HKT = "Asia/Hong_Kong"
MIN_SLICE_N = 20   # below this a slice's AUC is noise; it is still reported, with n, and flagged `thin`
N_NOTABLE = 5
CAL_BINS = 10
# (label, lower bound inclusive, upper bound exclusive) on minutes between the last score and the actual departure
LEAD_BUCKETS = [("< 30 min", 0.0, 30.0), ("30–120 min", 30.0, 120.0), ("2–12 h", 120.0, 720.0), ("> 12 h", 720.0, np.inf)]


def matured_predictions(conn, days: int = 7, now: dt.datetime | None = None) -> pd.DataFrame:
    """One row per departed flight in the window: last prediction before departure + actual delay."""
    if not conn.execute("SELECT name FROM sqlite_master WHERE name='predictions'").fetchone():
        return pd.DataFrame()
    now = now or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(days=days)).isoformat(timespec="seconds")
    q = """
    WITH last AS (
      SELECT p.date, p.flight_no, p.scheduled_ts, p.p_delay15, p.pred_delay_min, p.model_version, p.scored_at,
             ROW_NUMBER() OVER (PARTITION BY p.date, p.flight_no, p.scheduled_ts ORDER BY p.scored_at DESC) AS rn
      FROM predictions p JOIN flights f USING (date, flight_no)
      WHERE f.scheduled_ts = p.scheduled_ts AND f.actual_ts IS NOT NULL
        AND datetime(p.scored_at) <= datetime(f.actual_ts)
    )
    SELECT l.date, l.flight_no, l.scheduled_ts, l.p_delay15, l.pred_delay_min, l.model_version, l.scored_at,
           f.actual_ts, f.airline, f.destination
    FROM last l JOIN flights f ON f.date=l.date AND f.flight_no=l.flight_no AND f.scheduled_ts=l.scheduled_ts
    WHERE l.rn = 1 AND datetime(f.actual_ts) >= datetime(?)
    """
    df = pd.read_sql_query(q, conn, params=(since,))
    if df.empty:
        return df
    for c in ("scheduled_ts", "actual_ts", "scored_at"):
        df[c] = pd.to_datetime(df[c], utc=True)
    df["delay_min"] = (df["actual_ts"] - df["scheduled_ts"]).dt.total_seconds() / 60
    df = df[(df["delay_min"] >= DELAY_MIN) & (df["delay_min"] <= DELAY_MAX)].reset_index(drop=True)
    df["delayed15"] = (df["delay_min"] > 15).astype(int)
    df["lead_min"] = (df["actual_ts"] - df["scored_at"]).dt.total_seconds() / 60
    return df


# metrics in plain numpy (identical to sklearn's; keeps the dashboard's requirements free of scikit-learn)
def roc_auc(y, p) -> float | None:
    """Mann-Whitney AUC with average ranks for ties; None if only one class present."""
    y = np.asarray(y, dtype=int); p = np.asarray(p, dtype=float)
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = pd.Series(p).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def mean_absolute_error(y, yhat) -> float:
    return float(np.mean(np.abs(np.asarray(y, dtype=float) - np.asarray(yhat, dtype=float))))


def _clf(y, p) -> dict:
    y = np.asarray(y, dtype=float); p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    out = {"brier": round(float(np.mean((p - y) ** 2)), 4),
           "logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)}
    auc = roc_auc(y, p)
    out["auc"] = round(auc, 4) if auc is not None else None
    return out


def _num(x, nd: int = 4) -> float | None:
    """JSON-safe round: None / NaN / inf -> None (export_json dumps with allow_nan=False)."""
    if x is None:
        return None
    v = float(x)
    return None if not np.isfinite(v) else round(v, nd)


def _slice(y, p, r, yhat) -> dict:
    """AUC / Brier / MAE for one slice. AUC is None when the slice holds a single class."""
    y = np.asarray(y, dtype=int)
    if len(y) == 0:
        return {"auc": None, "brier": None, "mae": None}
    auc = roc_auc(y, p)
    pc = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return {"auc": _num(auc), "brier": _num(np.mean((pc - y) ** 2)),
            "mae": _num(mean_absolute_error(r, yhat), 3)}


def _baseline_columns(df: pd.DataFrame, models_dir: Path) -> pd.DataFrame | None:
    """Score the whole window with the airline x hour lookup table saved by hkia.train -> columns b_p, b_min."""
    import joblib

    from .baseline import baseline_b_predict
    tab = joblib.load(models_dir / "baseline_b_airline_hour.joblib")
    b = df.assign(sched_hour=df["scheduled_ts"].dt.tz_convert(HKT).dt.hour)
    return df.assign(b_p=np.asarray(baseline_b_predict(b, tab["clf"]), dtype=float),
                     b_min=np.asarray(baseline_b_predict(b, tab["reg"]), dtype=float))


def daily_series(df: pd.DataFrame, has_baseline: bool) -> list[dict]:
    """Per HKT departure date: n, observed rate, and the model's (and baseline's) AUC / Brier / MAE that day."""
    rows = []
    for date, g in df.groupby("date", sort=True):
        row = {"date": str(date), "n": int(len(g)), "delayed15_rate": _num(g["delayed15"].mean()),
               "thin": bool(len(g) < MIN_SLICE_N),
               "model": _slice(g["delayed15"], g["p_delay15"], g["delay_min"], g["pred_delay_min"])}
        if has_baseline:
            row["baseline"] = _slice(g["delayed15"], g["b_p"], g["delay_min"], g["b_min"])
        rows.append(row)
    return rows


def lead_time_buckets(df: pd.DataFrame, has_baseline: bool) -> list[dict]:
    """How well the model does as a function of how far ahead of departure its last score was written."""
    rows = []
    for label, lo, hi in LEAD_BUCKETS:
        g = df[(df["lead_min"] >= lo) & (df["lead_min"] < hi)]
        row = {"label": label, "lo_min": lo, "hi_min": None if not np.isfinite(hi) else hi,
               "n": int(len(g)), "thin": bool(len(g) < MIN_SLICE_N),
               "delayed15_rate": _num(g["delayed15"].mean()) if len(g) else None,
               "median_lead_min": _num(g["lead_min"].median(), 1) if len(g) else None,
               "model": _slice(g["delayed15"], g["p_delay15"], g["delay_min"], g["pred_delay_min"])}
        if has_baseline:
            row["baseline"] = _slice(g["delayed15"], g["b_p"], g["delay_min"], g["b_min"])
        rows.append(row)
    return rows


def calibration_bins(df: pd.DataFrame, nbins: int = CAL_BINS) -> list[dict]:
    """Reliability of the live probabilities: equal-width bins, mean predicted vs observed rate (empty bins dropped)."""
    edges = np.linspace(0.0, 1.0, nbins + 1)
    idx = np.clip(np.digitize(df["p_delay15"].to_numpy(dtype=float), edges[1:-1], right=False), 0, nbins - 1)
    rows = []
    for i in range(nbins):
        m = idx == i
        if not m.any():
            continue
        g = df[m]
        rows.append({"bin": f"{edges[i]:.1f}-{edges[i + 1]:.1f}", "n": int(m.sum()),
                     "pred_mean": _num(g["p_delay15"].mean(), 3), "obs_rate": _num(g["delayed15"].mean(), 3)})
    return rows


def notable_flights(df: pd.DataFrame, k: int = N_NOTABLE) -> dict:
    """The 5 most confident correct calls and the 5 biggest misses (|p - outcome|, ties broken by delay size)."""
    d = df.assign(dest=df.get("destination", pd.Series("", index=df.index)).fillna("").str.split(",").str[0].str.strip(),
                  err=(df["p_delay15"] - df["delayed15"]).abs())

    def rec(r) -> dict:
        return {"flight_no": r.flight_no, "date": str(r.date), "airline": r.airline, "dest": r.dest or None,
                "p": _num(r.p_delay15, 3), "pred_min": _num(r.pred_delay_min, 1), "delay_min": _num(r.delay_min, 0),
                "delayed15": int(r.delayed15), "lead_min": _num(r.lead_min, 0)}

    hits = d[d["delayed15"] == 1].sort_values("p_delay15", ascending=False).head(k)
    # biggest |p - outcome| in both directions: low p but late, and high p but on time (>= 2 of each when both occur,
    # because live probabilities rarely exceed 0.9 and a plain top-k would only ever show missed delays)
    late = d[d["delayed15"] == 1].sort_values(["err", "delay_min"], ascending=[False, False]).head(k // 2 + 1)
    calm = d[d["delayed15"] == 0].sort_values(["err", "delay_min"], ascending=[False, True]).head(k // 2 + 1)
    miss = pd.concat([late, calm]).sort_values("err", ascending=False).head(k)
    return {"confident_correct": [rec(r) for r in hits.itertuples(index=False)],
            "worst_misses": [rec(r) for r in miss.itertuples(index=False)]}


def compute(conn, days: int = 7, now: dt.datetime | None = None, models_dir: Path = ROOT / "models") -> dict:
    df = matured_predictions(conn, days, now)
    n = len(df)
    out = {"window_days": days, "n_matured": int(n), "min_n": MIN_N, "computed_at":
           (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")}
    if n < MIN_N:
        out["status"] = f"not enough matured predictions yet ({n} < {MIN_N}); the cron has to run for a while first"
        return out
    out["status"] = "ok"
    y, r = df["delayed15"].to_numpy(), df["delay_min"].to_numpy()
    out["date_min"], out["date_max"] = df["date"].min(), df["date"].max()
    out["delayed15_rate"] = round(float(y.mean()), 4)
    out["median_lead_min"] = round(float(df["lead_min"].median()), 1)
    out["model"] = {**_clf(y, df["p_delay15"]), "mae": round(float(mean_absolute_error(r, df["pred_delay_min"])), 3)}
    out["naive_rate"] = {**_clf(y, np.full(n, y.mean())), "mae": round(float(mean_absolute_error(r, np.full(n, np.median(r)))), 3)}
    try:  # airline x hour baseline table saved by hkia.train
        df = _baseline_columns(df, models_dir)
        out["baseline_airline_hour"] = {**_clf(y, df["b_p"]),
                                        "mae": round(float(mean_absolute_error(r, df["b_min"])), 3)}
    except Exception as e:  # noqa: BLE001 - baseline is optional
        out["baseline_airline_hour"] = {"error": str(e)}
    has_baseline = "b_p" in df.columns

    def _delta(k: str) -> float | None:
        a, b = out["model"].get(k), out["baseline_airline_hour"].get(k)
        return None if a is None or b is None else _num(a - b, 3 if k == "mae" else 4)

    out["deltas"] = {k: _delta(k) for k in ("auc", "brier", "logloss", "mae")} if has_baseline else None
    out["daily"] = daily_series(df, has_baseline)
    out["lead_buckets"] = lead_time_buckets(df, has_baseline)
    out["calibration"] = calibration_bins(df)
    out["notable"] = notable_flights(df)
    out["min_slice_n"] = MIN_SLICE_N
    out["by_model_version"] = df.groupby("model_version").size().to_dict()
    return out


def _fmt(x, nd: int = 4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def render(res: dict) -> str:
    lines = ["# Live evaluation — predictions vs actuals", "",
             f"Generated {res['computed_at']}. Window: flights departed in the last {res['window_days']} days; "
             f"per flight, the last prediction written before its actual departure. Matured predictions: **{res['n_matured']}**.", ""]
    if res["status"] != "ok":
        lines += [f"**{res['status']}**", ""]
        return "\n".join(lines)
    lines += [f"Dates {res['date_min']}..{res['date_max']}; observed P(delay > 15) = {res['delayed15_rate']}; "
              f"median lead time between last score and departure = {res['median_lead_min']} min.", "",
              "| predictor | AUC | Brier | log loss | MAE (min) |", "|---|---|---|---|---|"]
    for k in ("model", "baseline_airline_hour", "naive_rate"):
        m = res.get(k, {})
        if "error" in m:
            lines.append(f"| {k} | (error: {m['error']}) | | | |")
        else:
            lines.append(f"| {k} | {m.get('auc')} | {m.get('brier')} | {m.get('logloss')} | {m.get('mae')} |")
    d = res.get("deltas") or {}
    if d.get("auc") is not None:
        lines += ["", f"Model minus airline × hour baseline: AUC {d['auc']:+.4f} · Brier {d['brier']:+.4f} · "
                      f"log loss {d['logloss']:+.4f} · MAE {d['mae']:+.2f} min. "
                      "The margin is modest — this is a lookup table with weather and congestion bolted on, not a crystal ball."]

    thin = f"(< {res.get('min_slice_n', MIN_SLICE_N)} flights — treat as noise)"
    if res.get("daily"):
        lines += ["", "## Per day", "", "| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in res["daily"]:
            m, b = r["model"], r.get("baseline", {})
            lines.append(f"| {r['date']}{' *' if r['thin'] else ''} | {r['n']} | {_fmt(r['delayed15_rate'])} | {_fmt(m['auc'])} | "
                         f"{_fmt(b.get('auc'))} | {_fmt(m['brier'])} | {_fmt(m['mae'], 1)} | {_fmt(b.get('mae'), 1)} |")
        if any(r["thin"] for r in res["daily"]):
            lines += ["", f"`*` = thin day {thin}."]

    if res.get("lead_buckets"):
        lines += ["", "## By lead time (minutes between the last score and the actual departure)", "",
                  "| lead time | n | delayed > 15 | model AUC | baseline AUC | model MAE |", "|---|---:|---:|---:|---:|---:|"]
        for r in res["lead_buckets"]:
            m, b = r["model"], r.get("baseline", {})
            lines.append(f"| {r['label']}{' *' if r['thin'] else ''} | {r['n']} | {_fmt(r['delayed15_rate'])} | {_fmt(m['auc'])} | "
                         f"{_fmt(b.get('auc'))} | {_fmt(m['mae'], 1)} |")
        star = f"`*` = thin bucket {thin}. " if any(r["thin"] for r in res["lead_buckets"]) else ""
        lines += ["", star + "Scores written far ahead of departure know less: a bucket near 0.5 means no signal there."]

    if res.get("calibration"):
        lines += ["", "## Calibration on live data (10 equal-width probability bins)", "",
                  "| bin | n | pred_mean | obs_rate |", "|---|---:|---:|---:|"]
        lines += [f"| {r['bin']} | {r['n']} | {_fmt(r['pred_mean'], 3)} | {_fmt(r['obs_rate'], 3)} |" for r in res["calibration"]]

    nb = res.get("notable") or {}
    for key, title in (("confident_correct", "Most confident correct calls"), ("worst_misses", "Biggest misses")):
        if nb.get(key):
            lines += ["", f"## {title}", "", "| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |",
                      "|---|---|---|---|---:|---:|---:|"]
            lines += [f"| {r['flight_no']} | {r['date']} | {r['airline'] or '—'} | {r['dest'] or '—'} | {_fmt(r['p'], 2)} | "
                      f"{_fmt(r['pred_min'], 1)} | {_fmt(r['delay_min'], 0)} min |" for r in nb[key]]

    lines += ["", f"Model versions in window: {res['by_model_version']}", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "reports" / "live-eval.md"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    res = compute(connect(), a.days)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(render(res))
    log.info("%s -> %s", res["status"], a.out)
    print(render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
