"""Inbound-aircraft turnaround signal (docs/inbound-feature.md): arrivals parsing, ADS-B snapshot retention,
and the two rotation-linkage methods on synthetic days. In-memory SQLite, no network."""
import datetime as dt
import sqlite3

import pandas as pd
import pytest

from hkia import db as _db
from hkia import ingest_adsb, ingest_arrivals, rotations
from hkia.adsb import COLS
from hkia.ingest_adsb import ADSB_SCHEMA
from hkia.ingest_arrivals import ARRIVALS_SCHEMA, ARRIVALS_STATE_HIST_SCHEMA, parse_status, rows_from_payload
from hkia.rotations import LINKS_SCHEMA, position

UTC = dt.timezone.utc
HKT = dt.timezone(dt.timedelta(hours=8))
DAY = dt.date(2026, 8, 19)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(_db.SCHEMA + ARRIVALS_SCHEMA + ADSB_SCHEMA + LINKS_SCHEMA + ARRIVALS_STATE_HIST_SCHEMA)
    yield c
    c.close()


# ------------------------------------------------------------------ arrivals parsing
@pytest.mark.parametrize("status, expect", [
    ("At gate 09:04", ("2026-08-19T09:04:00+08:00", None, None)),
    ("At gate 17:18 (20/08/2026)", ("2026-08-20T17:18:00+08:00", None, None)),   # arrived on the next calendar day
    ("Landed 23:57", (None, "2026-08-19T23:57:00+08:00", None)),                 # touched down, not yet on blocks
    ("Est at 21:30", (None, None, "2026-08-19T21:30:00+08:00")),
    ("Est at 00:20 (20/08/2026)", (None, None, "2026-08-20T00:20:00+08:00")),
    ("Cancelled", (None, None, None)),
    ("", (None, None, None)),
    (None, (None, None, None)),
    ("At gate", (None, None, None)),                                             # malformed -> no timestamp, no crash
])
def test_arrival_status_parsing(status, expect):
    assert parse_status(status, "2026-08-19") == expect


