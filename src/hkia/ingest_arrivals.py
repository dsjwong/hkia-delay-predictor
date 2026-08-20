"""Ingest HKIA passenger arrivals into SQLite — the inbound half of the turnaround signal (docs/inbound-feature.md).

Same endpoint as departures with `arrival=true`:
  https://www.hongkongairport.com/flightinfo-rest/rest/flights/past?date=YYYY-MM-DD&lang=en&cargo=false&arrival=true
Verified 2026-08-20: 200 OK, ~440-455 passenger arrivals/day, same rolling ~91-day window as departures, same day-object shape.

Row fields differ from departures: `origin` (list of IATA) instead of `destination`, `stand` (parking position) instead of
`gate`, plus `hall` and `baggage`. Status vocabulary (observed 2026-08-19/20):
  past days   `At gate HH:MM [(DD/MM/YYYY)]` (426/447), `Cancelled`
  today       + `Landed HH:MM` (touched down, not yet on blocks), `Est at HH:MM [(DD/MM/YYYY)]`, `""` (not yet started)
  future days status is `""` and **`stand` is empty** — the parking position is only published ~2-3 h ahead.
So three timestamps are kept apart: `actual_ts` = on blocks ("At gate"), `landed_ts` = touchdown ("Landed"),
`estimated_ts` = the airport's live estimate. Turnaround is measured from `actual_ts` (on blocks) when it exists.

Arrivals are NOT the label source, so this job fails soft: a bad fetch logs and returns 0, never breaking the departures
+ predict pipeline it runs alongside.

Usage:
  python -m hkia.ingest_arrivals                # yesterday + today (+ tomorrow's schedule)
  python -m hkia.ingest_arrivals --backfill     # whole available window (~91 days)
  python -m hkia.ingest_arrivals --fill-gaps    # only the window days that are missing / thin (nightly, cheap)
  python -m hkia.ingest_arrivals 2026-08-01
"""
import argparse
import datetime as dt
import logging
import re
import sys
import time

import requests

from .db import connect
from .ingest_flights import BACKFILL_DAYS, HKT, _ts, fetch_day

log = logging.getLogger("hkia.arrivals")

ARRIVALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS arrivals (
    date            TEXT NOT NULL,   -- HKIA "date" of the row (HKT calendar day of scheduled arrival)
    flight_no       TEXT NOT NULL,   -- operating flight number, e.g. "CX 459"
    scheduled_time  TEXT NOT NULL,   -- "HH:MM" HKT as given by the API
    airline         TEXT,            -- ICAO airline code of the operating flight, e.g. "CPA"
    codeshares      TEXT,            -- other flight numbers on the same row, comma-separated
    origin          TEXT,            -- IATA code(s), comma-separated for multi-leg
    scheduled_ts    TEXT NOT NULL,   -- ISO 8601 with +08:00
    actual_ts       TEXT,            -- on blocks, from "At gate HH:MM [(DD/MM/YYYY)]"
    landed_ts       TEXT,            -- touchdown, from "Landed HH:MM [(DD/MM/YYYY)]"
    estimated_ts    TEXT,            -- from "Est at HH:MM [(DD/MM/YYYY)]"
    status_raw      TEXT,
    terminal        TEXT,
    hall            TEXT,            -- arrival hall (A/B)
    baggage         TEXT,            -- reclaim belt
    stand           TEXT,            -- parking position, e.g. "N36", "D214", "W65" -- links to a departure gate, see hkia.rotations
    first_seen_at   TEXT NOT NULL,   -- UTC ISO
    fetched_at      TEXT NOT NULL,   -- UTC ISO of the last upsert that changed this row
    PRIMARY KEY (date, flight_no, scheduled_time)
);
CREATE INDEX IF NOT EXISTS arrivals_stand ON arrivals(date, stand);
"""

# "At gate 17:18 (19/08/2026)" / "Landed 09:04" / "Est at 21:30"
_TIME_RE = re.compile(r"^(At gate|Landed|Est at)\s+(\d\d:\d\d)(?:\s+\((\d\d)/(\d\d)/(\d{4})\))?$")
_KIND = {"At gate": 0, "Landed": 1, "Est at": 2}


def parse_status(status: str, row_date: str) -> tuple[str | None, str | None, str | None]:
    """Return (actual_ts, landed_ts, estimated_ts) from the free-text status. Unknown/blank/"Cancelled" -> all None."""
    m = _TIME_RE.match((status or "").strip())
    if not m:
        return None, None, None
    kind, hhmm, d, mo, y = m.groups()
    ts = _ts(f"{y}-{mo}-{d}" if y else row_date, hhmm)
    out: list[str | None] = [None, None, None]
    out[_KIND[kind]] = ts
    return out[0], out[1], out[2]


def rows_from_payload(payload: list[dict]) -> list[dict]:
    out = []
    for day in payload:
        date = day["date"]
        for r in day.get("list", []):
            flights = r.get("flight") or []
            if not flights:
                continue
            actual, landed, est = parse_status(r.get("status"), date)
            out.append({
                "date": date,
                "flight_no": flights[0]["no"],
                "scheduled_time": r["time"],
                "airline": flights[0].get("airline"),
                "codeshares": ",".join(f["no"] for f in flights[1:]) or None,
                "origin": ",".join(r.get("origin") or []),
                "scheduled_ts": _ts(date, r["time"]),
                "actual_ts": actual,
                "landed_ts": landed,
                "estimated_ts": est,
                "status_raw": r.get("status"),
                "terminal": r.get("terminal"),
                "hall": r.get("hall"),
                "baggage": r.get("baggage"),
                "stand": r.get("stand"),
            })
    return out


UPSERT = """
INSERT INTO arrivals (date, flight_no, scheduled_time, airline, codeshares, origin, scheduled_ts,
                      actual_ts, landed_ts, estimated_ts, status_raw, terminal, hall, baggage, stand,
                      first_seen_at, fetched_at)
