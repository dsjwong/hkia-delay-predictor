"""SQLite helpers. Single file DB at data/hkia.db (override with HKIA_DB env var)."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("HKIA_DB", ROOT / "data" / "hkia.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS flights (
    date            TEXT NOT NULL,   -- HKIA "date" of the row (HKT calendar day of scheduled departure)
    flight_no       TEXT NOT NULL,   -- operating flight number, e.g. "CX 255"
    scheduled_time  TEXT NOT NULL,   -- "HH:MM" HKT as given by the API
    airline         TEXT,            -- ICAO airline code of operating flight, e.g. "CPA"
    codeshares      TEXT,            -- other flight numbers on the same row, comma-separated
    destination     TEXT,            -- IATA code(s), comma-separated for multi-leg
    scheduled_ts    TEXT NOT NULL,   -- ISO 8601 with +08:00
    actual_ts       TEXT,            -- ISO 8601 +08:00, parsed from "Dep HH:MM [(DD/MM/YYYY)]"
    estimated_ts    TEXT,            -- ISO 8601 +08:00, parsed from "Est at HH:MM [(DD/MM/YYYY)]"
    status_raw      TEXT,
    terminal        TEXT,
    aisle           TEXT,
    gate            TEXT,
    first_seen_at   TEXT NOT NULL,   -- UTC ISO
    fetched_at      TEXT NOT NULL,   -- UTC ISO of the last upsert that changed this row
    PRIMARY KEY (date, flight_no, scheduled_time)
);
CREATE TABLE IF NOT EXISTS hko_current (
    fetched_at  TEXT PRIMARY KEY,    -- UTC ISO
    update_time TEXT,                -- HKO updateTime (+08:00)
    raw_json    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hko_warnings (
    fetched_at  TEXT PRIMARY KEY,
    n_warnings  INTEGER,
    codes       TEXT,                -- comma-separated warning codes, e.g. "WTCSGNL,WRAIN"
    raw_json    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metar (
    report_time TEXT PRIMARY KEY,    -- UTC ISO from aviationweather (METAR is UTC)
    raw_ob      TEXT NOT NULL,
    temp_c      REAL,
    dewp_c      REAL,
    wdir        INTEGER,
    wspd_kt     INTEGER,
    wgst_kt     INTEGER,
    visib       TEXT,                -- as given ("6+" or number, statute miles)
    ceiling_ft  INTEGER,             -- lowest BKN/OVC base, NULL if none
    flt_cat     TEXT,
    wx_string   TEXT,
    fetched_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingest_log (
    run_at   TEXT NOT NULL,
    job      TEXT NOT NULL,
    detail   TEXT
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn
