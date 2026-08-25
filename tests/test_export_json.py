"""hkia.export_json against the synthetic fixture db of test_api (no network; models/ + reports/ of the repo are read if present)."""
import datetime as dt
import json
import sqlite3

import pytest

from hkia import export_json as E
from hkia.ingest_arrivals import ARRIVALS_SCHEMA
from hkia.rotations import LINKS_SCHEMA
from tests.test_api import DAY, HKT, NOW, fixture_db  # noqa: F401  (fixture re-exported)


def test_export_writes_all_files(fixture_db, tmp_path):
    out = tmp_path / "data"
    sizes = E.export(fixture_db, out, now=NOW)
    assert set(sizes) == {"meta.json", "departures_yesterday.json", "departures_today.json", "departures_tomorrow.json",
                          "patterns.json", "model.json", "weather.json"}
    assert sum(sizes.values()) < 1_000_000
    meta = json.loads((out / "meta.json").read_text())
    assert meta["dates"]["today"] == DAY and meta["counts"]["today_flights"] == 150 and meta["counts"]["predictions"] == 300
    assert meta["iata_to_icao"]["CX"] == "CPA" and meta["airports"]["TPE"]["city"].startswith("Taipei")
    today = json.loads((out / "departures_today.json").read_text())
    f = today["flights"][0]
    assert f["status"] == "departed" and f["delay_min"] is not None and f["p"] != 0.5  # latest score, not the early one
    assert f["history"][0][0] < f["history"][-1][0] and f["sched_ts"].endswith("Z")
    assert today["flights"][-1]["status"] == "scheduled" and "delay_min" in today["flights"][-1]
    # "why this prediction": top-3 attributions, only on flights that have not departed yet
    assert "why" not in f, "departed flights carry their score but not the attribution block"
    why = today["flights"][-1]["why"]
    assert len(why) == 3 and [w[0] for w in why] == [1, 1, -1]           # [direction, one-liner, probability points]
    assert why[0][1] == "thunderstorm reported at the field" and why[2][1].startswith("operated by Cathay")
    assert abs(why[0][2]) > abs(why[2][2]) > 0                           # ranked by size, signed like the direction
    assert sum(1 for x in today["flights"] if "why" in x) == 30          # the 30 still-scheduled flights
    assert sum(1 for x in today["flights"] if "inbound" in x) == 0       # no aircraft_links table in this fixture
    pat = json.loads((out / "patterns.json").read_text())
    assert pat["summary"]["n"] == 120 and len(pat["heatmap"]["mean_delay"]) == 7 and len(pat["heatmap"]["mean_delay"][0]) == 24
    assert pat["airlines"][0]["code"] == "CPA" and pat["destinations"][0]["code"] == "TPE"
    wx = json.loads((out / "weather.json").read_text())
    assert wx["metar"]["flt_cat"] == "VFR" and wx["hko_warnings"][0]["code"] == "WHOT"
    model = json.loads((out / "model.json").read_text())
    assert "live_eval" in model and model["live_eval"]["n_matured"] == 120 and len(model["limitations"]) >= 4
    ev = model["live_eval"]  # the report-card slices ride along in model.json (kept small: the whole file is < 100 KB)
    assert sizes["model.json"] < 100_000
    assert {"daily", "lead_buckets", "calibration", "notable", "deltas"} <= set(ev)
    assert sum(r["n"] for r in ev["daily"]) == ev["n_matured"] == sum(b["n"] for b in ev["lead_buckets"])
    assert len(ev["notable"]["confident_correct"]) == 5 and len(ev["notable"]["worst_misses"]) == 5


def _sched(i: int) -> dt.datetime:
    return dt.datetime(2026, 8, 17, 6, 0, tzinfo=HKT) + dt.timedelta(minutes=4 * i)


def _flight_row(flight_no: str, sched: dt.datetime, status_raw: str = ""):
    """A `flights` row with no actual_ts (status 'scheduled'), regardless of whether `sched` is already in the past --
    a delayed flight that has not yet actually left is still 'scheduled', which is exactly the case the now-gate test
    below needs (scheduled time before `now`, but no actual_ts)."""
    now = NOW.isoformat()
    return (sched.date().isoformat(), flight_no, sched.strftime("%H:%M"), "THA", None, "TPE", sched.isoformat(),
            None, None, status_raw, "T1", "A", "1", now, now)


