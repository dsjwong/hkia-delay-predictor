"""Backfill historical weather for the flight window.

1. VHHH hourly METAR from the Iowa Environmental Mesonet ASOS archive -> table `metar_hist`
   (kept separate from the live `metar` table, which comes from aviationweather.gov; `features.py`
   unions the two). Times are UTC in the source and stored as UTC ISO; convert at join time.
2. Tropical-cyclone / strong-monsoon signal history from HKO's public warning database
   (the tab-separated file behind https://www.hko.gov.hk/en/wxinfo/climat/warndb/warndb1.shtml)
   -> table `tc_signals`. Times are HKT.

Both are idempotent (INSERT OR REPLACE on natural keys). Usage:
  python -m hkia.backfill_weather                # incremental: last day in metar_hist (or min flight date-1) .. today
  python -m hkia.backfill_weather --start 2026-05-15 --end 2026-08-17
  python -m hkia.backfill_weather --tc-only | --metar-only
"""
import argparse
import csv
import datetime as dt
import io
import logging
import sys
import time

import requests

from .db import connect

log = logging.getLogger("hkia.backfill")
IEM_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
HKO_TC_URL = "https://www.hko.gov.hk/dps/wxinfo/climat/warndb/tc.dat"
HEADERS = {"User-Agent": "hkia-delay-predictor/0.1 (+https://github.com/dsjwong/hkia-delay-predictor)"}
HKT = dt.timezone(dt.timedelta(hours=8))


# ---------- METAR (IEM) ----------

def fetch_iem_csv(start: dt.date, end: dt.date, retries: int = 8, pause: float = 20.0) -> str:
    """Return the IEM ASOS CSV text for [start, end) UTC. Retries on 'server over capacity'."""
    params = {"station": "VHHH", "data": "all", "tz": "Etc/UTC", "format": "onlycomma", "latlon": "no",
              "missing": "M", "trace": "T", "direct": "no", "report_type": "3",
              "year1": start.year, "month1": start.month, "day1": start.day,
              "year2": end.year, "month2": end.month, "day2": end.day}
    for attempt in range(1, retries + 1):
        r = requests.get(IEM_URL, params=params, headers=HEADERS, timeout=120)
        if r.ok and r.text.startswith("station,"):
            return r.text
        log.warning("IEM %s..%s attempt %d: %s %s", start, end, attempt, r.status_code, r.text[:80].strip())
        time.sleep(pause)
    raise RuntimeError(f"IEM request failed after {retries} attempts for {start}..{end}")


def _num(x):
    try:
        return None if x in ("M", "", None) else float(x)
    except ValueError:
        return None


def _f_to_c(f):
    return None if f is None else round((f - 32) * 5 / 9, 1)


def ceiling_from_layers(covers, bases) -> int | None:
    bases_ft = [b for c, b in zip(covers, bases) if c in ("BKN", "OVC", "VV") and b is not None]
    return int(min(bases_ft)) if bases_ft else None


def flight_category(visib_sm, ceiling_ft) -> str | None:
    """Standard US flight-category rules (what aviationweather's fltCat uses)."""
    if visib_sm is None and ceiling_ft is None:
        return None
    v = 99.0 if visib_sm is None else visib_sm
    c = 99999 if ceiling_ft is None else ceiling_ft
    if v < 1 or c < 500:
        return "LIFR"
    if v < 3 or c < 1000:
        return "IFR"
    if v <= 5 or c <= 3000:
        return "MVFR"
    return "VFR"


def parse_iem_csv(text: str, now: str) -> list[tuple]:
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        valid = r["valid"]  # "YYYY-MM-DD HH:MM" UTC
        report_time = valid.replace(" ", "T") + ":00Z"
        covers = [r.get(f"skyc{i}") for i in range(1, 5)]
        bases = [_num(r.get(f"skyl{i}")) for i in range(1, 5)]
        vis = _num(r.get("vsby"))
        ceil = ceiling_from_layers(covers, bases)
        wx = r.get("wxcodes")
        rows.append((
            report_time, r.get("metar") or None,
            _f_to_c(_num(r.get("tmpf"))), _f_to_c(_num(r.get("dwpf"))),
            None if _num(r.get("drct")) is None else int(_num(r.get("drct"))),
            None if _num(r.get("sknt")) is None else int(round(_num(r.get("sknt")))),
            None if _num(r.get("gust")) is None else int(round(_num(r.get("gust")))),
            vis, ceil, flight_category(vis, ceil), None if wx in ("M", "") else wx, "iem", now,
        ))
    return rows


