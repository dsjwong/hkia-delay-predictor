"""Compact the `predictions` table: keep, per flight (date, flight_no, scheduled_ts), the FIRST score, the LATEST score,
at most one score per clock hour (UTC) in between (the last one of each hour), and -- when the flight has departed --
the last score before actual_ts (what `hkia.evaluate` uses). Everything else is deleted; then VACUUM.

Usage: python -m hkia.compact_predictions [--no-vacuum] [--dry-run]

Idempotent and cheap (one window query, 58k rows in well under a second), so it runs in the daily backfill workflow.
It is the retroactive twin of the write-time rule in `hkia.predict.write_predictions` (which additionally skips scores
that moved |p_delay15| < 0.01 and |pred_delay_min| < 1 vs the latest stored row -- a write-time rule only, so that the
compaction stays a pure function of the stored rows and re-running it is a no-op).
"""
import argparse
import logging
import sys
from pathlib import Path

from .db import DB_PATH, connect

log = logging.getLogger("hkia.compact_predictions")

KEEP = """
WITH x AS (
  SELECT p.rowid AS rid,
         ROW_NUMBER() OVER (w ORDER BY p.scored_at)      AS rn_first,
         ROW_NUMBER() OVER (w ORDER BY p.scored_at DESC) AS rn_last,
         ROW_NUMBER() OVER (PARTITION BY p.date, p.flight_no, p.scheduled_ts, substr(p.scored_at, 1, 13)
                            ORDER BY p.scored_at DESC)    AS rn_hour,
         ROW_NUMBER() OVER (PARTITION BY p.date, p.flight_no, p.scheduled_ts,
                                         (f.actual_ts IS NOT NULL AND datetime(p.scored_at) <= datetime(f.actual_ts))
                            ORDER BY p.scored_at DESC)    AS rn_pre,
         (f.actual_ts IS NOT NULL AND datetime(p.scored_at) <= datetime(f.actual_ts)) AS pre
  FROM predictions p
  LEFT JOIN flights f ON f.date = p.date AND f.flight_no = p.flight_no AND f.scheduled_ts = p.scheduled_ts
  WINDOW w AS (PARTITION BY p.date, p.flight_no, p.scheduled_ts)
)
SELECT rid FROM x WHERE rn_first = 1 OR rn_last = 1 OR rn_hour = 1 OR (pre AND rn_pre = 1)
"""


def compact(conn, vacuum: bool = True, dry_run: bool = False) -> dict:
    """Delete the rows not selected by KEEP. Returns {'before': n, 'after': n, 'deleted': n}."""
    if not conn.execute("SELECT name FROM sqlite_master WHERE name='predictions'").fetchone():
        return {"before": 0, "after": 0, "deleted": 0}
    before = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    if dry_run:
        keep = conn.execute(f"SELECT COUNT(*) FROM ({KEEP})").fetchone()[0]
        return {"before": before, "after": keep, "deleted": before - keep}
    conn.execute("CREATE TEMP TABLE _keep AS " + KEEP)
    conn.execute("DELETE FROM predictions WHERE rowid NOT IN (SELECT rid FROM _keep)")
    conn.execute("DROP TABLE _keep")
    conn.execute("DROP INDEX IF EXISTS ix_pred_flight")   # duplicated the primary-key autoindex
    after = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    conn.commit()
    if vacuum and before != after:
        conn.execute("VACUUM")
    return {"before": before, "after": after, "deleted": before - after}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-vacuum", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="report what would be deleted, change nothing")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    size0 = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
    conn = connect()
    res = compact(conn, vacuum=not a.no_vacuum, dry_run=a.dry_run)
    conn.close()
    size1 = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
    log.info("predictions rows %d -> %d (%d deleted%s); db %.1f MB -> %.1f MB", res["before"], res["after"],
             res["deleted"], " [dry run]" if a.dry_run else "", size0 / 1e6, size1 / 1e6)
    return 0


if __name__ == "__main__":
    sys.exit(main())
