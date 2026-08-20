"""Read-only data access for the Streamlit dashboard: SQLite (data/hkia.db) + models/ + reports/.

Everything is cached with st.cache_data(ttl=600); the DB is the committed file that the GitHub Actions cron refreshes every
30 min, so on Streamlit Community Cloud a new bot commit == fresh data on the next reload.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # hkia.evaluate (numpy/pandas only) for the live-evaluation section

from hkia.evaluate import MIN_N, compute as live_eval_compute  # noqa: E402

DB_PATH = Path(os.environ.get("HKIA_DB", ROOT / "data" / "hkia.db"))
HKT = dt.timezone(dt.timedelta(hours=8))
TTL = 600
DELAY_MIN, DELAY_MAX = -60, 600  # same outlier clip as hkia.features
HISTORY_DAYS = 91

from hkia import explain  # noqa: E402  (templates only — the attribution half imports xgboost lazily)
from hkia.airlines import AIRLINE_NAMES  # noqa: E402  (shared with hkia.export_json)


def airline_name(code: str | None) -> str:
    return AIRLINE_NAMES.get(code or "", code or "?")


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _q(sql: str, params=()) -> pd.DataFrame:
    with _conn() as c:
        return pd.read_sql_query(sql, c, params=params)


def db_available() -> bool:
    return DB_PATH.exists()


def now_hkt() -> dt.datetime:
    return dt.datetime.now(HKT)


def fmt_hkt(ts: str | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if not ts:
        return "—"
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return t.tz_convert("Asia/Hong_Kong").strftime(fmt) + " HKT"


# ---------------------------------------------------------------- freshness
@st.cache_data(ttl=TTL)
def freshness() -> dict:
    with _conn() as c:
        has_pred = c.execute("SELECT 1 FROM sqlite_master WHERE name='predictions'").fetchone() is not None
        return {
            "last_ingest": c.execute("SELECT MAX(run_at) FROM ingest_log").fetchone()[0],
            "flights_fetched": c.execute("SELECT MAX(fetched_at) FROM flights").fetchone()[0],
            "metar_report": c.execute("SELECT MAX(report_time) FROM metar").fetchone()[0],
            "pred_scored": c.execute("SELECT MAX(scored_at) FROM predictions").fetchone()[0] if has_pred else None,
            "n_flights": c.execute("SELECT COUNT(*) FROM flights").fetchone()[0],
            "date_min": c.execute("SELECT MIN(date) FROM flights").fetchone()[0],
            "date_max": c.execute("SELECT MAX(date) FROM flights").fetchone()[0],
        }


# ---------------------------------------------------------------- today's departures
LATEST_PRED = """
SELECT p.flight_no, p.scheduled_ts, p.p_delay15, p.pred_delay_min, p.scored_at
FROM predictions p
WHERE p.date = ? AND p.scored_at = (SELECT MAX(scored_at) FROM predictions q
                                   WHERE q.date=p.date AND q.flight_no=p.flight_no AND q.scheduled_ts=p.scheduled_ts)