def test_arrival_rows_from_payload():
    payload = [{"date": "2026-08-19", "arrival": True, "list": [
        {"time": "23:15", "flight": [{"no": "UO 755", "airline": "HKE"}, {"no": "CX 5755", "airline": "CPA"}],
         "status": "At gate 00:30 (20/08/2026)", "origin": ["CNX"], "baggage": "10", "hall": "A",
         "terminal": "", "stand": "D214"},
        {"time": "10:00", "flight": [], "status": "At gate 10:05", "origin": ["TPE"]},   # no flight -> dropped
    ]}]
    rows = rows_from_payload(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r["flight_no"] == "UO 755" and r["airline"] == "HKE" and r["codeshares"] == "CX 5755"
    assert r["origin"] == "CNX" and r["stand"] == "D214" and r["baggage"] == "10"
    assert r["scheduled_ts"] == "2026-08-19T23:15:00+08:00"
    assert r["actual_ts"] == "2026-08-20T00:30:00+08:00" and r["landed_ts"] is None


def test_arrival_upsert_is_idempotent_and_never_loses_a_stand(conn):
    def up(rows):
        for r in rows:
            r["now"] = "2026-08-19T12:00:00+00:00"
        conn.executemany(ingest_arrivals.UPSERT, rows)
        conn.commit()

    payload = [{"date": "2026-08-19", "list": [
        {"time": "09:00", "flight": [{"no": "CX 100", "airline": "CPA"}], "status": "Est at 09:20",
         "origin": ["NRT"], "stand": "N36", "hall": "A", "baggage": "5", "terminal": ""}]}]
    up(rows_from_payload(payload))
    up(rows_from_payload(payload))                                   # same payload twice -> still one row
    assert conn.execute("SELECT COUNT(*) FROM arrivals").fetchone()[0] == 1

    payload[0]["list"][0]["status"] = "At gate 09:31"                # the flight lands
    up(rows_from_payload(payload))
    row = conn.execute("SELECT actual_ts, estimated_ts, stand FROM arrivals").fetchone()
    assert row == ("2026-08-19T09:31:00+08:00", None, "N36")

    payload[0]["list"][0]["stand"] = ""                              # a later re-fetch drops the stand -> keep ours
    up(rows_from_payload(payload))
    assert conn.execute("SELECT actual_ts, stand FROM arrivals").fetchone() == ("2026-08-19T09:31:00+08:00", "N36")


# ------------------------------------------------------------------ ADS-B snapshots
def _frame(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_adsb_rows_from_frame_handles_missing_registration_and_nans():
    ac = _frame([
        ["780ABC", "CPA261 ", 22.4, 114.2, 9000.0, False, 320.0, 45.0, "A359", "B-LRA", 18.0],
        ["780def", "", 22.9, 113.4, 0.0, True, float("nan"), float("nan"), None, None, float("nan")],  # OpenSky-shaped
        ["", "XXX1", 22.0, 113.0, 100.0, False, 1.0, 1.0, None, None, 1.0],                            # no hex -> dropped
    ])
    rows = ingest_adsb.rows_from_frame(ac, "2026-08-19T12:00:00+00:00", "adsb.lol")
    assert len(rows) == 2
    a, b = rows
    assert a["hex"] == "780abc" and a["registration"] == "B-LRA" and a["ac_type"] == "A359" and a["on_ground"] == 0
    assert b["callsign"] is None and b["registration"] is None and b["gs_kt"] is None and b["dst_nm"] is None
    assert b["on_ground"] == 1


def test_adsb_snapshot_prune_keeps_the_retention_window(conn):
    now = dt.datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    for days_ago in (0, 1, 29, 30, 31, 60):
        ts = (now - dt.timedelta(days=days_ago)).isoformat(timespec="seconds")
        conn.execute("INSERT INTO adsb_snapshots (fetched_at, hex, provider) VALUES (?,?,?)", (ts, "780abc", "test"))
    conn.commit()
    deleted = ingest_adsb.prune(conn, now)
    conn.commit()
    kept = conn.execute("SELECT COUNT(*) FROM adsb_snapshots").fetchone()[0]
    assert deleted == 2 and kept == 4                       # 31 and 60 days old go; exactly 30 days stays
    assert ingest_adsb.prune(conn, now) == 0                # idempotent


def test_adsb_snapshot_is_idempotent_within_a_run(conn):
    """Two writes of the same frame at the same fetched_at collapse (PK), so a retried cron step cannot double-count."""
    ac = _frame([["780abc", "CPA261", 22.4, 114.2, 9000.0, False, 320.0, 45.0, "A359", "B-LRA", 18.0]])
    rows = ingest_adsb.rows_from_frame(ac, "2026-08-19T12:00:00+00:00", "adsb.lol")
    conn.executemany(ingest_adsb.INSERT, rows)
    conn.executemany(ingest_adsb.INSERT, rows)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM adsb_snapshots").fetchone()[0] == 1


# ------------------------------------------------------------------ linkage
@pytest.mark.parametrize("raw, want", [
    ("N36", "36"), ("D214", "214"), ("W123R", "123"), ("D301L", "301"), ("S1", "1"),
    ("36", "36"), ("07", "7"), ("", None), (None, None), ("BUS", None),
])
def test_position_normalisation(raw, want):
    assert position(raw) == want


def _arr(conn, flight_no, airline, sched, at_gate, stand, date=DAY):
    conn.execute("INSERT INTO arrivals (date, flight_no, scheduled_time, airline, origin, scheduled_ts, actual_ts, "
                 "stand, first_seen_at, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (date.isoformat(), flight_no, sched, airline, "NRT", f"{date}T{sched}:00+08:00",
                  f"{date}T{at_gate}:00+08:00" if at_gate else None, stand, "x", "x"))


def _dep(conn, flight_no, airline, sched, gate, date=DAY, status="Dep 12:00", actual=None):
    conn.execute("INSERT INTO flights (date, flight_no, scheduled_time, airline, destination, scheduled_ts, "
                 "actual_ts, status_raw, gate, first_seen_at, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (date.isoformat(), flight_no, sched, airline, "LHR", f"{date}T{sched}:00+08:00",
                  f"{date}T{actual}:00+08:00" if actual else None, status, gate, "x", "x"))


