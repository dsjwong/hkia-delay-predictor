"""Aircraft rotations: which inbound arrival feeds which HKIA departure. Phase 1 of the turnaround signal.

Nothing in the departures feed names the aircraft — no tail number, no inbound flight — so the link has to be inferred.
Two independent methods write into the same `aircraft_links` table, each row tagged with its `method`:

**`adsb_hex`** — ground truth, but only from 2026-08-20 forward. `adsb_snapshots` records the ICAO 24-bit address (`hex`)
of every aircraft within 100 nm. A hex seen transmitting an arrival callsign and later a departure callsign is the same
airframe turning around. Precise, and it carries the registration; limited by the 100 nm ring (an aircraft that lands
between two cron runs, or departs and clears the ring before the next poll, is simply not seen) and by having no history.

**`stand_gate`** — a proxy that works across the whole 91-day backfill. Arrivals publish `stand` (`N36`, `D214`, `W65`);
departures publish `gate` (`36`, `214`, `65`). They are the same numbering with an apron-area letter on the arrivals side:
on 2026-08-19, 373 of 438 departures sat at a position that also took an arrival, and the per-position counts line up
almost exactly (position 10: 9 arrivals / 9 departures, 68: 8/8, 209: 7/7, 214: 7/7). Positions with arrivals but no
departures are all remote stands (`S102`, `W121L`, `D3xx`) whose passengers leave from bus gates (`227-230`, `511-524`),
which is exactly what you would expect. So: pair each arrival at a position with the first departure from that position
after it and before the *next* arrival there. Conservative — if two departures fall inside one arrival's window only the
first is linked, because the second could be an aircraft towed in.
The proxy's failure mode is towing: an aircraft moved off-stand and replaced by another between the two events produces
a wrong pair. `airline_agreement()` measures it (linked arrival and departure should usually be the same carrier), and
once ~2 weeks of `adsb_hex` links exist the two methods can be compared head-to-head on the same departures.

Both are best-effort and incremental: the cron re-links yesterday and today every run (idempotent upsert), and coverage
per day goes into `ingest_log` under job `rotations`.

Usage:
  python -m hkia.rotations                 # yesterday + today (cron)
  python -m hkia.rotations --all           # every day in the flights window (stand_gate over the backfill)
  python -m hkia.rotations 2026-08-19
  python -m hkia.rotations --coverage      # print the coverage + airline-agreement report, link nothing
"""
import argparse
import datetime as dt
import logging
import re
import sys

from .adsb import parse_callsign
from .db import connect

log = logging.getLogger("hkia.rotations")
HKT = dt.timezone(dt.timedelta(hours=8))

LINKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS aircraft_links (
    date               TEXT NOT NULL,  -- HKT calendar day of the departure (== flights.date)
    dep_flight_no      TEXT NOT NULL,  -- }
    dep_scheduled_time TEXT NOT NULL,  -- } together with `date`: the flights primary key
    method             TEXT NOT NULL,  -- 'adsb_hex' (ground truth, 2026-08-20 ->) or 'stand_gate' (proxy, whole window)
    arr_date           TEXT NOT NULL,  -- }
    arr_flight_no      TEXT NOT NULL,  -- } together: the arrivals primary key
    arr_scheduled_time TEXT NOT NULL,  -- }
    hex                TEXT,           -- adsb_hex only
    registration       TEXT,           -- adsb_hex only, and only when a readsb-family provider served the frame
    position           TEXT,           -- stand_gate only: the shared stand/gate number
    arr_actual_ts      TEXT,           -- inbound on blocks (or touchdown when that is all we have)
    arr_estimated_ts   TEXT,           -- the airport's live estimate -- the only inbound time known *before* it lands
    dep_scheduled_ts   TEXT NOT NULL,
    turnaround_min     REAL,           -- dep_scheduled_ts - arr_actual_ts, minutes; NULL until the inbound is on blocks
    confidence         REAL NOT NULL,  -- 1.0 unambiguous, lower when several candidates fitted
    built_at           TEXT NOT NULL,
    PRIMARY KEY (date, dep_flight_no, dep_scheduled_time, method)
);
CREATE INDEX IF NOT EXISTS links_arr ON aircraft_links(arr_date, arr_flight_no, arr_scheduled_time);
CREATE INDEX IF NOT EXISTS links_method ON aircraft_links(method, date);
"""

MIN_TURN_MIN = 25          # below this it is not a turnaround, it is two aircraft sharing a position
MAX_TURN_MIN = 12 * 60     # beyond this the aircraft has almost certainly been towed away and back
LONG_TURN_MIN = 6 * 60     # a long sit is plausible but weaker evidence -> confidence penalty
_POS_RE = re.compile(r"^[A-Z]*0*(\d+)[LR]?$")

UPSERT = """
INSERT INTO aircraft_links (date, dep_flight_no, dep_scheduled_time, method, arr_date, arr_flight_no, arr_scheduled_time,
                            hex, registration, position, arr_actual_ts, arr_estimated_ts, dep_scheduled_ts,
                            turnaround_min, confidence, built_at)
