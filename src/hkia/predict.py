"""Live scoring: predict P(delay > 15 min) and expected delay minutes for not-yet-departed HKIA departures.

Usage:
  python -m hkia.predict                      # today + tomorrow (HKT), flights without actual_ts and not cancelled
  python -m hkia.predict --date 2026-08-18    # one or more explicit dates
  python -m hkia.predict --include-departed   # score every flight of the target dates (backtest / debugging)
  python -m hkia.predict --models models.cand --summary-json /tmp/cand.json   # score a candidate build, write its
                                              # per-horizon summary (the ship gate's drift check reads two of these)

Pipeline: models/ (xgb_delayed15 + xgb_delay_min + MANIFEST.json, written by hkia.train) -> the SAME feature builder as
training (`hkia.features.build_features` over the whole flights table, so congestion + point-in-time rolling delay
features see all history) -> rows written to table `predictions`. Retention per flight (see `write_predictions`):
the FIRST score, the LATEST score, and at most one score per clock hour (UTC) in between -- a new score replaces the
previous row from the same hour unless that row is the first. A new score that moves |p_delay15| < 0.01 AND
|pred_delay_min| < 1 vs the latest stored row is not stored at all. `hkia.evaluate` still takes the last stored score
before departure; `hkia.compact_predictions` applies the same hourly rule retroactively (idempotent, run daily).

The same forward pass also writes the top-3 local SHAP attributions of each score to table `explanations` (`hkia.explain`) —
**latest only**, replaced in place and pruned to a 3-day window, so that table does not grow with the scoring history.

Weather for flights in the future: the as-of join has nothing after "now", so those rows get the LATEST METAR observation
(persistence forecast; `metar_age_min` capped at the training tolerance of 180 min). Limitation, not a forecast — TAF is a
stretch goal. Rolling delay features for future flights only see flights that have already departed *as of now*, which is
a slightly narrower history than the training-time cutoff (scheduled - 2 h); documented in docs/features.md.

The inbound (turnaround) block is passed the scoring timestamp, so a flight whose scheduled - 2 h cutoff has not been
reached yet scores with the same all-missing block an unlinked flight gets — train and serve agree by construction. Its
coverage per forecast-horizon bucket goes into the ingest_log detail every run: that number is the drift monitor for the
dropout rate the model was trained with (`hkia.train --inbound-dropout`).
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

from . import explain
from .db import ROOT, connect
from .features import build_features, load_flights, load_links, load_metar, load_tc_signals, weather_asof
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
"""
# (the former ix_pred_flight index duplicated the primary-key autoindex column for column; dropped by hkia.compact_predictions)
MIN_DELTA_P = 0.01      # a new score is stored only if it moves p_delay15 by >= this ...
MIN_DELTA_MIN = 1.0     # ... or pred_delay_min by >= this (minutes), relative to the latest stored row
# forecast-horizon buckets (minutes between scoring time and the *scheduled* departure) for the inbound coverage
# monitor: the logged three go into ingest_log every run, the four in the summary feed the ship gate's drift check.
LOG_HORIZONS = ((None, 30, "<30min"), (30, 120, "30-120min"), (120, None, ">120min"))
SUMMARY_HORIZONS = ((None, 30, "<30min"), (30, 120, "30-120min"), (120, 720, "120min-12h"), (720, None, ">12h"))


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
    # `now` gates the inbound block: a flight whose scheduled - 2 h cutoff has not been reached scores exactly as an
    # unlinked flight, which is the encoding it was trained under (hkia.features.inbound_features).
    feat, stats = build_features(flights, metar, tc, top_dest=top_dest, keep_unlabelled=True,
                                 links=load_links(conn), now=now_ts)
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
    # same forward pass, one extra booster call: local SHAP contributions for the "why this prediction" block.
    # Explanations are a nice-to-have on top of the score, so they must not be able to fail the scoring run: an
    # xgboost API change (requirements-ml pins only >=2.1) or a feature reorder would otherwise stop predictions
    # entirely, and ingest.yml would still commit + export the stale ones.
    try:
        contribs = explain.attribute(clf["model"], X, clf["features"])
        tgt[["base_logodds", "top_json"]] = explain.explain_frame(tgt, X, contribs, clf["features"])
    except Exception:  # noqa: BLE001 — scoring continues without the "why" block
        log.exception("attribution failed; scoring continues without explanations")
    Xr, _ = to_matrix(tgt, models["reg"]["cats"], models["reg"]["features"])
    tgt["pred_delay_min"] = models["reg"]["model"].predict(Xr).round(1)
    tgt["features_hash"] = [hashlib.md5(json.dumps([None if (isinstance(v, float) and np.isnan(v)) else v for v in row],
                                                   default=str).encode()).hexdigest()
                            for row in tgt[clf["features"]].itertuples(index=False, name=None)]
    return tgt


