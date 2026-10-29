"""hkia.export_json.cancellations: counts, per-cell rates, the ordinary/disruption split and Wilson intervals."""
import datetime as dt
import sqlite3

import pytest

from hkia import db as _db
from hkia import export_json as E

NOW = dt.datetime(2026, 8, 10, 6, 0, tzinfo=dt.timezone.utc)
HKT = dt.timezone(dt.timedelta(hours=8))


@pytest.fixture()
def conn(tmp_path):
    path = tmp_path / "c.db"
    c = sqlite3.connect(path)
    c.executescript(_db.SCHEMA)
    rows = []

    def day(date, n, cancel_every=None, n_cancel=0, airline="CPA", hour0=8):
        for i in range(n):
            t = dt.datetime.fromisoformat(date).replace(hour=hour0, tzinfo=HKT) + dt.timedelta(minutes=5 * i)
            cancelled = i < n_cancel
            rows.append((date, f"XX {date[-2:]}{i}", t.strftime("%H:%M"), airline if i % 2 else "HKE", "TPE", t.isoformat(),
                         None if cancelled else (t + dt.timedelta(minutes=5)).isoformat(),
                         "Cancelled" if cancelled else "Dep", "x", "x"))
    day("2026-08-03", 100, n_cancel=1)                 # ordinary
    day("2026-08-04", 100, n_cancel=0)                 # ordinary
    day("2026-08-05", 100, n_cancel=20)                # disruption day (20 % cancelled), no signal
    day("2026-08-06", 100, n_cancel=40)                # under signal 8 below
    day("2026-08-10", 100, n_cancel=50)                # today (HKT) -> excluded: incomplete day
    c.executemany("INSERT INTO flights (date, flight_no, scheduled_time, airline, destination, scheduled_ts, actual_ts, status_raw, "
                  "first_seen_at, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    c.execute("INSERT INTO tc_signals (tc_id, tc_name, signal, direction, start_ts, end_ts, source) VALUES "
              "('202699','TEST','8','NW','2026-08-06T00:00:00+08:00','2026-08-07T00:00:00+08:00','x')")
    c.commit()
    c.close()
    return E._conn(path)


def test_counts_exclude_the_incomplete_day_and_split_ordinary_from_disruption(conn):
    out = E.cancellations(conn, NOW)
    s = out["summary"]
    assert (s["date_min"], s["date_max"]) == ("2026-08-03", "2026-08-06") and s["n_flights"] == 400
    assert s["n_cancelled"] == 61 and s["disruption_days"] == ["2026-08-05", "2026-08-06"]
    assert s["ordinary"]["n"] == 200 and s["ordinary"]["n_cancelled"] == 1
    assert s["top3_days_share"] == pytest.approx(1.0 - 0 / 61, abs=1e-3)       # three days hold every cancellation
    assert s["share_on_disruption_or_signal3"] == pytest.approx(60 / 61, abs=1e-3)


def test_by_signal_cells_carry_n_and_an_interval(conn):
    by = {r["signal"]: r for r in E.cancellations(conn, NOW)["by_signal"]}
    assert by[0]["n"] == 300 and by[0]["n_cancelled"] == 21 and by[8]["n"] == 100 and by[8]["rate"] == 0.4
    lo, hi = by[8]["ci"]
    assert lo < 0.4 < hi and 0.3 < lo and hi < 0.5
    assert by[8]["label"] == "No. 8" and by[8]["n_days"] == 1


def test_by_hour_and_airline_use_ordinary_days_only(conn):
    out = E.cancellations(conn, NOW)
    assert sum(r["n"] for r in out["by_hour"]) == 200 and sum(r["n_cancelled"] for r in out["by_hour"]) == 1
    assert len(out["by_hour"]) == 24 and out["by_airline"] == []             # no airline reaches MIN_CELL_AIRLINE here


def test_days_table_is_sorted_and_names_the_leading_airline(conn):
    days = E.cancellations(conn, NOW)["days"]
    assert [d["date"] for d in days] == ["2026-08-06", "2026-08-05", "2026-08-03"]
    assert days[0]["signal"] == 8 and days[1]["signal"] == 0 and days[1]["rate"] == 0.2


def test_wilson_interval_edges():
    assert E.wilson(0, 0) is None
    lo, hi = E.wilson(0, 50)
    assert lo == 0.0 and 0.0 < hi < 0.1
    lo, hi = E.wilson(50, 50)
    assert hi == 1.0 and lo > 0.9


def test_empty_db_is_a_clean_empty_state(tmp_path):
    p = tmp_path / "e.db"
    c = sqlite3.connect(p)
    c.executescript(_db.SCHEMA)
    c.commit()
    c.close()
    assert E.cancellations(E._conn(p), NOW) == {"summary": None}