VALUES (:date, :dep_flight_no, :dep_scheduled_time, :method, :arr_date, :arr_flight_no, :arr_scheduled_time,
        :hex, :registration, :position, :arr_actual_ts, :arr_estimated_ts, :dep_scheduled_ts,
        :turnaround_min, :confidence, :built_at)
ON CONFLICT(date, dep_flight_no, dep_scheduled_time, method) DO UPDATE SET
    arr_date=excluded.arr_date, arr_flight_no=excluded.arr_flight_no, arr_scheduled_time=excluded.arr_scheduled_time,
    hex=COALESCE(excluded.hex, aircraft_links.hex),
    registration=COALESCE(excluded.registration, aircraft_links.registration),
    position=COALESCE(excluded.position, aircraft_links.position),
    arr_actual_ts=COALESCE(excluded.arr_actual_ts, aircraft_links.arr_actual_ts),
    arr_estimated_ts=excluded.arr_estimated_ts,
    turnaround_min=COALESCE(excluded.turnaround_min, aircraft_links.turnaround_min),
    confidence=excluded.confidence, built_at=excluded.built_at
WHERE excluded.arr_date IS NOT aircraft_links.arr_date
   OR excluded.arr_flight_no IS NOT aircraft_links.arr_flight_no
   OR excluded.arr_scheduled_time IS NOT aircraft_links.arr_scheduled_time
   OR excluded.arr_estimated_ts IS NOT aircraft_links.arr_estimated_ts
   OR excluded.confidence IS NOT aircraft_links.confidence
   OR COALESCE(excluded.arr_actual_ts, aircraft_links.arr_actual_ts) IS NOT aircraft_links.arr_actual_ts
   OR COALESCE(excluded.turnaround_min, aircraft_links.turnaround_min) IS NOT aircraft_links.turnaround_min
   OR COALESCE(excluded.hex, aircraft_links.hex) IS NOT aircraft_links.hex
   OR COALESCE(excluded.registration, aircraft_links.registration) IS NOT aircraft_links.registration
   OR COALESCE(excluded.position, aircraft_links.position) IS NOT aircraft_links.position