def _month_chunks(start: dt.date, end: dt.date):
    """Yield [a, b) date pairs, one per calendar month, covering [start, end]."""
    a = start
    while a <= end:
        nxt = (a.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        b = min(nxt, end + dt.timedelta(days=1))
        yield a, b
        a = b


def backfill_metar(conn, start: dt.date, end: dt.date) -> int:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    n = 0
    for a, b in _month_chunks(start, end):
        rows = parse_iem_csv(fetch_iem_csv(a, b), now)
        conn.executemany("INSERT OR REPLACE INTO metar_hist VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        conn.commit()
        log.info("IEM %s..%s: %d obs", a, b, len(rows))
        n += len(rows)
        time.sleep(2)
    return n


# ---------- TC signals (HKO warning database) ----------

def parse_tc_dat(text: str) -> list[tuple]:
    """Parse HKO tc.dat (tab-separated). Columns (0-based): 0 tc_id, 1 class, 2 name, 3 signal, 4 direction,
    5 start HHMM, 6 start day, 7 start month, 8 start year, 10 end HHMM, 11 end day, 12 end month, 13 end year."""
    out = []
    for line in text.lstrip("﻿").splitlines():
        f = line.split("\t")
        if len(f) < 14 or "UUUU" in line:
            continue
        try:
            s = _hkt(f[8], f[7], f[6], f[5])
            e = _hkt(f[13], f[12], f[11], f[10])
        except ValueError:
            continue
        signal = "MSN" if f[1] == "MSN" else f[3]
        out.append((f[0], None if f[2] in ("X", "NIL") else f[2], signal, None if f[4] == "X" else f[4],
                    s, e, "hko_warndb"))
    return out


def _hkt(y, mo, d, hhmm) -> str:
    hhmm = hhmm.zfill(4)
    return dt.datetime(int(y), int(mo), int(d), int(hhmm[:2]), int(hhmm[2:]), tzinfo=HKT).isoformat()


def backfill_tc_signals(conn) -> int:
    r = requests.get(HKO_TC_URL, headers=HEADERS, timeout=60)
    r.raise_for_status()
    rows = parse_tc_dat(r.text)
    conn.executemany("INSERT OR REPLACE INTO tc_signals VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    return len(rows)


# ---------- CLI ----------

def default_window(conn) -> tuple[dt.date, dt.date]:
    """Incremental: from the last day already in metar_hist (re-fetched, it was partial), else from the first flight date - 1."""
    (last,) = conn.execute("SELECT MAX(report_time) FROM metar_hist").fetchone()
    if last:
        start = dt.date.fromisoformat(last[:10])
    else:
        (min_date,) = conn.execute("SELECT MIN(date) FROM flights").fetchone()
        start = dt.date.fromisoformat(min_date) - dt.timedelta(days=1) if min_date else dt.date.today() - dt.timedelta(days=92)
    return start, dt.datetime.now(dt.timezone.utc).date()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=dt.date.fromisoformat)
    ap.add_argument("--end", type=dt.date.fromisoformat)
    ap.add_argument("--metar-only", action="store_true")
    ap.add_argument("--tc-only", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    conn = connect()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    ok = True
    if not a.tc_only:
        start, end = default_window(conn)
        start, end = a.start or start, a.end or end
        try:
            n = backfill_metar(conn, start, end)
            lo, hi, tot = conn.execute("SELECT MIN(report_time), MAX(report_time), COUNT(*) FROM metar_hist").fetchone()
            log.info("metar_hist: fetched %d, table now %d rows %s..%s", n, tot, lo, hi)
            conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, "metar_hist", f"{start}..{end}: {n} rows"))
        except (RuntimeError, requests.RequestException) as e:  # IEM is often over capacity; keep whatever landed
            ok = False
            log.error("metar_hist backfill failed: %s", e)
            conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, "metar_hist", f"ERROR {e}"))
    if not a.metar_only:
        try:
            n = backfill_tc_signals(conn)
            recent = conn.execute("SELECT signal, start_ts, end_ts FROM tc_signals WHERE start_ts >= '2026-05-01' ORDER BY start_ts").fetchall()
            log.info("tc_signals: %d rows total; since 2026-05: %s", n, recent)
            conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, "tc_signals", f"{n} rows"))
        except requests.RequestException as e:
            ok = False
            log.error("tc_signals backfill failed: %s", e)
            conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, "tc_signals", f"ERROR {e}"))
    conn.commit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
