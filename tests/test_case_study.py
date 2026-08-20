"""hkia.case_study on a synthetic fixture db: hourly aggregation, the TC-signal join, totals and recovery.

No network, no model — the retrospective half needs models/ + xgboost and is exercised by build(..., with_model=False).
The fixture is a miniature typhoon: 5 days of hourly departures, a 1 -> 3 -> 8 -> 1 signal sequence on days 2-4, a
cancellation burst under signal 8, one hour with no schedule at all and one flight delayed past the 600-min clip.
"""
import datetime as dt
import json
import sqlite3

import pandas as pd
import pytest

from hkia import case_study as CS
from hkia.db import SCHEMA

HKT = "Asia/Hong_Kong"
DAYS = ["2026-07-23", "2026-07-24", "2026-07-25", "2026-07-26", "2026-07-27"]
# (signal, start HKT, end HKT) — a compressed version of the real Noul sequence, all inside the fixture window
SIGNALS = [("1", "2026-07-24T20:00:00+08:00", "2026-07-25T10:00:00+08:00"),
           ("3", "2026-07-25T10:00:00+08:00", "2026-07-25T18:00:00+08:00"),
           ("8", "2026-07-25T18:00:00+08:00", "2026-07-26T06:00:00+08:00"),
           ("1", "2026-07-26T06:00:00+08:00", "2026-07-26T12:00:00+08:00")]


def _delay_for(sched: pd.Timestamp, signal: int) -> float | None:
    """Deterministic delay: 5 min normally, 30 under T1/T3, 200 under T8."""
    return {0: 5.0, 1: 30.0, 3: 30.0, 8: 200.0}[signal]


@pytest.fixture
def fixture_db(tmp_path):
    """6 flights an hour, 06:00-21:59 HKT, over 5 days; hour 03:00 is deliberately empty (nothing scheduled)."""
    p = tmp_path / "case.db"
    c = sqlite3.connect(p)
    c.executescript(SCHEMA)
    tc = pd.DataFrame([{"signal": s, "start": pd.Timestamp(a), "end": pd.Timestamp(b), "level": int(s)}
                       for s, a, b in SIGNALS])
    rows, metar = [], []
    n_cancel = 0
    for day in DAYS:
        for hour in range(6, 22):
            for k in range(6):
                sched = pd.Timestamp(f"{day} {hour:02d}:{k * 10:02d}", tz=HKT)
                sig = int(CS.signal_at(pd.Series([sched]), tc).iloc[0])
                # under signal 8 the first three of every six flights are cancelled
                if sig == 8 and k < 3:
                    rows.append((day, f"XX {hour}{k}{day[-2:]}", f"{hour:02d}:{k * 10:02d}", "CPA", "TPE",
                                 sched.isoformat(), None, "Cancelled"))
                    n_cancel += 1
                    continue
                d = _delay_for(sched, sig)
                actual = sched + pd.Timedelta(minutes=d)
                rows.append((day, f"XX {hour}{k}{day[-2:]}", f"{hour:02d}:{k * 10:02d}", "CPA" if k else "HKE", "TPE",
                             sched.isoformat(), actual.isoformat(), f"Dep {actual:%H:%M}"))
        for hour in range(24):  # one hourly METAR per hour, windier under a signal
            t = pd.Timestamp(f"{day} {hour:02d}:00", tz=HKT)
            sig = int(CS.signal_at(pd.Series([t]), tc).iloc[0])
            metar.append((t.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:00Z"), "VHHH ...", 28.0, 24.0, 90,
                          10 + 5 * sig, 15 + 6 * sig, 6.21 if sig < 8 else 1.5, None,
                          "VFR" if sig < 8 else "IFR", "TSRA" if sig else None, "iem", "2026-08-01T00:00:00Z"))
    # one monster delay, past the [-60, 600] clip, scheduled under signal 8
    monster_sched = pd.Timestamp("2026-07-25 20:00", tz=HKT)
    rows.append(("2026-07-25", "XX 9999", "20:00", "CPA", "LAX", monster_sched.isoformat(),
                 (monster_sched + pd.Timedelta(minutes=1500)).isoformat(), "Dep 21:00"))
    c.executemany("INSERT INTO flights (date, flight_no, scheduled_time, airline, destination, scheduled_ts, actual_ts, "
                  "status_raw, first_seen_at, fetched_at) VALUES (?,?,?,?,?,?,?,?,'x','x')", rows)
    c.executemany("INSERT INTO metar_hist (report_time, raw_ob, temp_c, dewp_c, wdir, wspd_kt, wgst_kt, visib_sm, "
                  "ceiling_ft, flt_cat, wx_string, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", metar)
    c.executemany("INSERT INTO tc_signals (tc_id, tc_name, signal, direction, start_ts, end_ts, source) "
                  "VALUES (?,?,?,?,?,?,'hko_warndb')",
                  [(CS.TC_ID, "NOUL", s, "NW" if s == "8" else None, a, b) for s, a, b in SIGNALS]
                  + [("194601", None, "10", None, "1946-07-18T15:15:00+08:00", "1946-07-18T20:00:00+08:00")])  # archive noise
    c.commit()
    return p, n_cancel