"""


@st.cache_data(ttl=TTL)
def departures(date: str) -> pd.DataFrame:
    fl = _q("SELECT flight_no, scheduled_ts, airline, destination, codeshares, terminal, gate, status_raw, estimated_ts, "
            "actual_ts FROM flights WHERE date=? ORDER BY scheduled_ts, flight_no", (date,))
    if fl.empty:
        return fl
    with _conn() as c:
        has_pred = c.execute("SELECT 1 FROM sqlite_master WHERE name='predictions'").fetchone() is not None
    pr = _q(LATEST_PRED, (date,)) if has_pred else pd.DataFrame(columns=["flight_no", "scheduled_ts", "p_delay15", "pred_delay_min", "scored_at"])
    df = fl.merge(pr, on=["flight_no", "scheduled_ts"], how="left")
    sched = pd.to_datetime(df["scheduled_ts"], utc=True).dt.tz_convert("Asia/Hong_Kong")
    actual = pd.to_datetime(df["actual_ts"], utc=True, errors="coerce").dt.tz_convert("Asia/Hong_Kong")
    df["sched_hkt"] = sched
    df["sched_hour"] = sched.dt.hour
    df["sched_time"] = sched.dt.strftime("%H:%M")
    df["actual_time"] = actual.dt.strftime("%H:%M")
    df["delay_min"] = ((actual - sched).dt.total_seconds() / 60).round(0)
    cancelled = df["status_raw"].fillna("").str.strip().str.lower().eq("cancelled")
    df["status"] = np.where(cancelled, "cancelled", np.where(df["actual_ts"].notna(), "departed", "scheduled"))
    df["airline_name"] = df["airline"].map(airline_name)
    df["actual_delayed15"] = np.where(df["delay_min"].notna(), df["delay_min"] > 15, None)
    df["hit"] = np.where(df["delay_min"].notna() & df["p_delay15"].notna(),
                         (df["p_delay15"] >= 0.5) == (df["delay_min"] > 15), None)
    return df


@st.cache_data(ttl=TTL)
def explanations(date: str) -> dict[tuple[str, str], list[dict]]:
    """(flight_no, scheduled_ts) -> top-3 attributions of that flight's latest score (`hkia.explain.why` rows).

    Table `explanations` holds the latest score only, for a 3-day window; {} before the first scoring run writes it.
    """
    with _conn() as c:
        return explain.load(c, date)


@st.cache_data(ttl=TTL)
def weather_now() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        metar = c.execute("SELECT * FROM metar ORDER BY report_time DESC LIMIT 1").fetchone()
        warn = c.execute("SELECT fetched_at, n_warnings, codes, raw_json FROM hko_warnings ORDER BY fetched_at DESC LIMIT 1").fetchone()
        now = dt.datetime.now(HKT).isoformat()
        tc = c.execute("SELECT signal, tc_name, direction, start_ts, end_ts FROM tc_signals WHERE start_ts<=? AND end_ts>=? "
                       "ORDER BY start_ts DESC", (now, now)).fetchall()
    warnings = []
    if warn:
        try:
            for code, w in json.loads(warn["raw_json"]).items():
                warnings.append({"code": code, "name": w.get("name", code), "action": w.get("actionCode", "")})
        except (ValueError, AttributeError):
            warnings = [{"code": x, "name": x, "action": ""} for x in (warn["codes"] or "").split(",") if x]
    return {"metar": dict(metar) if metar else None,
            "warnings": warnings, "warnings_fetched_at": warn["fetched_at"] if warn else None,
            "tc_active": [dict(r) for r in tc]}


# ---------------------------------------------------------------- history / delay patterns
@st.cache_data(ttl=TTL)
def history(days: int = HISTORY_DAYS) -> pd.DataFrame:
    """Departed, non-cancelled flights of the rolling window with delay_min clipped to the training outlier bounds."""
    since = (dt.datetime.now(HKT).date() - dt.timedelta(days=days)).isoformat()
    df = _q("SELECT date, flight_no, scheduled_ts, actual_ts, airline, destination FROM flights "
            "WHERE actual_ts IS NOT NULL AND date >= ? AND LOWER(TRIM(COALESCE(status_raw,''))) != 'cancelled'", (since,))
    if df.empty:
        return df
    sched = pd.to_datetime(df["scheduled_ts"], utc=True).dt.tz_convert("Asia/Hong_Kong")
    actual = pd.to_datetime(df["actual_ts"], utc=True).dt.tz_convert("Asia/Hong_Kong")
    df["delay_min"] = (actual - sched).dt.total_seconds() / 60
    df = df[(df["delay_min"] >= DELAY_MIN) & (df["delay_min"] <= DELAY_MAX)].copy()
    df["delayed15"] = (df["delay_min"] > 15).astype(int)
    df["hour"] = sched.dt.hour
    df["dow"] = sched.dt.dayofweek
    df["dest1"] = df["destination"].fillna("").str.split(",").str[0]
    return df


@st.cache_data(ttl=TTL)
def typhoon_days(days: int = HISTORY_DAYS) -> pd.DataFrame:
    """Per date of the history window: max TC signal in force that day (any overlap), plus mean delay / % > 15."""
    h = history(days)
    if h.empty:
        return pd.DataFrame()
    tc = _q("SELECT tc_name, signal, start_ts, end_ts FROM tc_signals WHERE signal IN ('1','3','8','9','10') "
            "AND end_ts >= ? ORDER BY start_ts", (h["date"].min(),))
    per_day = h.groupby("date").agg(n=("delay_min", "size"), mean_delay=("delay_min", "mean"), pct15=("delayed15", "mean")).reset_index()
    per_day["signal"] = 0
    per_day["tc_name"] = None
    for r in tc.itertuples(index=False):
        d0 = pd.Timestamp(r.start_ts).tz_convert("Asia/Hong_Kong").date()
        d1 = pd.Timestamp(r.end_ts).tz_convert("Asia/Hong_Kong").date()
        for d in pd.date_range(d0, d1, freq="D").date:
            m = per_day["date"] == d.isoformat()
            per_day.loc[m, "signal"] = np.maximum(per_day.loc[m, "signal"], int(r.signal))
            per_day.loc[m, "tc_name"] = r.tc_name
    return per_day


# ---------------------------------------------------------------- model artefacts
@st.cache_data(ttl=TTL)
def manifest() -> dict | None:
    p = ROOT / "models" / "MANIFEST.json"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data(ttl=TTL)
def feature_importance() -> dict | None:
    p = ROOT / "models" / "feature_importance.json"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data(ttl=TTL)
def calibration_from_report() -> pd.DataFrame:
    """Parse the '## Calibration on test' table written by hkia.train into reports/M2-results.md."""
    p = ROOT / "reports" / "M2-results.md"
    if not p.exists():
        return pd.DataFrame()
    txt = p.read_text()
    m = re.search(r"## Calibration on test.*?\n\n(\|.*?)(?:\n\n|\Z)", txt, re.S)
    if not m:
        return pd.DataFrame()
    rows = []
    for line in m.group(1).splitlines()[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows.append({"bin": cells[0], "n": int(cells[1]), "pred_mean": float(cells[2]), "obs_rate": float(cells[3])})
    return pd.DataFrame(rows)


@st.cache_data(ttl=TTL)
def report_interpretation() -> str:
    p = ROOT / "reports" / "M2-results.md"
    if not p.exists():
        return ""
    txt = p.read_text()
    i = txt.find("## Interpretation")
    return txt[i:] if i >= 0 else ""


@st.cache_data(ttl=TTL)
def live_eval(days: int = 7) -> dict:
    with _conn() as c:
        return live_eval_compute(c, days)


__all__ = ["MIN_N"]
