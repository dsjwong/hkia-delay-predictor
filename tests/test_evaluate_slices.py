"""The report-card slices of hkia.evaluate (daily series, lead-time buckets, live calibration, notable flights, deltas)
on a hand-built synthetic db: 3 HKT days, controlled lead times, a deliberately planted miss in each direction.

The model here is a cheat oracle with noise (p = 0.85 for flights that end up late, 0.15 for the rest, plus two planted
mistakes), so the expected AUC is high and the numbers are checkable by hand — the point is the *aggregation*, not the model.
"""
import datetime as dt
import sqlite3

import pandas as pd
import pytest

from hkia import db as _db
from hkia.evaluate import CAL_BINS, LEAD_BUCKETS, calibration_bins, compute, matured_predictions, notable_flights
from hkia.predict import PRED_SCHEMA

HKT = dt.timezone(dt.timedelta(hours=8))
DAYS = ["2026-08-15", "2026-08-16", "2026-08-17"]
NOW = dt.datetime(2026, 8, 18, 0, 0, tzinfo=dt.timezone.utc)
# lead time (minutes before the actual departure) of the last score, cycled over the flights of each day -> one flight
# in every bucket boundary we care about: < 30, 30-120, 2-12 h, > 12 h
LEADS = [10.0, 25.0, 45.0, 100.0, 300.0, 900.0]


def _rows():
    """(flights, predictions) for 3 days x 40 flights; every 4th flight is late, flight 0 of each day is a planted miss."""
    fl, pr = [], []
    for di, day in enumerate(DAYS):
        for i in range(40):
            sched = dt.datetime.fromisoformat(day + "T06:00:00+08:00") + dt.timedelta(minutes=20 * i)
            late = i % 4 == 0                      # 25 % of flights are > 15 min late
            delay = 40.0 + i if late else 2.0
            p = 0.85 if late else 0.15
            if i == 0:                             # planted miss: very late but the model was confident it was fine
                p, delay = 0.02, 120.0
            if i == 1:                             # planted false alarm: model confident it was late, it left on time
                p, delay = 0.95, 1.0
            lead = LEADS[i % len(LEADS)]
            actual = sched + dt.timedelta(minutes=delay)
            fl.append((day, f"CX {100 + i}", sched.strftime("%H:%M"), "CPA", None, "TPE", sched.isoformat(),
                       actual.isoformat(), None, "Dep", "T1", "A", "1", "x", "x"))
            for k, scored in enumerate((actual - dt.timedelta(days=2), actual - dt.timedelta(minutes=lead))):
                pr.append((day, f"CX {100 + i}", sched.isoformat(), p if k else 0.5, delay if k else 8.0,
                           f"v{di % 2}@x", f"h{k}", scored.astimezone(dt.timezone.utc).isoformat(timespec="seconds")))
    return fl, pr


@pytest.fixture()
def slices_db(tmp_path, monkeypatch):
    path = tmp_path / "slices.db"
    conn = sqlite3.connect(path)
    conn.executescript(_db.SCHEMA + PRED_SCHEMA)
    fl, pr = _rows()
    conn.executemany("INSERT INTO flights VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fl)
    conn.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?)", pr)
    conn.commit()
    conn.close()
    monkeypatch.setattr(_db, "DB_PATH", path)
    return path


@pytest.fixture()
def res(slices_db):
    return compute(sqlite3.connect(slices_db), days=7, now=NOW, models_dir=slices_db.parent / "no-models")


def test_headline_is_still_computed(res):
    assert res["status"] == "ok" and res["n_matured"] == 120
    assert res["model"]["auc"] > 0.8                       # the cheat oracle, minus the two planted mistakes
    assert res["date_min"] == DAYS[0] and res["date_max"] == DAYS[-1]
    assert "error" in res["baseline_airline_hour"]         # no baseline table -> baseline slices are skipped, not faked
    assert res["deltas"] is None
    assert all(r.get("baseline") is None for r in res["daily"])


def test_daily_series_one_row_per_day_with_n_and_metrics(res):
    daily = res["daily"]
    assert [r["date"] for r in daily] == DAYS              # sorted, one row per HKT departure date
    assert [r["n"] for r in daily] == [40, 40, 40]
    assert sum(r["n"] for r in daily) == res["n_matured"]
    for r in daily:
        assert r["delayed15_rate"] == pytest.approx(10 / 40)   # every 4th flight (the planted miss is one of them)
        assert 0.0 <= r["model"]["auc"] <= 1.0 and r["model"]["brier"] is not None and r["model"]["mae"] >= 0
        assert r["thin"] is False                              # 40 >= MIN_SLICE_N


def test_daily_auc_is_none_when_a_day_has_one_class(slices_db):
    """A day where nothing was late has no AUC — report None, never 0.5 dressed up as a score."""
    conn = sqlite3.connect(slices_db)
    conn.execute("UPDATE flights SET actual_ts = scheduled_ts WHERE date = ?", (DAYS[0],))
    conn.commit()
    r = compute(conn, days=7, now=NOW, models_dir=slices_db.parent / "no-models")
    day0 = next(d for d in r["daily"] if d["date"] == DAYS[0])
    assert day0["delayed15_rate"] == 0.0 and day0["model"]["auc"] is None and day0["model"]["brier"] is not None