def horizon_stats(tgt: pd.DataFrame, now: dt.datetime, horizons=SUMMARY_HORIZONS) -> dict:
    """Per forecast-horizon bucket: n, mean p_delay15, mean inbound_known — the serve-time coverage / drift monitor.

    Horizon is scoring time -> *scheduled* departure (never -> actual, which would slice by the outcome). The inbound
    block is knowable only inside ~2 h of the scheduled time, so its coverage per bucket is what tells us whether the
    dropout rate the model was trained with still matches deployment (see hkia.train.mask_inbound).
    """
    if not len(tgt):
        return {label: {"n": 0, "p_mean": None, "inbound_known": None} for _, _, label in horizons}
    h = (tgt["scheduled_ts"] - pd.Timestamp(now).tz_convert("UTC")).dt.total_seconds() / 60
    known = tgt["inbound_known"] if "inbound_known" in tgt.columns else pd.Series(np.nan, index=tgt.index)
    out = {}
    all_rows = pd.Series(True, index=h.index)
    for lo, hi, label in horizons:
        s = (h >= lo if lo is not None else all_rows) & (h < hi if hi is not None else all_rows)
        n = int(s.sum())
        out[label] = {"n": n,
                      "p_mean": round(float(tgt.loc[s, "p_delay15"].mean()), 4) if n else None,
                      "inbound_known": round(float(known[s].mean()), 4) if n and known.notna().any() else None}
    return out


def inbound_coverage(tgt: pd.DataFrame, now: dt.datetime) -> str:
    """One-line inbound coverage by horizon for the ingest_log detail string."""
    st = horizon_stats(tgt, now, LOG_HORIZONS)
    parts = [f"{k} {v['inbound_known'] if v['inbound_known'] is not None else 'n/a'} (n={v['n']})" for k, v in st.items()]
    return "inbound_known " + ", ".join(parts)


def hour_key(scored_at: str) -> str:
    """Clock-hour bucket of a UTC ISO timestamp ('2026-08-17T10:18:03+00:00' -> '2026-08-17T10')."""
    return scored_at[:13]


def decide(first_ts: str | None, latest: tuple | None, p: float, pred_min: float, features_hash: str,
           scored_at: str) -> str:
    """Retention rule for one new score. `latest` = (scored_at, p_delay15, pred_delay_min, features_hash) of the
    latest stored row or None. Returns 'insert', 'replace' (delete the latest row, then insert) or 'skip'."""
    if latest is None:
        return "insert"
    l_ts, l_p, l_min, l_hash = latest
    if l_hash == features_hash:
        return "skip"                                            # feature vector unchanged -> same score
    if abs(p - l_p) < MIN_DELTA_P and abs(pred_min - l_min) < MIN_DELTA_MIN:
        return "skip"                                            # moved too little to be worth a row
    if l_ts != first_ts and hour_key(l_ts) == hour_key(scored_at):
        return "replace"                                         # one row per clock hour, first row is protected
    return "insert"


def _state(conn, dates: list[str]) -> dict:
    """(date, flight_no, scheduled_ts) -> (first_scored_at, latest_row) for every flight of `dates` with a prediction."""
    q = f"""
    SELECT date, flight_no, scheduled_ts, scored_at, p_delay15, pred_delay_min, features_hash,
           MIN(scored_at) OVER w AS first_ts,
           ROW_NUMBER() OVER (w ORDER BY scored_at DESC) AS rn
    FROM predictions WHERE date IN ({",".join("?" * len(dates))})
    WINDOW w AS (PARTITION BY date, flight_no, scheduled_ts)
    """
    return {(d, f, s): (first, (ts, p, m, h)) for d, f, s, ts, p, m, h, first, rn in conn.execute(q, dates) if rn == 1}