# ---------------------------------------------------------------- signal join
def test_signal_at_is_half_open_and_takes_the_max(fixture_db):
    p, _ = fixture_db
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        tc = CS.load_signals(conn)
    assert set(tc["tc_id"]) == {CS.TC_ID}, "the 1946 archive row must be filtered out by the `since` cutoff"
    t = pd.Series([pd.Timestamp("2026-07-24 19:59", tz=HKT),   # before the first signal
                   pd.Timestamp("2026-07-24 20:00", tz=HKT),   # start is inclusive
                   pd.Timestamp("2026-07-25 09:59", tz=HKT),
                   pd.Timestamp("2026-07-25 10:00", tz=HKT),   # T1 -> T3 handover, no overlap
                   pd.Timestamp("2026-07-25 20:00", tz=HKT),
                   pd.Timestamp("2026-07-26 12:00", tz=HKT)])  # end is exclusive: back to 0
    assert list(CS.signal_at(t, tc)) == [0, 1, 1, 3, 8, 0]


def test_signal_at_ignores_monsoon_rows():
    tc = pd.DataFrame({"level": [0, 3], "signal": ["MSN", "3"],
                       "start": [pd.Timestamp("2026-07-25 00:00", tz=HKT)] * 2,
                       "end": [pd.Timestamp("2026-07-26 00:00", tz=HKT)] * 2})
    t = pd.Series([pd.Timestamp("2026-07-25 12:00", tz=HKT)])
    assert list(CS.signal_at(t, tc)) == [3]


# ---------------------------------------------------------------- hourly aggregation
def test_hourly_timeline(fixture_db):
    p, _ = fixture_db
    start, end = pd.Timestamp("2026-07-23 00:00", tz=HKT), pd.Timestamp("2026-07-28 00:00", tz=HKT)
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        tc, fl = CS.load_signals(conn), CS.load_flights(conn, start, end)
        h = CS.hourly_timeline(fl, CS.load_metar(conn, start, end), tc, start, end)
    assert len(h) == 5 * 24, "every clock hour of the window gets a row, empty ones included"
    assert h["hour"].is_monotonic_increasing and h["hour"].iloc[0] == start
    by_t = h.set_index("hour")

    quiet = by_t.loc[pd.Timestamp("2026-07-23 10:00", tz=HKT)]          # no signal
    assert (quiet["signal"], quiet["n_sched"], quiet["n_departed"], quiet["n_cancelled"]) == (0, 6, 6, 0)
    assert quiet["mean_delay"] == pytest.approx(5.0) and quiet["p90_delay"] == pytest.approx(5.0)

    empty = by_t.loc[pd.Timestamp("2026-07-23 03:00", tz=HKT)]          # nothing scheduled at 03:00
    assert empty["n_sched"] == 0 and empty["n_departed"] == 0 and pd.isna(empty["mean_delay"])

    storm = by_t.loc[pd.Timestamp("2026-07-25 19:00", tz=HKT)]          # signal 8: 3 of 6 cancelled
    assert (storm["signal"], storm["n_sched"], storm["n_cancelled"], storm["n_departed"]) == (8, 6, 3, 3)
    assert storm["mean_delay"] == pytest.approx(200.0)
    assert storm["flt_cat"] == "IFR" and storm["wgst_kt"] == 63 and storm["visib_sm"] == pytest.approx(1.5)

    clipped = by_t.loc[pd.Timestamp("2026-07-25 20:00", tz=HKT)]        # the 1500-min flight rides along
    assert clipped["n_sched"] == 7 and clipped["n_departed"] == 4
    assert clipped["n_labelled"] == 3, "the 1500-min delay is outside [-60, 600] and leaves the mean"
    assert clipped["mean_delay"] == pytest.approx(200.0) and clipped["max_delay"] == pytest.approx(1500.0)


def test_hourly_counts_reconcile_with_the_flight_rows(fixture_db):
    p, n_cancel = fixture_db
    start, end = pd.Timestamp("2026-07-23 00:00", tz=HKT), pd.Timestamp("2026-07-28 00:00", tz=HKT)
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        tc, fl = CS.load_signals(conn), CS.load_flights(conn, start, end)
        h = CS.hourly_timeline(fl, CS.load_metar(conn, start, end), tc, start, end)
    assert h["n_sched"].sum() == len(fl)
    assert h["n_cancelled"].sum() == n_cancel == fl["cancelled"].sum()
    assert h["n_departed"].sum() == fl["actual"].notna().sum()


