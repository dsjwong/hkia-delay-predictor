"""API + evaluation tests against a small synthetic SQLite fixture (no network, no models needed except MANIFEST read)."""
import datetime as dt
import json
import sqlite3

import numpy as np
import pytest
from fastapi.testclient import TestClient

from hkia import db as _db
from hkia.api import app
from hkia.evaluate import compute
from hkia.explain import EXPLAIN_SCHEMA
from hkia.predict import PRED_SCHEMA

HKT = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime(2026, 8, 17, 4, 0, tzinfo=dt.timezone.utc)   # 12:00 HKT
DAY = "2026-08-17"


@pytest.fixture()
def fixture_db(tmp_path, monkeypatch):
    path = tmp_path / "fx.db"
    conn = sqlite3.connect(path)
    conn.executescript(_db.SCHEMA + PRED_SCHEMA + EXPLAIN_SCHEMA)
    rng = np.random.default_rng(0)
    fl, pr, ex = [], [], []
    # 150 flights: 120 departed (label known), 30 still scheduled; each with two predictions (early + last)
    for i in range(150):
        sched = dt.datetime(2026, 8, 17, 6, 0, tzinfo=HKT) + dt.timedelta(minutes=4 * i)
        p = float(rng.uniform(0.05, 0.9))
        departed = i < 120
        delay = float(rng.normal(30, 10)) if (departed and rng.uniform() < p) else float(rng.normal(3, 5))
        actual = (sched + dt.timedelta(minutes=delay)).isoformat() if departed else None
        fl.append((DAY, f"CX {100+i}", sched.strftime("%H:%M"), "CPA", None, "TPE", sched.isoformat(), actual, None,
                   "Dep" if departed else "", "T1", "A", "1", "x", "x"))
        for k, scored in enumerate((sched - dt.timedelta(hours=5), sched - dt.timedelta(minutes=20))):
            pr.append((DAY, f"CX {100+i}", sched.isoformat(), p if k else 0.5, 10.0 + p * 20 if k else 8.0, "test@0", f"h{k}",
                       scored.astimezone(dt.timezone.utc).isoformat(timespec="seconds")))
        # one attribution row per flight (latest score only — that is the whole point of the table's primary key)
        ex.append((DAY, f"CX {100+i}", sched.isoformat(), scored.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
                   "test@0", p, -0.97, json.dumps([["wx_ts", 1, 0.42], ["cong_pm60", 55, 0.21], ["airline", "CPA", -0.13]])))
    conn.executemany("INSERT INTO flights VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fl)
    conn.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?)", pr)
    conn.executemany("INSERT INTO explanations VALUES (?,?,?,?,?,?,?,?)", ex)
    conn.execute("INSERT INTO metar VALUES ('2026-08-17T03:30:00Z','VHHH 170330Z 09010KT 9999 FEW020 31/26 Q1006',31,26,90,10,NULL,'6+',NULL,'VFR',NULL,'x')")
    conn.execute("INSERT INTO hko_current VALUES ('2026-08-17T03:40:00+00:00','2026-08-17T11:30:00+08:00','{\"temperature\":{}}')")
    conn.execute("INSERT INTO hko_warnings VALUES ('2026-08-17T03:40:00+00:00',1,'WHOT','{\"WHOT\":{}}')")
    conn.commit(); conn.close()
    monkeypatch.setattr(_db, "DB_PATH", path)
    return path


def test_health_and_departures(fixture_db):
    c = TestClient(app)
    h = c.get("/health").json()
    assert h["status"] == "ok" and h["tables"]["flights"] == 150 and h["tables"]["predictions"] == 300
    d = c.get("/departures", params={"date": DAY}).json()
    assert d["summary"] == {"n": 150, "n_departed": 120, "n_cancelled": 0, "n_with_prediction": 150}
    f = d["flights"][0]
    assert f["status"] == "departed" and f["delay_min"] is not None
    assert f["prediction"]["scored_at"] > "2026-08-16" and f["prediction"]["p_delay15"] != 0.5  # latest, not the early one
    assert d["flights"][-1]["status"] == "scheduled"
    assert c.get("/departures", params={"date": "2026-01-01"}).json()["summary"]["n"] == 0
    assert c.get("/departures", params={"date": "bad"}).status_code == 422


def test_flight_lookup(fixture_db):
    c = TestClient(app)
    r = c.get("/flight/cx100", params={"date": DAY})            # case/space-insensitive
    assert r.status_code == 200
    body = r.json()
    assert body["flight_no"] == "CX 100" and len(body["prediction_history"]) == 2
    assert body["prediction_history"][0]["scored_at"] < body["prediction_history"][1]["scored_at"]
    assert c.get("/flight/ZZ 999", params={"date": DAY}).status_code == 404


def test_model_and_weather(fixture_db):
    c = TestClient(app)
    m = c.get("/model").json()
    assert "manifest" in m and m["live_eval"]["window_days"] == 7
    w = c.get("/weather/latest").json()
    assert w["metar"]["flt_cat"] == "VFR" and w["hko_warnings"]["codes"] == "WHOT" and "temperature" in w["hko_current"]["data"]


def test_evaluate_uses_last_score_before_departure(fixture_db):
    conn = sqlite3.connect(fixture_db)
    res = compute(conn, days=7, now=NOW + dt.timedelta(hours=12))
    assert res["status"] == "ok" and res["n_matured"] == 120
    assert res["model"]["auc"] > 0.7                       # last score (informative p), not the 0.5 early one
    assert res["naive_rate"]["auc"] is None or abs(res["naive_rate"]["auc"] - 0.5) < 1e-9
    assert res["median_lead_min"] < 60
    assert compute(conn, days=7, now=NOW + dt.timedelta(days=30))["status"].startswith("not enough")
