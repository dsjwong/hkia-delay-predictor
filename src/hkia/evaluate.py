"""Live evaluation: predictions vs actuals for flights that have since departed -> reports/live-eval.md.

Usage: python -m hkia.evaluate [--days 7] [--out reports/live-eval.md]

For each departed flight with at least one prediction, take the LAST score before departure (max scored_at with
scored_at <= actual_ts; predictions are only ever written for flights without an actual, so this is the freshest score
the service showed before the plane left). Metrics over the flights that departed in the last `days` days:
AUC / Brier / log loss for P(delay > 15 min), MAE for delay minutes, versus the airline x hour baseline table saved
by hkia.train and the naive rates. Honest about small samples: fewer than MIN_N matured predictions -> "not enough data".
"""
import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, roc_auc_score

from .db import ROOT, connect
from .features import DELAY_MAX, DELAY_MIN

log = logging.getLogger("hkia.evaluate")
MIN_N = 100
HKT = "Asia/Hong_Kong"


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
           f.actual_ts, f.airline
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


def _clf(y, p) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    out = {"brier": round(float(brier_score_loss(y, p)), 4), "logloss": round(float(log_loss(y, p)), 4)}
    out["auc"] = round(float(roc_auc_score(y, p)), 4) if len(np.unique(y)) == 2 else None
    return out


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
        import joblib
        from .train import baseline_b_predict
        tab = joblib.load(models_dir / "baseline_b_airline_hour.joblib")
        b = df.assign(sched_hour=df["scheduled_ts"].dt.tz_convert(HKT).dt.hour)
        out["baseline_airline_hour"] = {**_clf(y, baseline_b_predict(b, tab["clf"])),
                                        "mae": round(float(mean_absolute_error(r, baseline_b_predict(b, tab["reg"]))), 3)}
    except Exception as e:  # noqa: BLE001 - baseline is optional
        out["baseline_airline_hour"] = {"error": str(e)}
    out["by_model_version"] = df.groupby("model_version").size().to_dict()
    return out


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