def test_stand_gate_pairs_each_arrival_with_the_next_departure_from_that_position(conn):
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _arr(conn, "CX 200", "CPA", "14:00", "14:05", "N36")
    _dep(conn, "CX 099", "CPA", "08:20", "36")     # 10 min after the inbound: too fast to be its turnaround
    _dep(conn, "CX 101", "CPA", "09:30", "36")     # <- CX 100's aircraft
    _dep(conn, "CX 201", "CPA", "15:30", "36")     # <- CX 200's aircraft
    _dep(conn, "CX 900", "CPA", "10:00", "12")     # different position, no arrival there
    conn.commit()
    rows = rotations.link_stand_gate(conn, DAY, "now")
    got = {r["dep_flight_no"]: r for r in rows}
    assert set(got) == {"CX 101", "CX 201"}
    assert got["CX 101"]["arr_flight_no"] == "CX 100" and got["CX 101"]["position"] == "36"
    assert got["CX 101"]["turnaround_min"] == pytest.approx(80.0)      # 08:10 -> 09:30
    assert got["CX 201"]["arr_flight_no"] == "CX 200"
    assert all(r["confidence"] == 1.0 for r in rows)


def test_stand_gate_is_conservative_when_two_departures_fit_one_arrival(conn):
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    _dep(conn, "CX 103", "CPA", "11:30", "36")     # a second aircraft was towed in; we do not guess
    conn.commit()
    rows = rotations.link_stand_gate(conn, DAY, "now")
    assert [r["dep_flight_no"] for r in rows] == ["CX 101"]
    assert rows[0]["confidence"] == 0.6            # two candidates fitted -> flagged as ambiguous


def test_stand_gate_skips_cancelled_departures_and_arrivals_that_never_landed(conn):
    _arr(conn, "CX 100", "CPA", "08:00", None, "N36")          # never on blocks
    _arr(conn, "CX 300", "CPA", "12:00", "12:05", "N40")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    _dep(conn, "CX 301", "CPA", "13:30", "40", status="Cancelled")
    conn.commit()
    assert rotations.link_stand_gate(conn, DAY, "now") == []


def test_stand_gate_ignores_an_implausibly_long_sit(conn):
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "23:30", "36")                 # 15 h later: towed away and back, not a turnaround
    conn.commit()
    assert rotations.link_stand_gate(conn, DAY, "now") == []


def _snap(conn, hexid, callsign, when_hkt, reg="B-LRA"):
    ts = when_hkt.astimezone(UTC).isoformat(timespec="seconds")
    conn.execute("INSERT INTO adsb_snapshots (fetched_at, hex, callsign, registration, provider) VALUES (?,?,?,?,?)",
                 (ts, hexid, callsign, reg, "adsb.lol"))


def test_adsb_hex_links_one_airframe_in_as_cpa123_and_out_as_cpa456(conn):
    _arr(conn, "CX 123", "CPA", "09:50", "10:02", "N36")
    _dep(conn, "CX 456", "CPA", "12:30", "36")
    _snap(conn, "780abc", "CPA123", dt.datetime(2026, 8, 19, 9, 55, tzinfo=HKT))
    _snap(conn, "780abc", "CPA456", dt.datetime(2026, 8, 19, 12, 35, tzinfo=HKT))
    _snap(conn, "780fff", "CSN999", dt.datetime(2026, 8, 19, 11, 0, tzinfo=HKT))   # unrelated traffic
    conn.commit()
    rows = rotations.link_adsb(conn, DAY, "now")
    assert len(rows) == 1
    r = rows[0]
    assert (r["dep_flight_no"], r["arr_flight_no"], r["method"]) == ("CX 456", "CX 123", "adsb_hex")
    assert r["hex"] == "780abc" and r["registration"] == "B-LRA" and r["confidence"] == 1.0
    assert r["turnaround_min"] == pytest.approx(148.0)                             # 10:02 -> 12:30


