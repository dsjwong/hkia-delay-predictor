"""Streamlit dashboard smoke tests via AppTest against the real committed data/hkia.db (skipped if the db is absent).

Offline: the adsb.lol feed used by the live map is mocked (requests.get -> fixture), so no network is needed.
"""
import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "streamlit_app.py"
sys.path.insert(0, str(ROOT / "app"))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "hkia.db").exists(), reason="data/hkia.db not present")

PAGES = {"live": "🛰️ Live map", "today": "🛫 Today", "patterns": "📊 Patterns", "model": "🎯 Model", "about": "ℹ️ About"}
ADSB_FIXTURE = {"ac": [
    {"hex": "780abc", "flight": "CPA261  ", "lat": 22.45, "lon": 114.2, "alt_baro": 9000, "gs": 320, "track": 45.0, "t": "A359", "r": "B-LRA", "dst": 18.0},
    {"hex": "780def", "flight": "CSN3456 ", "lat": 22.9, "lon": 113.4, "alt_baro": 31000, "gs": 450, "track": 200.0, "t": "A321", "r": "B-1234", "dst": 60.2},
    {"hex": "780aaa", "flight": "HKE622  ", "lat": 22.31, "lon": 113.92, "alt_baro": "ground", "gs": 5, "track": None, "t": "A320", "r": "B-LCA", "dst": 0.2},
    {"hex": "780bbb", "lat": 22.1, "lon": 114.5, "alt_baro": 3000, "gs": 150, "t": "H145", "r": "B-HKF", "dst": 40.0},
], "total": 4, "now": 0}


class _Resp:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return ADSB_FIXTURE


@pytest.fixture(autouse=True)
def _offline_adsb(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())


def _run(page: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    if page:
        at.sidebar.radio[0].set_value(PAGES[page]).run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_live_map_is_landing_page_and_renders():
    at = _run()
    assert at.sidebar.radio[0].value == PAGES["live"]
    labels = {m.label for m in at.metric}
    assert {"In range", "Tracked"} <= labels
    assert any(m.value == "4" for m in at.metric if m.label == "In range")
    assert any("Data as of" in m.value for m in at.sidebar.markdown)


def test_live_map_feed_failure_is_graceful(monkeypatch):
    import live_map
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(requests, "get", boom)
    live_map.fetch_adsb.clear()
    live_map._LAST_GOOD.update(at=None, data=None)
    at = _run()
    assert any("feed unavailable" in w.value for w in at.warning) or any("feed unavailable" in m.value for m in at.markdown)


def test_today_page_renders():
    at = _run("today")
    labels = {m.label for m in at.metric}
    assert "Flights" in labels and "METAR VHHH" in labels
    assert at.dataframe, "departures table missing"
    cols = set(at.dataframe[0].value.columns)
    assert {"Flight", "Airline", "P(delay>15)", "Pred delay (min)", "Actual delay (min)"} <= cols


def test_patterns_page_renders():
    at = _run("patterns")
    assert any("Delay patterns" in m.value for m in at.markdown)
    assert len(at.dataframe) >= 2  # airline + destinations tables in the expander
    airline_tbl = at.dataframe[0].value
    assert (airline_tbl["n"] >= 50).all()


def test_model_page_renders():
    at = _run("model")
    labels = {m.label for m in at.metric}
    assert {"AUC", "Brier", "MAE (min)"} <= labels
    met = at.dataframe[0].value
    assert "XGBoost" in set(met["predictor"]) and "AUC ↑" in met.columns
    assert any("matured" in i.value for i in at.info) or len(at.dataframe) >= 3


def test_about_page_renders():
    at = _run("about")
    assert any("Darren Wong" in m.value for m in at.markdown)


def test_callsign_matching():
    import live_map
    assert live_map.parse_callsign("CPA261 ") == ("CPA", 261, "")
    assert live_map.parse_callsign("CPA0261A") == ("CPA", 261, "A")
    assert live_map.parse_callsign("CX261") == ("CX", 261, "")
    assert live_map.parse_callsign("") is None
