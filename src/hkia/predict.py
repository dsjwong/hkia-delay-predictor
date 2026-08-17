"""Live scoring: predict P(delay > 15 min) and expected delay minutes for not-yet-departed HKIA departures.

Usage:
  python -m hkia.predict                      # today + tomorrow (HKT), flights without actual_ts and not cancelled
  python -m hkia.predict --date 2026-08-18    # one or more explicit dates
  python -m hkia.predict --include-departed   # score every flight of the target dates (backtest / debugging)

Pipeline: models/ (xgb_delayed15 + xgb_delay_min + MANIFEST.json, written by hkia.train) -> the SAME feature builder as
training (`hkia.features.build_features` over the whole flights table, so congestion + point-in-time rolling delay
features see all history) -> rows appended to table `predictions` (history is kept: one row per flight per run whose
feature vector changed, so `hkia.evaluate` can compare the last score before departure with the actual).

Weather for flights in the future: the as-of join has nothing after "now", so those rows get the LATEST METAR observation
(persistence forecast; `metar_age_min` capped at the training tolerance of 180 min). Limitation, not a forecast — TAF is a
stretch goal. Rolling delay features for future flights only see flights that have already departed *as of now*, which is
a slightly narrower history than the training-time cutoff (scheduled - 2 h); documented in docs/features.md.
"""
import argparse
import datetime as dt
import hashlib
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .db import ROOT, connect
from .features import build_features, load_flights, load_metar, load_tc_signals, weather_asof
from .train import to_matrix

log = logging.getLogger("hkia.predict")
HKT = dt.timezone(dt.timedelta(hours=8))
MODELS_DIR = ROOT / "models"
WX_COLS = ["temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "flt_cat", "wx_rain", "wx_ts", "wx_fog"]
METAR_TOL_MIN = 180

PRED_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    date           TEXT NOT NULL,
    flight_no      TEXT NOT NULL,
    scheduled_ts   TEXT NOT NULL,   -- ISO +08:00 (matches flights.scheduled_ts)
    p_delay15      REAL NOT NULL,
    pred_delay_min REAL NOT NULL,
    model_version  TEXT NOT NULL,   -- MANIFEST git_sha@created_at
    features_hash  TEXT NOT NULL,   -- md5 of the feature vector; a flight is re-scored only when this changes
    scored_at      TEXT NOT NULL,   -- UTC ISO
    PRIMARY KEY (date, flight_no, scheduled_ts, scored_at)
);
CREATE INDEX IF NOT EXISTS ix_pred_flight ON predictions (date, flight_no, scheduled_ts, scored_at);
"""


def load_models(models_dir: Path = MODELS_DIR) -> dict:
    clf = joblib.load(models_dir / "xgb_delayed15.joblib")
    reg = joblib.load(models_dir / "xgb_delay_min.joblib")
    manifest = json.loads((models_dir / "MANIFEST.json").read_text())
    return {"clf": clf, "reg": reg, "manifest": manifest,
            "version": f"{manifest.get('git_sha', 'unknown')}@{manifest.get('created_at', '')}"}


def target_dates(explicit: list[str] | None, now: dt.datetime) -> list[str]:
    if explicit:
        return sorted(explicit)
    today = now.astimezone(HKT).date()
    return [today.isoformat(), (today + dt.timedelta(days=1)).isoformat()]


def apply_latest_weather(feat: pd.DataFrame, metar: pd.DataFrame, now: pd.Timestamp) -> tuple[pd.DataFrame, str | None]:
    """For rows scheduled after `now`, replace the (empty) as-of weather with the latest observation <= now."""
    obs = metar[metar["report_time"] <= now]
    if obs.empty:
        return feat, None
    last = obs.sort_values("report_time").iloc[-1]
    fut = feat["scheduled_ts"] > now
    for c in WX_COLS:
        feat.loc[fut, c] = last[c]
    feat.loc[fut, "flt_cat"] = feat.loc[fut, "flt_cat"].fillna("UNK")
    age = (feat.loc[fut, "scheduled_ts"] - last["report_time"]).dt.total_seconds() / 60
    feat.loc[fut, "metar_age_min"] = age.clip(upper=METAR_TOL_MIN)
    return feat, last["report_time"].isoformat()


def score(conn, models: dict, dates: list[str], include_departed: bool = False,
          now: dt.datetime | None = None) -> pd.DataFrame:
    """Return one row per target flight with p_delay15 / pred_delay_min (not yet written)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    now_ts = pd.Timestamp(now).tz_convert("UTC")
    flights, metar, tc = load_flights(conn), load_metar(conn), load_tc_signals(conn)
    clf = models["clf"]
    top_dest = set(clf["cats"]["dest"].categories) - {"OTHER"}
    feat, stats = build_features(flights, metar, tc, top_dest=top_dest, keep_unlabelled=True)
    feat, wx_time = apply_latest_weather(feat, metar, now_ts)
    sel = feat["date"].isin(dates) & (feat["cancelled"] == 0)
    if not include_departed:
        sel &= feat["actual_ts"].isna()
    tgt = feat.loc[sel].reset_index(drop=True)
    log.info("features: %d rows (%s); targets %d for %s; latest METAR used for future rows: %s",
             stats["n_rows"], stats["date_min"] + ".." + stats["date_max"], len(tgt), dates, wx_time)
    if tgt.empty:
        return tgt.assign(p_delay15=np.nan, pred_delay_min=np.nan, features_hash="")
    X, _ = to_matrix(tgt, clf["cats"], clf["features"])
    tgt["p_delay15"] = clf["model"].predict_proba(X)[:, 1].round(4)
    Xr, _ = to_matrix(tgt, models["reg"]["cats"], models["reg"]["features"])
    tgt["pred_delay_min"] = models["reg"]["model"].predict(Xr).round(1)
    tgt["features_hash"] = [hashlib.md5(json.dumps([None if (isinstance(v, float) and np.isnan(v)) else v for v in row],
                                                   default=str).encode()).hexdigest()
                            for row in tgt[clf["features"]].itertuples(index=False, name=None)]
    return tgt