# ---------------------------------------------------------------- totals, recovery, document
def test_by_signal_and_baseline(fixture_db):
    p, _ = fixture_db
    start, end = pd.Timestamp("2026-07-23 00:00", tz=HKT), pd.Timestamp("2026-07-28 00:00", tz=HKT)
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        tc, all_fl = CS.load_signals(conn), CS.load_flights(conn)
        rows = CS.by_signal(CS.load_flights(conn, start, end), tc)
        base = CS.baseline(all_fl, tc)
    by = {r["signal"]: r for r in rows}
    assert set(by) == {0, 1, 3, 8}
    assert by[0]["mean_delay"] == pytest.approx(5.0) and by[0]["cancel_rate"] == 0
    assert by[1]["mean_delay"] == pytest.approx(30.0) and by[3]["mean_delay"] == pytest.approx(30.0)
    assert by[8]["mean_delay"] == pytest.approx(200.0)
    # half of every T8 hour is cancelled; the one extra row is the monster-delay flight, which was not
    assert by[8]["n_cancelled"] / (by[8]["n"] - 1) == pytest.approx(0.5)
    assert by[8]["pct15"] == 1.0 and by[8]["n_over_clip"] == 1
    assert by[0]["n"] + by[1]["n"] + by[3]["n"] + by[8]["n"] == sum(r["n"] for r in rows)
    assert base["mean_delay"] == pytest.approx(5.0)
    # Jul 25 is signalled through every scheduled hour, so it contributes nothing to the no-signal baseline
    assert base["n_days"] == len(DAYS) - 1 and "2026-07-25" not in (base["date_min"], base["date_max"])


def test_recovery_needs_a_busy_hour(fixture_db):
    p, _ = fixture_db
    start, end = pd.Timestamp("2026-07-23 00:00", tz=HKT), pd.Timestamp("2026-07-28 00:00", tz=HKT)
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        tc, fl = CS.load_signals(conn), CS.load_flights(conn, start, end)
        h = CS.hourly_timeline(fl, CS.load_metar(conn, start, end), tc, start, end)
    rec = CS.recovery(h, tc, baseline_mean=5.0, min_n=6)
    assert rec["all_clear_ts"].startswith("2026-07-26T12:00")
    assert rec["recovered_at"].startswith("2026-07-26T12:00"), "delays drop back to 5 min the hour the signal comes down"
    assert rec["hours_to_recover"] == 0
    # an hour needs min_n departures: with min_n above the fixture's 6/hour nothing ever qualifies
    assert CS.recovery(h, tc, baseline_mean=5.0, min_n=99)["hours_to_recover"] is None
    # and a baseline the airport never reaches is honestly reported as "not recovered"
    assert CS.recovery(h, tc, baseline_mean=-10.0, min_n=6)["recovered_at"] is None


def test_build_document_is_json_safe_and_flagged(fixture_db, tmp_path):
    p, n_cancel = fixture_db
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        doc = CS.build(conn, now=dt.datetime(2026, 8, 20, tzinfo=dt.timezone.utc), with_model=False)
    txt = json.dumps(doc, allow_nan=False)          # no NaN/Inf anywhere
    assert len(txt) < 60_000
    assert doc["static"] is True and doc["retrospective"] is None
    assert doc["episode"]["peak_signal"] == 8 and doc["episode"]["sequence"] == "T1→T3→T8→T1"
    assert len(doc["hourly"]) == 5 * 24 and doc["hourly"][0]["t"].startswith("2026-07-23T00:00")
    assert doc["headline"]["n_cancelled_episode"] == n_cancel
    assert doc["headline"]["peak_hour_mean_delay"] == pytest.approx(200.0)
    assert doc["headline"]["peak_gust_kt"] == 63
    assert doc["cancellations"]["total"] == n_cancel
    assert doc["worst_flights"][0]["flight_no"] == "XX 9999" and doc["worst_flights"][0]["over_clip"] is True
    assert doc["worst_flights"][0]["delay_min"] == 1500
    assert [r["date"] for r in doc["cancellations"]["by_day"]] == DAYS
    md = CS.to_markdown(doc)
    assert "IN-SAMPLE" not in md and "Not generated" in md      # no model -> no retrospective section, said plainly
    assert "T1→T3→T8→T1" in md

    sizes = CS.write(doc, tmp_path / "case_noul.json", tmp_path / "case-noul.md")
    assert len(sizes) == 2 and all(v > 0 for v in sizes.values())
    assert json.loads((tmp_path / "case_noul.json").read_text())["episode"]["name"] == "NOUL"
