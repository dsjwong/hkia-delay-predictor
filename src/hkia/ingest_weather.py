"""Ingest HKO current readings + warnings and VHHH METAR into SQLite.

Sources (all free, no key):
  HKO:   https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType={rhrread,warnsum}&lang=en
  METAR: https://aviationweather.gov/api/data/metar?ids=VHHH&format=json&hours=24
"""
import datetime as dt
import json
import logging
import sys
import time

import requests

from .db import connect

log = logging.getLogger("hkia.weather")
HKO_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
METAR_URL = "https://aviationweather.gov/api/data/metar"
HEADERS = {"User-Agent": "hkia-delay-predictor/0.1 (+https://github.com/dsjwong/hkia-delay-predictor)"}


def _get_json(url, params, retries: int = 2, backoff: float = 5.0):
    """GET JSON; retry once (with backoff) on 5xx / connection errors — aviationweather.gov returns 502 now and then."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=60)
            if r.status_code >= 500 and attempt < retries:
                raise requests.HTTPError(f"{r.status_code} from {url}", response=r)
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            if attempt >= retries:
                raise
            log.warning("%s attempt %d failed (%s); retrying in %.0fs", url, attempt, e, backoff * attempt)
            time.sleep(backoff * attempt)


def ingest_hko_current(conn, now: str) -> int:
    cur = _get_json(HKO_URL, {"dataType": "rhrread", "lang": "en"})
    conn.execute("INSERT OR REPLACE INTO hko_current VALUES (?,?,?)",
                 (now, cur.get("updateTime"), json.dumps(cur, ensure_ascii=False)))
    conn.commit()
    return 1


def ingest_hko_warnings(conn, now: str) -> int:
    warn = _get_json(HKO_URL, {"dataType": "warnsum", "lang": "en"})
    codes = ",".join(sorted(warn.keys())) if isinstance(warn, dict) else ""
    conn.execute("INSERT OR REPLACE INTO hko_warnings VALUES (?,?,?,?)",
                 (now, len(warn) if isinstance(warn, dict) else 0, codes, json.dumps(warn, ensure_ascii=False)))
    conn.commit()
    return len(warn) if isinstance(warn, dict) else 0


def ceiling_ft(clouds) -> int | None:
    bases = [c.get("base") for c in (clouds or []) if c.get("cover") in ("BKN", "OVC", "OVX") and c.get("base") is not None]
    return min(bases) if bases else None


def ingest_metar(conn, now: str, hours: int = 24) -> int:
    obs = _get_json(METAR_URL, {"ids": "VHHH", "format": "json", "hours": hours})
    rows = [(o["reportTime"], o["rawOb"], o.get("temp"), o.get("dewp"), o.get("wdir"), o.get("wspd"),
             o.get("wgst"), str(o.get("visib")) if o.get("visib") is not None else None,
             ceiling_ft(o.get("clouds")), o.get("fltCat"), o.get("wxString"), now) for o in obs]
    before = conn.execute("SELECT COUNT(*) FROM metar").fetchone()[0]
    conn.executemany("INSERT OR IGNORE INTO metar VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM metar").fetchone()[0] - before


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    conn = connect()
    # Each source fails soft (WARNING + ingest_log row) so one flaky upstream never fails the cron; always exit 0.
    for name, fn in (("hko_current", ingest_hko_current), ("hko_warnings", ingest_hko_warnings), ("metar", ingest_metar)):
        try:
            res = fn(conn, now)
            log.info("%s: %s", name, res)
            conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, name, str(res)))
        except (requests.RequestException, ValueError) as e:  # ValueError: non-JSON body
            log.warning("%s failed (skipped this run): %s", name, e)
            conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (now, name, f"ERROR {e}"))
    conn.commit()
    for t in ("hko_current", "hko_warnings", "metar"):
        log.info("%s: %d rows", t, conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