def write_predictions(conn, tgt: pd.DataFrame, version: str, now: dt.datetime, dedupe: bool = True) -> int:
    conn.executescript(PRED_SCHEMA)
    scored_at = now.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
    rows = []
    last = {}
    if dedupe:
        cur = conn.execute("SELECT date, flight_no, scheduled_ts, features_hash FROM predictions p WHERE scored_at = "
                           "(SELECT MAX(scored_at) FROM predictions q WHERE q.date=p.date AND q.flight_no=p.flight_no "
                           "AND q.scheduled_ts=p.scheduled_ts)")
        last = {(d, f, s): h for d, f, s, h in cur}
    for r in tgt.itertuples(index=False):
        sched = r.scheduled_ts.tz_convert(HKT).isoformat()
        if last.get((r.date, r.flight_no, sched)) == r.features_hash:
            continue
        rows.append((r.date, r.flight_no, sched, float(r.p_delay15), float(r.pred_delay_min), version, r.features_hash, scored_at))
    conn.executemany("INSERT OR REPLACE INTO predictions VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (scored_at, "predict", f"{len(tgt)} scored, {len(rows)} written, {version}"))
    conn.commit()
    return len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", action="append", help="YYYY-MM-DD (repeatable); default today + tomorrow HKT")
    ap.add_argument("--include-departed", action="store_true")
    ap.add_argument("--no-dedupe", action="store_true", help="append even if the feature vector is unchanged")
    ap.add_argument("--models", default=str(MODELS_DIR))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    now = dt.datetime.now(dt.timezone.utc)
    models = load_models(Path(a.models))
    conn = connect()
    tgt = score(conn, models, target_dates(a.date, now), a.include_departed, now)
    n = write_predictions(conn, tgt, models["version"], now, dedupe=not a.no_dedupe)
    if len(tgt):
        p = tgt["p_delay15"]
        log.info("scored %d flights, wrote %d rows (model %s); p_delay15 mean %.3f, quantiles 10/50/90 = %.3f/%.3f/%.3f, "
                 "P(p>0.5)=%.3f; pred_delay_min mean %.1f", len(tgt), n, models["version"], p.mean(),
                 *p.quantile([0.1, 0.5, 0.9]), (p > 0.5).mean(), tgt["pred_delay_min"].mean())
    else:
        log.info("nothing to score")
    return 0


if __name__ == "__main__":
    sys.exit(main())