def _arrival_row(flight_no: str, sched: dt.datetime, origin: str, actual: dt.datetime | None, estimated: dt.datetime | None,
                  date: str | None = None):
    now = NOW.isoformat()
    return (date or DAY, flight_no, sched.strftime("%H:%M"), "THA", None, origin, sched.isoformat(),
            actual.isoformat() if actual else None, actual.isoformat() if actual else None,
            estimated.isoformat() if estimated else None, "x", "T1", "A", "1", "36", now, now)


def _link_row(dep_flight_no: str, dep_sched: dt.datetime, method: str, arr_flight_no: str, arr_sched: dt.datetime,
              confidence: float, arr_actual: dt.datetime | None, arr_estimated: dt.datetime | None,
              dep_date: str | None = None, arr_date: str | None = None):
    now = NOW.isoformat()
    return (dep_date or DAY, dep_flight_no, dep_sched.strftime("%H:%M"), method, arr_date or DAY, arr_flight_no,
            arr_sched.strftime("%H:%M"), None, None, "36", arr_actual.isoformat() if arr_actual else None,
            arr_estimated.isoformat() if arr_estimated else None, dep_sched.isoformat(), None, confidence, now)


@pytest.fixture()
def fixture_db_with_inbound(fixture_db):
    conn = sqlite3.connect(fixture_db)
    conn.executescript(ARRIVALS_SCHEMA + LINKS_SCHEMA)
    arr, links = [], []

    # i=120 "CX 220" 14:00 HKT: stand_gate, on blocks 3 h before departure -> well past the 2 h cutoff -> used_by_model
    dep = _sched(120)
    arr_a = dep - dt.timedelta(hours=3, minutes=30)
    arr.append(_arrival_row("UO 755", arr_a, "CNX", dep - dt.timedelta(hours=3), None))
    links.append(_link_row("CX 220", dep, "stand_gate", "UO 755", arr_a, 1.0, dep - dt.timedelta(hours=3), None))

    # i=121 "CX 221" 14:04 HKT: stand_gate, on blocks 1 h50 before departure -> inside the 2 h cutoff -> not used
    dep = _sched(121)
    arr_a = dep - dt.timedelta(hours=2, minutes=20)
    arr.append(_arrival_row("UO 756", arr_a, "CNX", dep - dt.timedelta(hours=1, minutes=50), None))
    links.append(_link_row("CX 221", dep, "stand_gate", "UO 756", arr_a, 0.6, dep - dt.timedelta(hours=1, minutes=50), None))

    # i=122 "CX 222" 14:08 HKT: adsb_hex only, on blocks 3 h before departure (same margin as the stand_gate case
    # above) -> must still be used_by_model = False, because adsb_hex is never a model feature
    dep = _sched(122)
    arr_a = dep - dt.timedelta(hours=3, minutes=30)
    arr.append(_arrival_row("UO 757", arr_a, "CNX", dep - dt.timedelta(hours=3), None))
    links.append(_link_row("CX 222", dep, "adsb_hex", "UO 757", arr_a, 0.8, dep - dt.timedelta(hours=3), None))

    # i=123 "CX 223" 14:12 HKT: stand_gate, not yet on blocks, only a live estimate -> in_flight
    dep = _sched(123)
    arr_a = dep - dt.timedelta(hours=2)
    links.append(_link_row("CX 223", dep, "stand_gate", "UO 758", arr_a, 1.0, None, dep - dt.timedelta(hours=1)))
    arr.append(_arrival_row("UO 758", arr_a, "CNX", None, dep - dt.timedelta(hours=1)))

    # i=0 "CX 100" 06:00 HKT: already departed -- a link exists but must never surface as `inbound`
    dep = _sched(0)
    arr_a = dep - dt.timedelta(hours=3, minutes=30)
    arr.append(_arrival_row("UO 700", arr_a, "CNX", dep - dt.timedelta(hours=3), None))
    links.append(_link_row("CX 100", dep, "stand_gate", "UO 700", arr_a, 1.0, dep - dt.timedelta(hours=3), None))

    fl = []
    # "CX 500" 10:00 HKT today: scheduled_ts is already *before* NOW (12:00 HKT) but the flight never actually left
    # (no actual_ts -> still status 'scheduled', a delayed-but-not-departed flight). Its 2 h cutoff (08:00 HKT) is
    # unambiguously in the past relative to NOW -- not the CX 220 boundary case (cutoff == NOW) -- so this is the
    # clearly-true side of the now-gate.
    dep = dt.datetime(2026, 8, 17, 10, 0, tzinfo=HKT)
    arr_a = dep - dt.timedelta(hours=3, minutes=30)
    fl.append(_flight_row("CX 500", dep))
    arr.append(_arrival_row("UO 800", arr_a, "CNX", dep - dt.timedelta(hours=3, minutes=30), None))
    links.append(_link_row("CX 500", dep, "stand_gate", "UO 800", arr_a, 1.0, dep - dt.timedelta(hours=3, minutes=30), None))

    # "CX 900" 00:30 HKT *tomorrow* (2026-08-18): the day-ahead case. Inbound is already on blocks (21:00 HKT today,
    # comfortably before the raw dep_sched - 2h threshold of 22:30), but that 22:30 cutoff has not been reached by
    # NOW (12:00 HKT today) -- exactly the population features.inbound_features's `now`-gate excludes, because at
    # a 12:00 (or even a 22:00) export the model itself would have scored this flight `inbound_known=0`.
    dep = dt.datetime(2026, 8, 18, 0, 30, tzinfo=HKT)
    arr_sched = dt.datetime(2026, 8, 17, 20, 30, tzinfo=HKT)
    arr_actual = dt.datetime(2026, 8, 17, 21, 0, tzinfo=HKT)
    fl.append(_flight_row("CX 900", dep))
    arr.append(_arrival_row("UO 900", arr_sched, "CNX", arr_actual, None, date="2026-08-17"))
    links.append(_link_row("CX 900", dep, "stand_gate", "UO 900", arr_sched, 1.0, arr_actual, None,
                           dep_date="2026-08-18", arr_date="2026-08-17"))

    conn.executemany("INSERT INTO flights VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fl)
    conn.executemany("INSERT INTO arrivals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", arr)
    conn.executemany("INSERT INTO aircraft_links VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", links)
    conn.commit()
    conn.close()
    return fixture_db


def test_inbound_aircraft(fixture_db_with_inbound, tmp_path):
    out = tmp_path / "data"
    E.export(fixture_db_with_inbound, out, now=NOW)
    today = json.loads((out / "departures_today.json").read_text())
    by_no = {f["flight_no"]: f for f in today["flights"]}

    assert "inbound" not in by_no["CX 100"]        # departed flight: never surfaced, even though a link exists

    ib = by_no["CX 220"]["inbound"]                # cutoff == NOW exactly: the boundary case
    assert ib["flight_no"] == "UO 755" and ib["origin"] == "CNX" and ib["status"] == "landed"
    assert ib["method"] == "stand_gate" and ib["used_by_model"] is True

    ib = by_no["CX 221"]["inbound"]
    assert ib["status"] == "landed" and ib["method"] == "stand_gate" and ib["used_by_model"] is False

    ib = by_no["CX 222"]["inbound"]
    assert ib["method"] == "adsb_hex" and ib["used_by_model"] is False   # never a model feature, even before the cutoff

    ib = by_no["CX 223"]["inbound"]
    assert ib["status"] == "in_flight" and ib["actual_ts"] is None and ib["est_ts"] is not None
    assert ib["used_by_model"] is False

    ib = by_no["CX 500"]["inbound"]                # cutoff (08:00 HKT) clearly before NOW (12:00 HKT)
    assert ib["status"] == "landed" and ib["method"] == "stand_gate" and ib["used_by_model"] is True

    assert sum(1 for f in today["flights"] if "inbound" in f) == 5       # the 5 scheduled-today flights with a link
    for f in today["flights"]:
        if "inbound" in f:
            assert f["status"] == "scheduled"

    txt = json.dumps(today, allow_nan=False)   # every float went through _r(); no NaN leaked into the JSON
    assert "NaN" not in txt


def test_inbound_day_ahead_now_gate(fixture_db_with_inbound, tmp_path):
    """A departure tomorrow whose inbound is already on blocks (well before the raw 2 h threshold) must still be
    used_by_model = False if that threshold has not been reached yet AT EXPORT TIME -- matching the exact serve-time
    gate hkia.features.inbound_features applies (`cutoff <= now`), not just the raw arr_actual_ts < cutoff test."""
    out = tmp_path / "data"
    E.export(fixture_db_with_inbound, out, now=NOW)
    tomorrow = json.loads((out / "departures_tomorrow.json").read_text())
    by_no = {f["flight_no"]: f for f in tomorrow["flights"]}
    ib = by_no["CX 900"]["inbound"]
    assert ib["status"] == "landed" and ib["actual_ts"] is not None   # the inbound really is on blocks already
    assert ib["method"] == "stand_gate"
    assert ib["used_by_model"] is False    # ... but the model's cutoff (22:30 today) is still in the future at NOW