def test_adsb_hex_needs_both_halves_of_the_rotation(conn):
    _arr(conn, "CX 123", "CPA", "09:50", "10:02", "N36")
    _dep(conn, "CX 456", "CPA", "12:30", "36")
    _snap(conn, "780abc", "CPA123", dt.datetime(2026, 8, 19, 9, 55, tzinfo=HKT))   # inbound seen, outbound never was
    conn.commit()
    assert rotations.link_adsb(conn, DAY, "now") == []


def test_adsb_hex_resolves_an_iata_callsign_prefix_through_the_db(conn):
    """A feed that transmits `UO755` rather than `HKE755` still matches: the IATA->ICAO map is built from our own rows."""
    _arr(conn, "UO 123", "HKE", "09:50", "10:02", "N36")
    _dep(conn, "UO 456", "HKE", "12:30", "36")
    _snap(conn, "780bbb", "UO123", dt.datetime(2026, 8, 19, 9, 55, tzinfo=HKT), reg=None)
    _snap(conn, "780bbb", "UO456", dt.datetime(2026, 8, 19, 12, 35, tzinfo=HKT), reg=None)
    conn.commit()
    rows = rotations.link_adsb(conn, DAY, "now")
    assert [(r["arr_flight_no"], r["dep_flight_no"]) for r in rows] == [("UO 123", "UO 456")]
    assert rows[0]["registration"] is None                                          # OpenSky-style frame, no reg


def test_build_is_idempotent_and_records_coverage(conn):
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    _dep(conn, "CX 900", "CPA", "10:00", "12")
    conn.commit()
    first = rotations.build(conn, [DAY])
    second = rotations.build(conn, [DAY])
    assert first == second == {"adsb_hex": 0, "stand_gate": 1, "departures": 2, "covered": 1}
    assert conn.execute("SELECT COUNT(*) FROM aircraft_links").fetchone()[0] == 1
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY run_at DESC").fetchone()[0]
    assert "1/2 departures linked" in detail


def test_rebuild_drops_a_stand_gate_link_the_new_evidence_no_longer_supports(conn):
    """Gates are reassigned during the day; the newest build wins. ADS-B links are never dropped — see DELETE_STALE."""
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    conn.commit()
    rotations.build(conn, [DAY])
    assert conn.execute("SELECT dep_flight_no FROM aircraft_links").fetchone() == ("CX 101",)

    conn.execute("UPDATE flights SET gate='40' WHERE flight_no='CX 101'")   # the departure moved to another gate
    conn.commit()
    rotations.build(conn, [DAY])
    assert conn.execute("SELECT COUNT(*) FROM aircraft_links").fetchone()[0] == 0


def test_rebuild_keeps_adsb_links_whose_snapshots_have_been_pruned(conn):
    _arr(conn, "CX 123", "CPA", "09:50", "10:02", "N36")
    _dep(conn, "CX 456", "CPA", "12:30", "36")
    _snap(conn, "780abc", "CPA123", dt.datetime(2026, 8, 19, 9, 55, tzinfo=HKT))
    _snap(conn, "780abc", "CPA456", dt.datetime(2026, 8, 19, 12, 35, tzinfo=HKT))
    conn.commit()
    rotations.build(conn, [DAY])
    conn.execute("DELETE FROM adsb_snapshots")                              # 30-day retention aged the evidence out
    conn.commit()
    rotations.build(conn, [DAY])
    assert conn.execute("SELECT COUNT(*) FROM aircraft_links WHERE method='adsb_hex'").fetchone()[0] == 1