"""  # WHERE: re-linking the same pair must not rewrite the row -> the 30-min cron leaves no git delta

# A departure's stand_gate pairing can change during the day as gates are (re)assigned, so the rebuild is authoritative:
# links this build no longer produces are dropped. adsb_hex links are NEVER dropped — adsb_snapshots is pruned to 30 days,
# so an old ADS-B link cannot be rebuilt once its evidence has aged out.
DELETE_STALE = "DELETE FROM aircraft_links WHERE date=? AND method='stand_gate'"


# ------------------------------------------------------------------ helpers
def _dt(s: str | None) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def _min(a: dt.datetime | None, b: dt.datetime | None) -> float | None:
    return None if a is None or b is None else (b - a).total_seconds() / 60.0


def position(s: str | None) -> str | None:
    """`N36` / `D214` / `W123R` / `36` -> `36` / `214` / `123` / `36`. Non-numeric or blank -> None."""
    m = _POS_RE.match((s or "").strip().upper())
    return m.group(1).lstrip("0") or None if m else None


def _days(date: dt.date, back: int = 1, fwd: int = 1) -> list[str]:
    return [(date + dt.timedelta(days=i)).isoformat() for i in range(-back, fwd + 1)]


def load_arrivals(conn, dates: list[str]) -> list[dict]:
    """Arrival rows for the given HKIA day-labels, each with its best-known event time."""
    q = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT date, flight_no, scheduled_time, airline, origin, scheduled_ts, actual_ts, landed_ts, estimated_ts, stand "
        f"FROM arrivals WHERE date IN ({q})", dates).fetchall()
    out = []
    for d, fno, stime, airline, origin, sched, actual, landed, est, stand in rows:
        on_blocks = _dt(actual) or _dt(landed)
        out.append({"date": d, "flight_no": fno, "scheduled_time": stime, "airline": airline, "origin": origin,
                    "scheduled_ts": sched, "actual_ts": actual or landed, "estimated_ts": est, "stand": stand,
                    "position": position(stand), "event": on_blocks or _dt(est) or _dt(sched), "on_blocks": on_blocks})
    return out


def load_departures(conn, dates: list[str]) -> list[dict]:
    """Departure rows for the given HKIA day-labels. Cancelled flights never turn an aircraft around -> excluded."""
    q = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT date, flight_no, scheduled_time, airline, destination, scheduled_ts, actual_ts, estimated_ts, gate, status_raw "
        f"FROM flights WHERE date IN ({q})", dates).fetchall()
    out = []
    for d, fno, stime, airline, dest, sched, actual, est, gate, status in rows:
        if (status or "").strip().lower() == "cancelled":
            continue
        out.append({"date": d, "flight_no": fno, "scheduled_time": stime, "airline": airline, "destination": dest,
                    "scheduled_ts": sched, "actual_ts": actual, "estimated_ts": est, "gate": gate,
                    "position": position(gate), "event": _dt(actual) or _dt(est) or _dt(sched)})
    return out


def icao_map(conn) -> dict[str, str]:
    """IATA prefix of flight_no -> the most common ICAO `airline` code seen with it (CX -> CPA), from both tables."""
    counts: dict[tuple[str, str], int] = {}
    for table in ("flights", "arrivals"):
        try:
            rows = conn.execute(f"SELECT flight_no, airline, COUNT(*) FROM {table} "
                                f"WHERE airline IS NOT NULL GROUP BY 1,2").fetchall()
        except Exception:  # noqa: BLE001 — arrivals may not exist yet
            continue
        for fno, airline, n in rows:
            iata = (fno or "").split()[0].upper()
            if iata:
                counts[(iata, airline.upper())] = counts.get((iata, airline.upper()), 0) + n
    best: dict[str, tuple[int, str]] = {}
    for (iata, icao), n in counts.items():
        if n > best.get(iata, (0, ""))[0]:
            best[iata] = (n, icao)
    return {k: v[1] for k, v in best.items()}


def _key(row: dict, m: dict[str, str]) -> tuple[str, int] | None:
    """(ICAO airline, flight number) for a flights/arrivals row — the same key a callsign parses to."""
    num = re.search(r"(\d+)", row["flight_no"] or "")
    if not num:
        return None
    icao = (row["airline"] or m.get((row["flight_no"] or "").split()[0].upper()) or "").upper()
    return (icao, int(num.group(1))) if icao else None


def _link_row(dep: dict, arr: dict, method: str, built_at: str, confidence: float,
              hexid: str | None = None, reg: str | None = None, pos: str | None = None) -> dict:
    return {"date": dep["date"], "dep_flight_no": dep["flight_no"], "dep_scheduled_time": dep["scheduled_time"],
            "method": method, "arr_date": arr["date"], "arr_flight_no": arr["flight_no"],
            "arr_scheduled_time": arr["scheduled_time"], "hex": hexid, "registration": reg, "position": pos,
            "arr_actual_ts": arr["actual_ts"], "arr_estimated_ts": arr["estimated_ts"],
            "dep_scheduled_ts": dep["scheduled_ts"],
            "turnaround_min": _min(arr["on_blocks"], _dt(dep["scheduled_ts"])),
            "confidence": confidence, "built_at": built_at}


# ------------------------------------------------------------------ method: stand <-> gate
def link_stand_gate(conn, date: dt.date, built_at: str) -> list[dict]:
    """Pair each arrival at a stand with the first departure from the same-numbered gate before the next arrival there."""
    arrivals = [a for a in load_arrivals(conn, _days(date, back=1, fwd=0)) if a["position"] and a["on_blocks"]]
    departures = [d for d in load_departures(conn, _days(date, back=0, fwd=1))
                  if d["position"] and d["event"] and d["date"] == date.isoformat()]
    by_pos_a: dict[str, list[dict]] = {}
    by_pos_d: dict[str, list[dict]] = {}
    for a in arrivals:
        by_pos_a.setdefault(a["position"], []).append(a)
    for d in departures:
        by_pos_d.setdefault(d["position"], []).append(d)

    out, used = [], set()
    for pos, arrs in by_pos_a.items():
        deps = sorted(by_pos_d.get(pos, []), key=lambda r: r["event"])
        if not deps:
            continue
        arrs = sorted(arrs, key=lambda r: r["on_blocks"])
        for i, a in enumerate(arrs):
            t0 = a["on_blocks"]
            nxt = arrs[i + 1]["on_blocks"] if i + 1 < len(arrs) else None
            cands = [d for d in deps
                     if id(d) not in used
                     and MIN_TURN_MIN <= (d["event"] - t0).total_seconds() / 60 <= MAX_TURN_MIN
                     and (nxt is None or d["event"] < nxt)]
            if not cands:
                continue
            d = cands[0]
            used.add(id(d))
            gap = (d["event"] - t0).total_seconds() / 60
            conf = 1.0 if len(cands) == 1 else 0.6
            if gap > LONG_TURN_MIN:
                conf *= 0.6
            out.append(_link_row(d, a, "stand_gate", built_at, round(conf, 2), pos=pos))
    return out


# ------------------------------------------------------------------ method: ADS-B hex
def _snapshot_callsigns(conn, date: dt.date) -> dict[str, tuple[str | None, dict[str, dt.datetime]]]:
    """{hex: (registration, {callsign: last time seen, HKT})} over the target HKT day and the one before (overnight rotations)."""
    lo = dt.datetime.combine(date - dt.timedelta(days=1), dt.time(0), HKT).astimezone(dt.timezone.utc)
    hi = dt.datetime.combine(date + dt.timedelta(days=1), dt.time(0), HKT).astimezone(dt.timezone.utc)
    rows = conn.execute(
        "SELECT hex, callsign, MAX(registration), MAX(fetched_at) FROM adsb_snapshots "
        "WHERE fetched_at >= ? AND fetched_at < ? AND callsign IS NOT NULL AND callsign != '' GROUP BY hex, callsign",
        (lo.isoformat(timespec="seconds"), hi.isoformat(timespec="seconds"))).fetchall()
    seen: dict[str, tuple[str | None, dict[str, dt.datetime]]] = {}
    for hexid, cs, reg, last in rows:
        entry = seen.setdefault(hexid, (None, {}))
        last_hkt = _dt(last)
        if last_hkt:
            entry[1][cs] = last_hkt.astimezone(HKT)
        if reg and not entry[0]:
            seen[hexid] = (reg, entry[1])
    return seen


def link_adsb(conn, date: dt.date, built_at: str) -> list[dict]:
    """Link via a hex seen under an arrival callsign and later under a departure callsign."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='adsb_snapshots'").fetchone():
        return []
    seen = _snapshot_callsigns(conn, date)
    if not seen:
        return []
    m = icao_map(conn)
    days = _days(date, back=1, fwd=1)
    arr_idx: dict[tuple[str, int], list[dict]] = {}
    dep_idx: dict[tuple[str, int], list[dict]] = {}
    for a in load_arrivals(conn, days):
        k = _key(a, m)
        if k and a["event"]:
            arr_idx.setdefault(k, []).append(a)
    for d in load_departures(conn, days):
        k = _key(d, m)
        if k and d["event"] and d["date"] == date.isoformat():
            dep_idx.setdefault(k, []).append(d)

    out = []
    for hexid, (reg, callsigns) in seen.items():
        arr_hits, dep_hits = [], []
        for cs, last_seen in callsigns.items():
            p = parse_callsign(cs)
            if not p:
                continue
            prefix, num, _sfx = p
            icao = prefix if len(prefix) == 3 else m.get(prefix)
            if not icao:
                continue
            for a in arr_idx.get((icao, num), []):
                if abs((a["event"] - last_seen).total_seconds()) <= 4 * 3600:
                    arr_hits.append(a)
            for d in dep_idx.get((icao, num), []):
                if abs((d["event"] - last_seen).total_seconds()) <= 4 * 3600:
                    dep_hits.append(d)
        if not arr_hits or not dep_hits:
            continue
        for d in dep_hits:
            fits = [a for a in arr_hits if a["event"] and MIN_TURN_MIN <= (d["event"] - a["event"]).total_seconds() / 60 <= MAX_TURN_MIN]
            if not fits:
                continue
            a = max(fits, key=lambda r: r["event"])          # the inbound immediately before this departure
            conf = 1.0 if len(fits) == 1 else 0.8            # hex identity is exact; only "which inbound" is ambiguous
            out.append(_link_row(d, a, "adsb_hex", built_at, conf, hexid=hexid, reg=reg,
                                 pos=d["position"] or a["position"]))
    return out


