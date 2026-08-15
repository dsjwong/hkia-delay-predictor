"""Ingest HKIA passenger departures into SQLite.

Endpoint (Airport Authority HK, via data.gov.hk):
  https://www.hongkongairport.com/flightinfo-rest/rest/flights/past?date=YYYY-MM-DD&lang=en&cargo=false&arrival=false
Serves a rolling window of ~91 days back plus upcoming days (schedule only).

Usage:
  python -m hkia.ingest_flights                 # yesterday + today (+ tomorrow's schedule)
  python -m hkia.ingest_flights --backfill      # whole available window (~91 days) — first run
  python -m hkia.ingest_flights 2026-08-01 2026-08-02
"""
import argparse
import datetime as dt
import logging
import re
import sys
import time

import requests

from .db import connect

log = logging.getLogger("hkia.flights")
URL = "https://www.hongkongairport.com/flightinfo-rest/rest/flights/past"
HEADERS = {"User-Agent": "hkia-delay-predictor/0.1 (+https://github.com/dsjwong/hkia-delay-predictor)"}
HKT = dt.timezone(dt.timedelta(hours=8))
BACKFILL_DAYS = 91  # empirically: date=today-91 -> 200, today-92 -> 400 (see docs/M0-data-recon.md)

_TIME_RE = re.compile(r"^(Dep|Est at)\s+(\d\d:\d\d)(?:\s+\((\d\d)/(\d\d)/(\d{4})\))?$")


def fetch_day(date: dt.date, session: requests.Session | None = None) -> list[dict]:
    s = session or requests
    r = s.get(URL, params={"date": date.isoformat(), "lang": "en", "cargo": "false", "arrival": "false"},
              headers=HEADERS, timeout=60)
    if r.status_code == 400:  # outside the served window
        return []
    r.raise_for_status()
    return r.json()


def _ts(date_str: str, hhmm: str) -> str:
    return f"{date_str}T{hhmm}:00+08:00"


def parse_status(status: str, row_date: str) -> tuple[str | None, str | None]:
    """Return (actual_ts, estimated_ts) from the free-text status."""
    m = _TIME_RE.match(status or "")
    if not m:
        return None, None
    kind, hhmm, d, mo, y = m.groups()
    date_str = f"{y}-{mo}-{d}" if y else row_date
    ts = _ts(date_str, hhmm)
    return (ts, None) if kind == "Dep" else (None, ts)


def rows_from_payload(payload: list[dict]) -> list[dict]:
    out = []
    for day in payload:
        date = day["date"]
        for r in day.get("list", []):
            flights = r.get("flight") or []
            if not flights:
                continue
            actual, est = parse_status(r.get("status"), date)
            out.append({
                "date": date,
                "flight_no": flights[0]["no"],
                "scheduled_time": r["time"],
                "airline": flights[0].get("airline"),
                "codeshares": ",".join(f["no"] for f in flights[1:]) or None,
                "destination": ",".join(r.get("destination") or []),
                "scheduled_ts": _ts(date, r["time"]),
                "actual_ts": actual,
                "estimated_ts": est,
                "status_raw": r.get("status"),
                "terminal": r.get("terminal"),
                "aisle": r.get("aisle"),
                "gate": r.get("gate"),
            })
    return out


UPSERT = """
INSERT INTO flights (date, flight_no, scheduled_time, airline, codeshares, destination, scheduled_ts,
                     actual_ts, estimated_ts, status_raw, terminal, aisle, gate, first_seen_at, fetched_at)
VALUES (:date, :flight_no, :scheduled_time, :airline, :codeshares, :destination, :scheduled_ts,
        :actual_ts, :estimated_ts, :status_raw, :terminal, :aisle, :gate, :now, :now)
ON CONFLICT(date, flight_no, scheduled_time) DO UPDATE SET
    airline=excluded.airline, codeshares=excluded.codeshares, destination=excluded.destination,
    actual_ts=COALESCE(excluded.actual_ts, flights.actual_ts),
    estimated_ts=excluded.estimated_ts,
    status_raw=excluded.status_raw, terminal=excluded.terminal, aisle=excluded.aisle, gate=excluded.gate,
    fetched_at=excluded.fetched_at
"""


def ingest_dates(dates: list[dt.date], conn) -> int:
    n = 0
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with requests.Session() as s:
        for d in dates:
            try:
                payload = fetch_day(d, s)
            except requests.RequestException as e:
                log.warning("%s: fetch failed: %s", d, e)
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
    conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, "flights", f"{len(dates)} dates, {n} rows"))
    conn.commit()
    return n


def default_dates(backfill: bool) -> list[dt.date]:
    today = dt.datetime.now(HKT).date()
    if backfill:
        return [today - dt.timedelta(days=i) for i in range(BACKFILL_DAYS, -1, -1)] + [today + dt.timedelta(days=1)]
    return [today - dt.timedelta(days=1), today, today + dt.timedelta(days=1)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dates", nargs="*", help="YYYY-MM-DD; default yesterday/today/tomorrow")
    ap.add_argument("--backfill", action="store_true", help="ingest the whole ~91-day window")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    dates = [dt.date.fromisoformat(x) for x in a.dates] or default_dates(a.backfill)
    conn = connect()
    n = ingest_dates(dates, conn)
    total = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
    labelled = conn.execute("SELECT COUNT(*) FROM flights WHERE actual_ts IS NOT NULL").fetchone()[0]
    log.info("upserted %d rows; flights table: %d rows, %d with actual_ts", n, total, labelled)
    return 0


if __name__ == "__main__":
    sys.exit(main())