def test_both_methods_coexist_on_the_same_departure(conn):
    """The two methods are independent rows, so they can be compared head-to-head once adsb_hex has history."""
    _arr(conn, "CX 123", "CPA", "09:50", "10:02", "N36")
    _dep(conn, "CX 456", "CPA", "12:30", "36")
    _snap(conn, "780abc", "CPA123", dt.datetime(2026, 8, 19, 9, 55, tzinfo=HKT))
    _snap(conn, "780abc", "CPA456", dt.datetime(2026, 8, 19, 12, 35, tzinfo=HKT))
    conn.commit()
    rotations.build(conn, [DAY])
    methods = dict(conn.execute("SELECT method, arr_flight_no FROM aircraft_links").fetchall())
    assert methods == {"stand_gate": "CX 123", "adsb_hex": "CX 123"}
    same, tot = rotations.airline_agreement(conn, "stand_gate")
    assert (same, tot) == (1, 1)


def test_coverage_report_survives_an_empty_database(conn):
    assert "no links yet" in rotations.coverage(conn)


def test_coverage_report_survives_links_with_no_actuals_yet(conn):
    """Tomorrow's links (if gates ever appear early) have no on-blocks time and no turnaround — must not divide by zero."""
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    conn.commit()
    rotations.build(conn, [DAY])
    conn.execute("UPDATE aircraft_links SET turnaround_min=NULL")
    conn.execute("UPDATE arrivals SET airline=NULL")
    conn.commit()
    report = rotations.coverage(conn)
    assert "no inbound on blocks yet" in report and "airline agreement n/a" in report


# ------------------------------------------------------------------ event_source="sched" (leak fix)
def test_stand_gate_event_source_sched_avoids_leaking_the_actual_time(conn):
    """A departure's SCHEDULED time can place it outside the pairing window while its ACTUAL time places it inside
    (or vice versa). event_source="sched" must follow the scheduled time only -- link existence cannot depend on the
    departure's post-outcome time, or a training rebuild leaks the label into the feature."""
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "08:20", "36", actual="09:00")   # sched: 10 min (too fast); actual: 50 min (fits)
    _arr(conn, "CX 200", "CPA", "08:00", "08:10", "N40")
    _dep(conn, "CX 201", "CPA", "09:00", "40", actual="08:20")   # sched: 50 min (fits); actual: 10 min (too fast)
    conn.commit()

    default_rows = rotations.link_stand_gate(conn, DAY, "now")
    sched_rows = rotations.link_stand_gate(conn, DAY, "now", event_source="sched")

    assert {r["dep_flight_no"] for r in default_rows} == {"CX 101"}   # actual event links it, sched would not
    assert {r["dep_flight_no"] for r in sched_rows} == {"CX 201"}     # sched event links it, actual would not


def test_build_threads_event_source_into_stand_gate_and_the_ingest_log(conn):
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "08:20", "36", actual="09:00")   # only linkable via the actual event
    conn.commit()

    sched_stats = rotations.build(conn, [DAY], event_source="sched")
    assert sched_stats["stand_gate"] == 0
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "events=sched" in detail

    actual_stats = rotations.build(conn, [DAY], event_source="actual")
    assert actual_stats["stand_gate"] == 1
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "events=sched" not in detail


def test_build_marks_scope_all_only_for_a_full_rebuild(conn):
    """events=sched alone can't tell a full --all rebuild (leak-free over the whole window) from a one-date run
    (leak-free for that date only, the rest of the table still actual-built) -- scope=all disambiguates."""
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    conn.commit()

    rotations.build(conn, [DAY], event_source="sched", full_rebuild=False)
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "events=sched" in detail and "scope=all" not in detail

    rotations.build(conn, [DAY], event_source="sched", full_rebuild=True)
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "events=sched" in detail and "scope=all" in detail

    rotations.build(conn, [DAY], event_source="actual", full_rebuild=True)
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "events=sched" not in detail and "scope=all" in detail