# ------------------------------------------------------------------ driver
def build(conn, dates: list[dt.date], now: dt.datetime | None = None) -> dict[str, int]:
    """Build both methods for the given dates. Returns per-method link counts plus departures covered."""
    conn.executescript(LINKS_SCHEMA)
    built_at = (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")
    stats = {"adsb_hex": 0, "stand_gate": 0, "departures": 0, "covered": 0}
    for date in dates:
        ds = date.isoformat()
        sg = link_stand_gate(conn, date, built_at)
        rows = sg + link_adsb(conn, date, built_at)
        keep = [f"{r['dep_flight_no']}|{r['dep_scheduled_time']}" for r in sg]
        conn.execute(DELETE_STALE + (f" AND (dep_flight_no || '|' || dep_scheduled_time) NOT IN ({','.join('?' * len(keep))})"
                                     if keep else ""), [ds, *keep])
        conn.executemany(UPSERT, rows)
        conn.commit()
        for r in rows:
            stats[r["method"]] += 1
        n_dep = conn.execute("SELECT COUNT(*) FROM flights WHERE date=? AND COALESCE(status_raw,'')!='Cancelled'", (ds,)).fetchone()[0]
        n_cov = conn.execute("SELECT COUNT(DISTINCT dep_flight_no || dep_scheduled_time) FROM aircraft_links WHERE date=?", (ds,)).fetchone()[0]
        stats["departures"] += n_dep
        stats["covered"] += n_cov
        log.info("%s: %d links (%d departures, %d linked = %.0f%%)", ds, len(rows), n_dep, n_cov,
                 100 * n_cov / n_dep if n_dep else 0)
    conn.execute("INSERT INTO ingest_log VALUES (?,?,?)", (
        built_at, "rotations",
        f"{len(dates)} dates, {stats['covered']}/{stats['departures']} departures linked "
        f"(adsb_hex {stats['adsb_hex']}, stand_gate {stats['stand_gate']})"))
    conn.commit()
    return stats


def airline_agreement(conn, method: str = "stand_gate") -> tuple[int, int]:
    """(pairs whose arrival and departure are the same carrier, pairs total) — the sanity check on the stand_gate proxy.
    An aircraft normally arrives and departs for the same airline, so a low rate means the pairing is wrong a lot."""
    row = conn.execute("""
        SELECT SUM(CASE WHEN a.airline = f.airline THEN 1 ELSE 0 END), COUNT(*)
        FROM aircraft_links l
        JOIN flights  f ON f.date = l.date AND f.flight_no = l.dep_flight_no AND f.scheduled_time = l.dep_scheduled_time
        JOIN arrivals a ON a.date = l.arr_date AND a.flight_no = l.arr_flight_no AND a.scheduled_time = l.arr_scheduled_time
        WHERE l.method = ? AND a.airline IS NOT NULL AND f.airline IS NOT NULL""", (method,)).fetchone()
    return (row[0] or 0, row[1] or 0)


def coverage(conn) -> str:
    """Human-readable coverage report — what phase 2 can actually be trained on."""
    conn.executescript(LINKS_SCHEMA)
    lines = []
    for method in ("stand_gate", "adsb_hex"):
        n, days, turn = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT date), AVG(turnaround_min) FROM aircraft_links WHERE method=?", (method,)).fetchone()
        same, tot = airline_agreement(conn, method)
        lines.append(f"{method:>10}: {n:>6} links over {days or 0:>3} days, mean turnaround "
                     f"{turn:.0f} min, airline agreement {100 * same / tot:.1f}% ({same}/{tot})"
                     if n else f"{method:>10}: no links yet")
    dep = conn.execute("SELECT COUNT(*) FROM flights WHERE COALESCE(status_raw,'')!='Cancelled'").fetchone()[0]
    cov = conn.execute("SELECT COUNT(DISTINCT date || dep_flight_no || dep_scheduled_time) FROM aircraft_links").fetchone()[0]
    lines.append(f"{'overall':>10}: {cov}/{dep} departures have an inbound link ({100 * cov / dep:.1f}%)" if dep else "no departures")
    return "\n".join(lines)