def write_predictions(conn, tgt: pd.DataFrame, version: str, now: dt.datetime, dedupe: bool = True) -> int:
    """Apply `decide` to every scored flight. Returns the number of rows written (inserted or replaced).
    dedupe=False appends every score unconditionally (debugging only)."""
    conn.executescript(PRED_SCHEMA)
    scored_at = now.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
    dates = sorted(set(tgt["date"])) if len(tgt) else []
    state = _state(conn, dates) if (dedupe and dates) else {}
    rows, drop = [], []
    for r in tgt.itertuples(index=False):
        sched = r.scheduled_ts.tz_convert(HKT).isoformat()
        p, m = float(r.p_delay15), float(r.pred_delay_min)
        first_ts, latest = state.get((r.date, r.flight_no, sched), (None, None))
        action = decide(first_ts, latest, p, m, r.features_hash, scored_at) if dedupe else "insert"
        if action == "skip":
            continue
        if action == "replace":
            drop.append((r.date, r.flight_no, sched, latest[0]))
        rows.append((r.date, r.flight_no, sched, p, m, version, r.features_hash, scored_at))
    conn.executemany("DELETE FROM predictions WHERE date=? AND flight_no=? AND scheduled_ts=? AND scored_at=?", drop)
    conn.executemany("INSERT OR REPLACE INTO predictions VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.execute("INSERT INTO ingest_log VALUES (?,?,?)",
                 (scored_at, "predict", f"{len(tgt)} scored, {len(rows)} written ({len(drop)} replaced same-hour rows), "
                                        f"{version}, {inbound_coverage(tgt, now)}"))
    conn.commit()
    return len(rows)


def write_explanations(conn, tgt: pd.DataFrame, version: str, now: dt.datetime,
                       prune_old: bool = True) -> tuple[int, int]:
    """Store the top-3 SHAP attributions of every scored flight, then prune old dates. Returns (written, pruned).

    Unlike `predictions` this table is **latest-only** (primary key without `scored_at`): a re-score replaces the row, so the
    table stays at ~3 days of schedule no matter how often the cron runs. See `hkia.explain`.

    `prune_old=False` for an explicit `--date` run, which may target a day outside the rolling window — pruning there
    would delete the rows the same call just wrote.
    """
    written = explain.write(conn, tgt, version, now, HKT)
    pruned = explain.prune(conn, now, HKT) if prune_old else 0
    conn.commit()
    return written, pruned


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", action="append", help="YYYY-MM-DD (repeatable); default today + tomorrow HKT")
    ap.add_argument("--include-departed", action="store_true")
    ap.add_argument("--no-dedupe", action="store_true", help="append every score unconditionally (debugging)")
    ap.add_argument("--models", default=str(MODELS_DIR), help="model directory (a candidate build can be scored "
                                                              "against a scratch db without touching models/)")
    ap.add_argument("--summary-json", help="write the per-horizon scoring summary here (input to scripts/inbound_gate.py)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    now = dt.datetime.now(dt.timezone.utc)
    models = load_models(Path(a.models))
    conn = connect()
    tgt = score(conn, models, target_dates(a.date, now), a.include_departed, now)
    n = write_predictions(conn, tgt, models["version"], now, dedupe=not a.no_dedupe)
    n_why = write_explanations(conn, tgt, models["version"], now, prune_old=not a.date)
    log.info("explanations: %d rows written (latest only, unchanged ones skipped), %d pruned outside yesterday..tomorrow", *n_why)
    if a.summary_json:
        summary = {"scored_at": now.isoformat(timespec="seconds"), "models": str(Path(a.models)),
                   "model_version": models["version"], "dates": target_dates(a.date, now), "n": int(len(tgt)),
                   "p_delay15_mean": round(float(tgt["p_delay15"].mean()), 4) if len(tgt) else None,
                   "horizon": horizon_stats(tgt, now)}
        Path(a.summary_json).write_text(json.dumps(summary, indent=2))
        log.info("wrote %s", a.summary_json)
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