def test_main_marks_scope_all_only_when_invoked_with_dash_dash_all(conn, monkeypatch):
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    conn.commit()
    monkeypatch.setattr(rotations, "connect", lambda: conn)

    rotations.main([DAY.isoformat()])
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "scope=all" not in detail

    rotations.main(["--all"])
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "scope=all" in detail


# ------------------------------------------------------------------ default_dates() includes tomorrow
def test_default_dates_is_yesterday_today_tomorrow():
    today = dt.datetime.now(HKT).date()
    assert rotations.default_dates() == [today - dt.timedelta(days=1), today, today + dt.timedelta(days=1)]


def test_a_past_midnight_departure_links_to_the_previous_evenings_arrival(conn):
    """Prediction scores today+tomorrow, so a departure scheduled 00:00-01:59 HKT needs tomorrow's link set built --
    default_dates() must include tomorrow for this to ever get a link."""
    today = dt.datetime.now(HKT).date()
    tomorrow = today + dt.timedelta(days=1)
    _arr(conn, "CX 900", "CPA", "23:50", "23:58", "N36", date=today)
    _dep(conn, "CX 901", "CPA", "00:30", "36", date=tomorrow)
    conn.commit()

    rotations.build(conn, rotations.default_dates())
    row = conn.execute("SELECT arr_flight_no FROM aircraft_links WHERE date=? AND dep_flight_no='CX 901'",
                       (tomorrow.isoformat(),)).fetchone()
    assert row == ("CX 900",)


# ------------------------------------------------------------------ rollback on failure
def test_main_rolls_back_a_pending_delete_when_the_rebuild_fails(conn, monkeypatch):
    """Reproduces the bug: DELETE_STALE and the UPSERT that rebuilds it run in one (uncommitted) transaction inside
    build()'s per-date loop. If something fails between them, main()'s except block must not commit the pending
    DELETE without its rebuild -- that would silently blank the day's links. Here link_stand_gate is monkeypatched to
    return a row with confidence=NULL, which conn.executemany(UPSERT, ...) rejects (NOT NULL) *after* DELETE_STALE has
    already run for the date, reproducing the exact failure window the fix (conn.rollback() first in main()'s except
    block) protects."""
    _arr(conn, "CX 100", "CPA", "08:00", "08:10", "N36")
    _dep(conn, "CX 101", "CPA", "09:30", "36")
    conn.commit()
    rotations.build(conn, [DAY])
    before = conn.execute("SELECT dep_flight_no, arr_flight_no FROM aircraft_links WHERE date=?",
                          (DAY.isoformat(),)).fetchall()
    assert before == [("CX 101", "CX 100")]

    real_link_stand_gate = rotations.link_stand_gate

    def poisoned(conn, date, built_at, event_source="actual"):
        rows = real_link_stand_gate(conn, date, built_at, event_source=event_source)
        for r in rows:
            r["confidence"] = None
        return rows

    monkeypatch.setattr(rotations, "connect", lambda: conn)
    monkeypatch.setattr(rotations, "link_stand_gate", poisoned)
    rotations.main([DAY.isoformat()])

    after = conn.execute("SELECT dep_flight_no, arr_flight_no FROM aircraft_links WHERE date=?",
                         (DAY.isoformat(),)).fetchall()
    assert after == before                     # the pending DELETE from the failed rebuild did not persist
    errors = conn.execute("SELECT detail FROM ingest_log WHERE job='rotations' AND detail LIKE 'ERROR%'").fetchall()
    assert len(errors) == 1


