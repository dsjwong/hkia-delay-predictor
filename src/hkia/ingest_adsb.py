"""Snapshot the ADS-B feed into SQLite once per cron run — the raw material for aircraft-rotation linkage.

One `hkia.adsb.fetch_adsb()` frame per run (~50-60 aircraft within 100 nm of HKIA) is appended to `adsb_snapshots`:
~55 rows/run x 48 runs/day ~= 2,600 rows/day, pruned to a 30-day retention window (~80 k rows, a few MB).

What the snapshots are for: `hex` (ICAO 24-bit address) is a stable per-airframe identity. A hex seen under an arrival
callsign and later the same day under a departure callsign is the same aircraft turning around — see `hkia.rotations`.

Registration (`r`) and type (`t`) only arrive when a readsb-family provider serves the frame; OpenSky's /states/all has
neither, so those columns are NULL on OpenSky runs. Mapping hex -> registration offline would need an aircraft database
(the OpenSky aircraft CSV, ~500 k rows) — noted, deliberately not built: `hex` is enough to link a rotation, and
registration is only nicer to *display*.

Coverage caveat worth knowing before trusting this: the feed is a 100 nm ring, so an inbound only appears in it for the
last ~15-20 min of its flight. The snapshots identify *which* aircraft turned around, not how late it was an hour out —
that lateness comes from the arrivals table's `estimated_ts`.

Usage: python -m hkia.ingest_adsb        # one snapshot + prune; fails soft, always exits 0
"""
import argparse
import datetime as dt
import logging
import sys

import pandas as pd

from . import adsb
from .db import connect

log = logging.getLogger("hkia.adsb")

ADSB_SCHEMA = """
CREATE TABLE IF NOT EXISTS adsb_snapshots (
    fetched_at   TEXT NOT NULL,   -- UTC ISO of the poll that produced this frame (one value per run)
    hex          TEXT NOT NULL,   -- ICAO 24-bit address, lower-case hex -- the stable airframe identity
    callsign     TEXT,            -- as transmitted, e.g. "CPA261"
    registration TEXT,            -- readsb `r` (e.g. "B-LRA"); NULL when the frame came from OpenSky
    ac_type      TEXT,            -- readsb `t` (e.g. "A359"); NULL on OpenSky
    lat          REAL,
    lon          REAL,
    alt_ft       REAL,
    on_ground    INTEGER,
    gs_kt        REAL,
    track_deg    REAL,
    dst_nm       REAL,            -- great-circle distance from HKIA
    provider     TEXT NOT NULL,   -- which feed served the frame
    PRIMARY KEY (fetched_at, hex)
);
CREATE INDEX IF NOT EXISTS adsb_callsign ON adsb_snapshots(callsign, fetched_at);
CREATE INDEX IF NOT EXISTS adsb_hex ON adsb_snapshots(hex, fetched_at);
"""

RETENTION_DAYS = 30

INSERT = """
INSERT OR IGNORE INTO adsb_snapshots
    (fetched_at, hex, callsign, registration, ac_type, lat, lon, alt_ft, on_ground, gs_kt, track_deg, dst_nm, provider)
VALUES (:fetched_at, :hex, :callsign, :registration, :ac_type, :lat, :lon, :alt_ft, :on_ground, :gs_kt, :track_deg, :dst_nm, :provider)
"""


def _n(v):
    """NaN/NaT -> None so sqlite stores NULL rather than the float nan."""
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


def rows_from_frame(ac: pd.DataFrame, fetched_at: str, provider: str) -> list[dict]:
    """Standard `hkia.adsb` frame -> adsb_snapshots rows. Aircraft with no hex are dropped (nothing to link them by)."""
    out = []
    for r in ac.itertuples(index=False):
        hx = (str(r.hex).strip().lower() if isinstance(r.hex, str) else "")
        if not hx:
            continue
        cs = (r.callsign or "").strip().upper() if isinstance(r.callsign, str) else None
        out.append({
            "fetched_at": fetched_at, "hex": hx, "callsign": cs or None,
            "registration": _n(r.r) if isinstance(r.r, str) and r.r.strip() else None,
            "ac_type": _n(r.t) if isinstance(r.t, str) and r.t.strip() else None,
            "lat": _n(float(r.lat)), "lon": _n(float(r.lon)), "alt_ft": _n(float(r.alt_ft)),
            "on_ground": int(bool(r.on_ground)), "gs_kt": _n(None if pd.isna(r.gs_kt) else float(r.gs_kt)),
            "track_deg": _n(None if pd.isna(r.track_deg) else float(r.track_deg)),
            "dst_nm": _n(None if pd.isna(r.dst_nm) else float(r.dst_nm)), "provider": provider,
        })
    return out


def prune(conn, now: dt.datetime | None = None) -> int:
    """Drop snapshots older than RETENTION_DAYS. Returns rows deleted."""
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = (now - dt.timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    cur = conn.execute("DELETE FROM adsb_snapshots WHERE fetched_at < ?", (cutoff,))
    return cur.rowcount


def snapshot(conn, now: dt.datetime | None = None) -> str:
    """Fetch one frame and store it. Returns a one-line summary for ingest_log. Never raises."""
    conn.executescript(ADSB_SCHEMA)
    now = now or dt.datetime.now(dt.timezone.utc)
    fetched_at = now.isoformat(timespec="seconds")
    ac, err, _at = adsb.fetch_adsb()
    if ac is None or not len(ac):
        return f"ERROR no frame ({err or 'empty'})"
    provider = adsb._LAST_GOOD["provider"] or "?"
    rows = rows_from_frame(ac, fetched_at, provider)
    conn.executemany(INSERT, rows)
    deleted = prune(conn, now)
    conn.commit()
    n_reg = sum(1 for r in rows if r["registration"])
    return f"{len(rows)} aircraft via {provider}, {n_reg} with registration, {deleted} pruned"


def main(argv=None):
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    conn = connect()
    now = dt.datetime.now(dt.timezone.utc)
    try:
        detail = snapshot(conn, now)
    except Exception as e:  # noqa: BLE001 — a flaky ADS-B feed must never fail the cron
        detail = f"ERROR {type(e).__name__}: {e}"
    log.info("adsb snapshot: %s", detail)
    conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now.isoformat(timespec="seconds"), "adsb", detail))
    conn.commit()
    total, runs = conn.execute("SELECT COUNT(*), COUNT(DISTINCT fetched_at) FROM adsb_snapshots").fetchone()
    log.info("adsb_snapshots: %d rows over %d snapshots", total, runs)
    return 0  # fail soft


if __name__ == "__main__":
    sys.exit(main())