def test_lead_time_buckets_partition_the_window(res):
    buckets = res["lead_buckets"]
    assert [b["label"] for b in buckets] == [b[0] for b in LEAD_BUCKETS]
    assert sum(b["n"] for b in buckets) == res["n_matured"]     # every flight lands in exactly one bucket
    n = {b["label"]: b["n"] for b in buckets}
    assert n["< 30 min"] == 42 and n["30–120 min"] == 42        # leads 10/25 and 45/100 min, 2 of the 6 cycled leads each
    assert n["2–12 h"] == 18 and n["> 12 h"] == 18              # 300 min and 900 min
    for b in buckets:
        assert b["median_lead_min"] >= b["lo_min"]
        assert b["thin"] is (b["n"] < 20)                       # thin slices are flagged, not hidden
    assert [b["thin"] for b in buckets] == [False, False, True, True]
    assert buckets[-1]["hi_min"] is None                        # open-ended top bucket, JSON-safe (no inf)


def test_calibration_bins_are_ordered_and_sum_to_n(res):
    cal = res["calibration"]
    assert 0 < len(cal) <= CAL_BINS
    assert sum(b["n"] for b in cal) == res["n_matured"]
    assert [b["bin"] for b in cal] == sorted(b["bin"] for b in cal)
    for b in cal:
        lo, hi = (float(x) for x in b["bin"].split("-"))
        assert lo <= b["pred_mean"] <= hi and 0.0 <= b["obs_rate"] <= 1.0
    n = {b["bin"]: b["n"] for b in cal}
    assert n["0.1-0.2"] == 87 and n["0.8-0.9"] == 27   # 29 on-time + 9 late flights a day, the two planted ones aside
    assert n["0.0-0.1"] == 3 and n["0.9-1.0"] == 3     # the planted miss / false alarm, one per day


def test_calibration_drops_empty_bins(res, slices_db):
    df = matured_predictions(sqlite3.connect(slices_db), 7, NOW)
    assert len(calibration_bins(df)) == len(res["calibration"])
    single = pd.DataFrame({"p_delay15": [0.42, 0.44], "delayed15": [0, 1]})
    assert calibration_bins(single) == [{"bin": "0.4-0.5", "n": 2, "pred_mean": 0.43, "obs_rate": 0.5}]


def test_notable_flights_pick_both_kinds_of_miss(res):
    nb = res["notable"]
    assert len(nb["confident_correct"]) == 5 and len(nb["worst_misses"]) == 5
    for r in nb["confident_correct"]:
        assert r["delayed15"] == 1 and r["p"] >= 0.5 and r["delay_min"] > 15
        assert set(r) == {"flight_no", "date", "airline", "dest", "p", "pred_min", "delay_min", "delayed15", "lead_min"}
        assert r["airline"] == "CPA" and r["dest"] == "TPE" and r["date"] in DAYS
    misses = nb["worst_misses"]
    assert any(r["p"] < 0.1 and r["delay_min"] > 60 for r in misses)      # planted: low p, very late
    assert any(r["p"] > 0.9 and r["delayed15"] == 0 for r in misses)      # planted: high p, on time
    assert all(r["flight_no"] in ("CX 100", "CX 101") for r in misses)    # only the planted mistakes are big misses


def test_notable_ranks_confident_correct_by_probability(slices_db):
    df = matured_predictions(sqlite3.connect(slices_db), 7, NOW)
    hits = notable_flights(df, k=3)["confident_correct"]
    assert len(hits) == 3 and [r["p"] for r in hits] == sorted((r["p"] for r in hits), reverse=True)


def test_slices_survive_a_missing_destination_column(slices_db):
    """notable_flights must not blow up if `destination` is NULL for a flight."""
    conn = sqlite3.connect(slices_db)
    conn.execute("UPDATE flights SET destination = NULL WHERE flight_no = 'CX 100'")
    conn.commit()
    nb = notable_flights(matured_predictions(conn, 7, NOW))
    assert any(r["dest"] is None for r in nb["worst_misses"])


def test_everything_is_json_safe(res):
    """export_json dumps with allow_nan=False; no NaN/inf/numpy types may leak out of compute()."""
    import json
    txt = json.dumps(res, allow_nan=False)
    assert "NaN" not in txt and "Infinity" not in txt
    assert len(txt) < 100_000


def test_baseline_scoring_does_not_need_the_training_stack(slices_db, monkeypatch):
    """The Streamlit app runs on requirements.txt (no xgboost / scikit-learn), so the report card's baseline must be
    scoreable from hkia.baseline alone — importing hkia.train here would break the deployed dashboard."""
    import sys

    import joblib
    from hkia.baseline import baseline_b_predict, baseline_b_table

    models = slices_db.parent / "models"
    models.mkdir()
    train = pd.DataFrame({"airline": ["CPA"] * 6, "sched_hour": [6, 6, 7, 7, 8, 8],
                          "delayed15": [1, 0, 1, 1, 0, 0], "delay_min": [40.0, 2.0, 30.0, 50.0, 1.0, 3.0]})
    joblib.dump({"clf": baseline_b_table(train, "delayed15"), "reg": baseline_b_table(train, "delay_min")},
                models / "baseline_b_airline_hour.joblib")
    for m in [k for k in sys.modules if k.startswith("hkia.train")]:
        del sys.modules[m]
    monkeypatch.setitem(sys.modules, "xgboost", None)          # make `import hkia.train` impossible
    monkeypatch.setitem(sys.modules, "sklearn", None)

    res = compute(sqlite3.connect(slices_db), days=7, now=NOW, models_dir=models)
    assert "error" not in res["baseline_airline_hour"] and res["baseline_airline_hour"]["auc"] is not None
    assert res["deltas"]["auc"] is not None
    assert all("baseline" in r for r in res["daily"]) and all("baseline" in b for b in res["lead_buckets"])
    assert "hkia.train" not in sys.modules
    assert baseline_b_predict(train.head(2), baseline_b_table(train, "delayed15")).tolist() == [0.5, 0.5]