# ------------------------------------------------------------------ arrivals_state_hist
def test_arrivals_state_hist_appends_only_on_change(conn):
    payload = [{"date": "2026-08-19", "list": [
        {"time": "09:00", "flight": [{"no": "CX 100", "airline": "CPA"}], "status": "Est at 09:20",
         "origin": ["NRT"], "stand": "N36", "hall": "A", "baggage": "5", "terminal": ""}]}]
    rows = rows_from_payload(payload)
    first = ingest_arrivals._hist_rows(conn, "2026-08-19", rows, "2026-08-19T10:00:00+00:00")
    assert len(first) == 1 and first[0]["estimated_ts"] == "2026-08-19T09:20:00+08:00"
    conn.executemany(ingest_arrivals.HIST_INSERT, first)
    conn.commit()

    same = ingest_arrivals._hist_rows(conn, "2026-08-19", rows, "2026-08-19T10:30:00+00:00")
    assert same == []                                              # nothing changed -> nothing to append

    payload[0]["list"][0]["status"] = "Est at 09:35"                # the airport moves its estimate
    rows2 = rows_from_payload(payload)
    changed = ingest_arrivals._hist_rows(conn, "2026-08-19", rows2, "2026-08-19T11:00:00+00:00")
    assert len(changed) == 1 and changed[0]["estimated_ts"] == "2026-08-19T09:35:00+08:00"
    conn.executemany(ingest_arrivals.HIST_INSERT, changed)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM arrivals_state_hist").fetchone()[0] == 2


def test_ingest_dates_records_and_logs_arrival_state_history(conn, monkeypatch):
    today = dt.datetime.now(HKT).date()
    payload = [{"date": today.isoformat(), "list": [
        {"time": "09:00", "flight": [{"no": "CX 100", "airline": "CPA"}], "status": "Est at 09:20",
         "origin": ["NRT"], "stand": "N36", "hall": "A", "baggage": "5", "terminal": ""}]}]
    monkeypatch.setattr(ingest_arrivals, "fetch_day", lambda d, s, arrival=False: payload)
    n, failed, n_hist = ingest_arrivals.ingest_dates([today], conn)
    assert (n, failed, n_hist) == (1, 0, 1)
    assert conn.execute("SELECT COUNT(*) FROM arrivals_state_hist").fetchone()[0] == 1
    detail = conn.execute("SELECT detail FROM ingest_log WHERE job='arrivals' ORDER BY run_at DESC LIMIT 1").fetchone()[0]
    assert "1 state changes" in detail


def test_ingest_dates_skips_history_for_dates_outside_the_live_window(conn, monkeypatch):
    """A --fill-gaps / --backfill run touches old (already-landed) dates alongside the live window. Recording their
    first observation would inject one no-information row per flight across the whole 91-day backfill -- only
    yesterday/today/tomorrow get history."""
    today = dt.datetime.now(HKT).date()
    old = today - dt.timedelta(days=10)

    def fake_fetch(d, s, arrival=False):
        return [{"date": d.isoformat(), "list": [
            {"time": "09:00", "flight": [{"no": "CX 100", "airline": "CPA"}], "status": "Est at 09:20",
             "origin": ["NRT"], "stand": "N36", "hall": "A", "baggage": "5", "terminal": ""}]}]

    monkeypatch.setattr(ingest_arrivals, "fetch_day", fake_fetch)
    n, failed, n_hist = ingest_arrivals.ingest_dates([old, today], conn)
    assert n == 2 and failed == 0
    assert n_hist == 1                                              # only today's arrival gets a history row
    assert conn.execute("SELECT arr_date FROM arrivals_state_hist").fetchall() == [(today.isoformat(),)]


def test_arrivals_state_hist_prune_keeps_the_retention_window(conn):
    now = dt.datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    for days_ago in (0, 1, 29, 30, 31, 60):
        ts = (now - dt.timedelta(days=days_ago)).isoformat(timespec="seconds")
        conn.execute("INSERT INTO arrivals_state_hist (arr_date, flight_no, scheduled_time, observed_at) "
                     "VALUES (?,?,?,?)", ("2026-08-19", "CX 100", "09:00", ts))
    conn.commit()
    deleted = ingest_arrivals.prune_hist(conn, now)
    conn.commit()
    kept = conn.execute("SELECT COUNT(*) FROM arrivals_state_hist").fetchone()[0]
    assert deleted == 2 and kept == 4                       # 31 and 60 days old go; exactly 30 days stays
    assert ingest_arrivals.prune_hist(conn, now) == 0        # idempotent
