"""Streamlit dashboard smoke tests via AppTest against the real committed data/hkia.db (skipped if the db is absent).

Offline: the ADS-B feeds used by the live map are mocked (requests.get -> fixture), so no network is needed.
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

PAGES = {"live": "Live map", "today": "Today", "patterns": "Patterns", "model": "Model", "about": "About"}
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


OPENSKY_FIXTURE = {"time": 0, "states": [
    # icao24, callsign, country, t_pos, t_contact, lon, lat, baro_alt_m, on_ground, vel_ms, track, vrate, sensors, geo_alt_m, squawk, spi, src
    ["780abc", "CPA261  ", "Hong Kong", 0, 0, 114.2, 22.45, 2743.2, False, 164.6, 45.0, 0, None, 2800.0, None, False, 0],
    ["780aaa", "HKE622  ", "Hong Kong", 0, 0, 113.92, 22.31, None, True, 2.6, None, 0, None, None, None, False, 0],
    ["4bb475", "MNB6031 ", "Turkey", 0, 0, 120.0, 22.0, 8107.7, False, 245.7, 167.9, 0, None, 8679.2, None, False, 0],  # > 100 nm, dropped
    ["000000", None, "?", 0, 0, None, None, None, False, None, None, 0, None, None, None, False, 0],  # no position, dropped
]}


@pytest.fixture(autouse=True)
def _offline_adsb(monkeypatch):
    import live_map
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())
    live_map._LAST_GOOD.update(at=None, data=None, provider=None, interval=10)
    live_map._LAST_POLL.clear()


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


def test_opensky_mapper():
    import live_map
    ac = live_map.normalise_opensky(OPENSKY_FIXTURE)
    assert list(ac.columns) == live_map.COLS
    assert len(ac) == 2 and set(ac["callsign"]) == {"CPA261", "HKE622"}
    cx = ac[ac["callsign"] == "CPA261"].iloc[0]
    assert abs(cx["alt_ft"] - 9000) < 1 and abs(cx["gs_kt"] - 320) < 1 and cx["track_deg"] == 45.0 and not cx["on_ground"]
    assert 15 < cx["dst_nm"] < 20
    hke = ac[ac["callsign"] == "HKE622"].iloc[0]
    assert hke["on_ground"] and hke["alt_ft"] == 0 and hke["dst_nm"] < 1
    assert live_map.normalise_opensky({"states": None}).empty


def test_provider_chain_falls_back_to_first_non_empty(monkeypatch):
    import live_map
    calls = []

    class R:
        def __init__(self, js): self._js = js
        def raise_for_status(self): pass
        def json(self): return self._js

    def fake_get(url, *a, **k):
        calls.append(url)
        if "adsb.lol" in url:
            return R({"ac": [], "total": 0})          # empty = what Streamlit Cloud sees
        if "opensky" in url:
            return R(OPENSKY_FIXTURE)
        raise AssertionError("chain should stop at the first provider with aircraft")
    import requests
    monkeypatch.setattr(requests, "get", fake_get)
    ac, err, at = live_map.fetch_adsb(now=1000.0)
    assert err is None and len(ac) == 2 and live_map._LAST_GOOD["provider"] == "OpenSky" and live_map._LAST_GOOD["interval"] == 30
    assert [("adsb.lol" in u, "opensky" in u) for u in calls] == [(True, False), (False, True)]
    # within the OpenSky interval the cached frame is served, nothing is polled
    ac2, err2, at2 = live_map.fetch_adsb(now=1020.0)
    assert len(calls) == 2 and at2 == 1000.0 and err2 is None
    # after 30 s the chain runs again: adsb.lol first, then OpenSky
    live_map.fetch_adsb(now=1031.0)
    assert len(calls) == 4


def test_provider_chain_all_empty_keeps_last_good(monkeypatch):
    import live_map
    import requests
    live_map._LAST_GOOD.update(at=500.0, data=live_map.normalise_readsb(ADSB_FIXTURE), provider="adsb.lol", interval=10)

    class R:
        def raise_for_status(self): pass
        def json(self): return {"ac": [], "states": []}
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    ac, err, at = live_map.fetch_adsb(now=600.0)
    assert len(ac) == 4 and at == 500.0
    assert err.startswith("feed degraded:") and "adsb.lol" in err and "OpenSky" in err and "airplanes.live" in err
