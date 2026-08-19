"""Retention rule of the predictions table: write-time (hkia.predict.write_predictions / decide) and the retroactive
compaction (hkia.compact_predictions). In-memory SQLite, no models."""
import datetime as dt
import sqlite3

import pandas as pd
import pytest

from hkia import db as _db
from hkia.compact_predictions import compact
from hkia.evaluate import matured_predictions
from hkia.predict import PRED_SCHEMA, decide, write_predictions

HKT = dt.timezone(dt.timedelta(hours=8))
UTC = dt.timezone.utc
DAY = "2026-08-17"
SCHED = dt.datetime(2026, 8, 17, 18, 40, tzinfo=HKT)
T0 = dt.datetime(2026, 8, 17, 2, 5, tzinfo=UTC)


def _conn():
    c = sqlite3.connect(":memory:")
    c.executescript(_db.SCHEMA + PRED_SCHEMA)
    return c


def _tgt(p, m, h, flight="CX 255"):
    return pd.DataFrame({"date": [DAY], "flight_no": [flight], "scheduled_ts": [pd.Timestamp(SCHED)],
                         "p_delay15": [p], "pred_delay_min": [m], "features_hash": [h]})


def _rows(c, flight="CX 255"):
    return c.execute("SELECT scored_at, p_delay15, pred_delay_min FROM predictions WHERE flight_no=? ORDER BY scored_at",
                     (flight,)).fetchall()


def _ts(minutes):
    return (T0 + dt.timedelta(minutes=minutes)).isoformat(timespec="seconds")


def test_decide_rules():
    first = _ts(0)
    assert decide(None, None, 0.5, 10, "a", _ts(0)) == "insert"
    # same hour as the first row -> insert (first is protected)
    assert decide(first, (first, 0.5, 10, "a"), 0.7, 20, "b", _ts(30)) == "insert"
    latest = (_ts(30), 0.7, 20, "b")
    assert decide(first, latest, 0.7, 20, "b", _ts(50)) == "skip"                 # unchanged features
    assert decide(first, latest, 0.705, 20.5, "c", _ts(50)) == "skip"             # below both deltas
    assert decide(first, latest, 0.72, 20.5, "c", _ts(50)) == "replace"           # p moved, same hour (02:xx)
    assert decide(first, latest, 0.705, 21.5, "c", _ts(50)) == "replace"          # minutes moved, same hour
    assert decide(first, latest, 0.72, 20.5, "c", _ts(60)) == "insert"            # new clock hour (03:xx)


def test_write_keeps_first_latest_and_one_per_hour():
    c = _conn()
    # run every 30 min for 3 hours; p drifts by 0.05 each run (always above threshold)
    for i in range(7):
        write_predictions(c, _tgt(0.3 + 0.05 * i, 10.0 + 2 * i, f"h{i}"), "v", T0 + dt.timedelta(minutes=30 * i))
    got = _rows(c)
    # hours: 02:05 (first), 02:35 -> kept (first protected), 03:05 replaced by 03:35, 04:05 replaced by 04:35, 05:05 (latest)
    assert [r[0] for r in got] == [_ts(0), _ts(30), _ts(90), _ts(150), _ts(180)]
    assert got[0][1] == pytest.approx(0.3) and got[-1][1] == pytest.approx(0.6)


def test_write_skips_small_deltas_but_not_first():
    c = _conn()
    assert write_predictions(c, _tgt(0.5, 10.0, "a"), "v", T0) == 1                                  # first: always stored
    assert write_predictions(c, _tgt(0.505, 10.5, "b"), "v", T0 + dt.timedelta(hours=2)) == 0         # tiny move: not stored
    assert write_predictions(c, _tgt(0.5, 10.0, "a"), "v", T0 + dt.timedelta(hours=3)) == 0           # unchanged hash
    assert write_predictions(c, _tgt(0.52, 10.0, "c"), "v", T0 + dt.timedelta(hours=4)) == 1          # p moved >= 0.01
    assert write_predictions(c, _tgt(0.52, 11.2, "d"), "v", T0 + dt.timedelta(hours=5)) == 1          # minutes moved >= 1
    assert len(_rows(c)) == 3
    log = c.execute("SELECT detail FROM ingest_log WHERE job='predict'").fetchall()
    assert len(log) == 5 and all("1 scored" in d[0] for d in log)   # skipped scores still count as scored


def test_no_dedupe_appends_everything():
    c = _conn()
    for i in range(3):
        write_predictions(c, _tgt(0.5, 10.0, "a"), "v", T0 + dt.timedelta(minutes=i), dedupe=False)
    assert len(_rows(c)) == 3


def _seed_raw(c, actual=None, n=14):
    """14 raw scores every 20 min from T0 (02:05..06:25 UTC), p = 0.30, 0.31, ..."""
    c.execute("INSERT INTO flights VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (DAY, "CX 255", "18:40", "CPA", None, "TPE", SCHED.isoformat(), actual, None, "x", "T1", "A", "1", "x", "x"))
    c.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?)",
                  [(DAY, "CX 255", SCHED.isoformat(), 0.3 + 0.01 * i, 10.0 + i, "v", f"h{i}", _ts(20 * i)) for i in range(n)])


def test_compact_first_latest_hourly_and_idempotent():
    c = _conn()
    _seed_raw(c)
    res = compact(c, vacuum=False)
    got = [r[0] for r in _rows(c)]
    # 02:05 first, 02:45 (last of 02h), 03:45, 04:45, 05:45, 06:25 latest
    assert got == [_ts(0), _ts(40), _ts(100), _ts(160), _ts(220), _ts(260)]
    assert res == {"before": 14, "after": 6, "deleted": 8}
    assert compact(c, vacuum=False) == {"before": 6, "after": 6, "deleted": 0}   # idempotent
    assert compact(c, vacuum=False, dry_run=True)["deleted"] == 0


def test_compact_protects_last_score_before_departure_and_evaluate_finds_it():
    c = _conn()
    # scheduled 10:40 UTC, departed 10:43 UTC; scores every 20 min 02:05..11:45 -> last pre-departure score is 10:25
    # (i=25), and 10:45 (i=26) is the last of the 10h bucket, so 10:25 survives only thanks to the protection
    actual = (SCHED + dt.timedelta(minutes=3)).isoformat()
    _seed_raw(c, actual=actual, n=30)
    compact(c, vacuum=False)
    got = [r[0] for r in _rows(c)]
    assert _ts(500) in got and _ts(520) in got and _ts(480) not in got
    df = matured_predictions(c, days=30, now=T0 + dt.timedelta(days=1))
    assert len(df) == 1 and df.loc[0, "scored_at"] == pd.Timestamp(_ts(500))
    assert df.loc[0, "p_delay15"] == pytest.approx(0.55)


def test_write_path_output_is_a_fixed_point_of_compaction():
    c = _conn()
    for i in range(12):
        write_predictions(c, _tgt(0.3 + 0.05 * i, 10.0, f"h{i}"), "v", T0 + dt.timedelta(minutes=25 * i))
    n = len(_rows(c))
    assert compact(c, vacuum=False)["deleted"] == 0 and len(_rows(c)) == n