def default_dates() -> list[dt.date]:
    today = dt.datetime.now(HKT).date()
    return [today - dt.timedelta(days=1), today]


def all_dates(conn) -> list[dt.date]:
    rows = conn.execute("SELECT DISTINCT date FROM flights ORDER BY date").fetchall()
    return [dt.date.fromisoformat(r[0]) for r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dates", nargs="*", help="YYYY-MM-DD; default yesterday + today")
    ap.add_argument("--all", action="store_true", help="every day present in the flights table")
    ap.add_argument("--coverage", action="store_true", help="print the coverage report and exit")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    conn = connect()
    if a.coverage:
        print(coverage(conn))
        return 0
    try:
        dates = all_dates(conn) if a.all else ([dt.date.fromisoformat(x) for x in a.dates] or default_dates())
        stats = build(conn, dates)
        log.info("linked %d/%d departures (adsb_hex %d, stand_gate %d)",
                 stats["covered"], stats["departures"], stats["adsb_hex"], stats["stand_gate"])
    except Exception as e:  # noqa: BLE001 — a feature-source job must never fail the cron
        log.error("rotations failed (skipped this run): %s: %s", type(e).__name__, e)
        conn.execute("INSERT INTO ingest_log VALUES (?,?,?)",
                     (dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rotations", f"ERROR {e}"))
        conn.commit()
    return 0  # fail soft


if __name__ == "__main__":
    sys.exit(main())
