"""Read-only FastAPI service over data/hkia.db (set HKIA_DB to point elsewhere).

  uvicorn hkia.api:app --reload            # http://127.0.0.1:8000/docs

  GET /health                              db path, row counts, freshness of flights / metar / predictions
  GET /departures?date=YYYY-MM-DD          schedule for a HKT day + latest prediction per flight + status
  GET /flight/{flight_no}?date=YYYY-MM-DD  one flight incl. its full prediction history for that day
  GET /model                               models/MANIFEST.json + rolling 7-day live evaluation
  GET /weather/latest                      latest METAR (live table) + latest HKO current readings / warnings

Predictions are produced by the cron (`python -m hkia.predict`) and cached in table `predictions`; the API never scores.
"""
import datetime as dt
import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from . import db as _db
from .evaluate import compute as live_eval

app = FastAPI(title="HKIA delay predictor", version="0.3.0", description=__doc__)
HKT = dt.timezone(dt.timedelta(hours=8))
DATE_RE = r"^\d{4}-\d{2}-\d{2}$"


def _conn() -> sqlite3.Connection:
    if not _db.DB_PATH.exists():
        raise HTTPException(503, f"database not found: {_db.DB_PATH}")
    conn = sqlite3.connect(f"file:{_db.DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _has(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _today() -> str:
    return dt.datetime.now(HKT).date().isoformat()


LATEST_PRED = """
SELECT p.date, p.flight_no, p.scheduled_ts, p.p_delay15, p.pred_delay_min, p.model_version, p.scored_at
FROM predictions p
WHERE p.date = ? AND p.scored_at = (SELECT MAX(scored_at) FROM predictions q
                                   WHERE q.date=p.date AND q.flight_no=p.flight_no AND q.scheduled_ts=p.scheduled_ts)
"""


def _flight_dict(f: sqlite3.Row, pred: dict | None) -> dict:
    d = dict(f)
    delay = None
    if d.get("actual_ts"):
        a = dt.datetime.fromisoformat(d["actual_ts"]); s = dt.datetime.fromisoformat(d["scheduled_ts"])
        delay = round((a - s).total_seconds() / 60, 1)
    status = "cancelled" if (d.get("status_raw") or "").strip().lower() == "cancelled" else \
        "departed" if d.get("actual_ts") else "scheduled"
    d.update(status=status, delay_min=delay, prediction=pred)
    return d


@app.get("/health")
def health():
    with _conn() as c:
        out = {"db": str(_db.DB_PATH), "now_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "tables": {}}
        for t in ("flights", "metar", "metar_hist", "hko_current", "hko_warnings", "tc_signals", "predictions"):
            if _has(c, t):
                out["tables"][t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        out["flights_last_fetched_at"] = c.execute("SELECT MAX(fetched_at) FROM flights").fetchone()[0]
        out["metar_latest_report_time"] = c.execute("SELECT MAX(report_time) FROM metar").fetchone()[0]
        out["predictions_last_scored_at"] = c.execute("SELECT MAX(scored_at) FROM predictions").fetchone()[0] if _has(c, "predictions") else None
        out["status"] = "ok"
        return out


@app.get("/departures")
def departures(date: str | None = Query(None, pattern=DATE_RE, description="HKT day, default today")):
    date = date or _today()
    with _conn() as c:
        preds = {(r["flight_no"], r["scheduled_ts"]): dict(r) for r in c.execute(LATEST_PRED, (date,))} if _has(c, "predictions") else {}
        rows = c.execute("SELECT date, flight_no, scheduled_ts, airline, destination, codeshares, terminal, gate, "
                         "status_raw, estimated_ts, actual_ts FROM flights WHERE date=? ORDER BY scheduled_ts, flight_no", (date,)).fetchall()
        flights = [_flight_dict(f, preds.get((f["flight_no"], f["scheduled_ts"]))) for f in rows]
        summary = {"n": len(flights), "n_departed": sum(f["status"] == "departed" for f in flights),
                   "n_cancelled": sum(f["status"] == "cancelled" for f in flights),
                   "n_with_prediction": sum(f["prediction"] is not None for f in flights)}
        return {"date": date, "summary": summary, "flights": flights}


@app.get("/flight/{flight_no}")
def flight(flight_no: str, date: str | None = Query(None, pattern=DATE_RE)):
    date = date or _today()
    flight_no = flight_no.strip().upper()
    with _conn() as c:
        rows = c.execute("SELECT * FROM flights WHERE date=? AND (flight_no=? OR REPLACE(flight_no,' ','')=?) "
                         "ORDER BY scheduled_ts", (date, flight_no, flight_no.replace(" ", ""))).fetchall()
        if not rows:
            raise HTTPException(404, f"no departure {flight_no} on {date}")
        out = []
        for f in rows:
            hist = [dict(r) for r in c.execute("SELECT p_delay15, pred_delay_min, model_version, features_hash, scored_at FROM predictions "
                                               "WHERE date=? AND flight_no=? AND scheduled_ts=? ORDER BY scored_at",
                                               (date, f["flight_no"], f["scheduled_ts"]))] if _has(c, "predictions") else []
            d = _flight_dict(f, hist[-1] if hist else None)
            d["prediction_history"] = hist
            out.append(d)
        return out[0] if len(out) == 1 else {"date": date, "flight_no": flight_no, "legs": out}


@app.get("/model")
def model(eval_days: int = Query(7, ge=1, le=90)):
    manifest_path = Path(_db.ROOT) / "models" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    with _conn() as c:
        return {"manifest": manifest, "live_eval": live_eval(c, eval_days)}


@app.get("/weather/latest")
def weather_latest():
    with _conn() as c:
        metar = c.execute("SELECT * FROM metar ORDER BY report_time DESC LIMIT 1").fetchone()
        cur = c.execute("SELECT fetched_at, update_time, raw_json FROM hko_current ORDER BY fetched_at DESC LIMIT 1").fetchone()
        warn = c.execute("SELECT fetched_at, n_warnings, codes, raw_json FROM hko_warnings ORDER BY fetched_at DESC LIMIT 1").fetchone()
        return {"metar": dict(metar) if metar else None,
                "hko_current": {"fetched_at": cur["fetched_at"], "update_time": cur["update_time"], "data": json.loads(cur["raw_json"])} if cur else None,
                "hko_warnings": {"fetched_at": warn["fetched_at"], "n_warnings": warn["n_warnings"], "codes": warn["codes"],
                                 "data": json.loads(warn["raw_json"])} if warn else None}