VALUES (:date, :flight_no, :scheduled_time, :airline, :codeshares, :origin, :scheduled_ts,
        :actual_ts, :landed_ts, :estimated_ts, :status_raw, :terminal, :hall, :baggage, :stand, :now, :now)
ON CONFLICT(date, flight_no, scheduled_time) DO UPDATE SET
    airline=excluded.airline, codeshares=excluded.codeshares, origin=excluded.origin,
    actual_ts=COALESCE(excluded.actual_ts, arrivals.actual_ts),
    landed_ts=COALESCE(excluded.landed_ts, arrivals.landed_ts),
    estimated_ts=excluded.estimated_ts,
    status_raw=excluded.status_raw, terminal=excluded.terminal, hall=excluded.hall,
    baggage=excluded.baggage, stand=COALESCE(NULLIF(excluded.stand, ''), arrivals.stand),
    fetched_at=excluded.fetched_at
WHERE excluded.status_raw IS NOT arrivals.status_raw
   OR COALESCE(NULLIF(excluded.stand, ''), arrivals.stand) IS NOT arrivals.stand
   OR excluded.origin IS NOT arrivals.origin OR excluded.codeshares IS NOT arrivals.codeshares
   OR excluded.terminal IS NOT arrivals.terminal OR excluded.hall IS NOT arrivals.hall
   OR excluded.baggage IS NOT arrivals.baggage
"""  # WHERE: only rewrite the row when something changed -> fewer dirty pages -> smaller git deltas
# stand: COALESCE(NULLIF(...)) because a re-fetch of an old day can come back with an empty stand; never lose one we saw.


def ingest_dates(dates: list[dt.date], conn) -> tuple[int, int]:
    """Upsert the given dates. Returns (rows upserted, dates whose fetch failed)."""
    conn.executescript(ARRIVALS_SCHEMA)
    n, failed = 0, 0
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with requests.Session() as s:
        for d in dates:
            try:
                payload = fetch_day(d, s, arrival=True)
            except (requests.RequestException, ValueError) as e:
                log.warning("%s: fetch failed: %s", d, e)
                failed += 1
                continue
            rows = rows_from_payload(payload)
            for r in rows:
                r["now"] = now
            conn.executemany(UPSERT, rows)
            conn.commit()
            log.info("%s: %d rows", d, len(rows))
            n += len(rows)
            if len(dates) > 3:
                time.sleep(0.5)  # be polite during backfill
    conn.execute("INSERT INTO ingest_log VALUES (?,?,?)",
                 (now, "arrivals", f"{len(dates)} dates, {n} rows, {failed} failed"))
    conn.commit()
    return n, failed


THIN = 300  # a complete day is ~440-455 rows; anything below this was never fully ingested


def gap_dates(conn) -> list[dt.date]:
    """Window days that are missing or thin — what the nightly backfill job re-fetches (cheap and self-healing)."""
    conn.executescript(ARRIVALS_SCHEMA)
    have = dict(conn.execute("SELECT date, COUNT(*) FROM arrivals GROUP BY 1").fetchall())
    today = dt.datetime.now(HKT).date()
    window = [today - dt.timedelta(days=i) for i in range(BACKFILL_DAYS, 0, -1)]  # completed days only
    return [d for d in window if have.get(d.isoformat(), 0) < THIN]


def default_dates(backfill: bool) -> list[dt.date]:
    today = dt.datetime.now(HKT).date()
    if backfill:
        return [today - dt.timedelta(days=i) for i in range(BACKFILL_DAYS, -1, -1)] + [today + dt.timedelta(days=1)]
    return [today - dt.timedelta(days=1), today, today + dt.timedelta(days=1)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dates", nargs="*", help="YYYY-MM-DD; default yesterday/today/tomorrow")
    ap.add_argument("--backfill", action="store_true", help="ingest the whole ~91-day window")
    ap.add_argument("--fill-gaps", action="store_true", help="ingest only window days that are missing or thin")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    conn = connect()
    if a.fill_gaps:
        dates = gap_dates(conn)
        log.info("fill-gaps: %d window days missing or < %d rows", len(dates), THIN)
    else:
        dates = [dt.date.fromisoformat(x) for x in a.dates] or default_dates(a.backfill)
    n, failed = ingest_dates(dates, conn) if dates else (0, 0)
    total = conn.execute("SELECT COUNT(*) FROM arrivals").fetchone()[0]
    landed = conn.execute("SELECT COUNT(*) FROM arrivals WHERE actual_ts IS NOT NULL").fetchone()[0]
    log.info("upserted %d rows; arrivals table: %d rows, %d with actual_ts", n, total, landed)
    if failed:
        log.error("%d of %d arrival dates failed to fetch (non-fatal: arrivals are a feature source, not the labels)",
                  failed, len(dates))
    return 0  # fail soft — never break the departures + predict pipeline this runs alongside


if __name__ == "__main__":
    sys.exit(main())
