"""Streamlit dashboard smoke tests via AppTest against the real committed data/hkia.db (skipped if the db is absent)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "streamlit_app.py"
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "hkia.db").exists(), reason="data/hkia.db not present")


def _run(page: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    if page:
        at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_today_page_renders():
    at = _run()
    assert any("HKIA departures" in t.value for t in at.title)
    assert any("Data as of" in m.value for m in at.sidebar.markdown)
    labels = {m.label for m in at.metric}
    assert "Flights" in labels and "METAR VHHH" in labels
    assert at.dataframe, "departures table missing"
    cols = set(at.dataframe[0].value.columns)
    assert {"Flight", "Airline", "P(delay>15)", "Pred delay (min)", "Actual delay (min)"} <= cols


def test_patterns_page_renders():
    at = _run("Delay patterns")
    assert any("Delay patterns" in t.value for t in at.title)
    assert len(at.dataframe) >= 2  # airline table + destinations table
    airline_tbl = at.dataframe[0].value
    assert (airline_tbl["n"] >= 50).all()


def test_model_page_renders():
    at = _run("Model performance")
    assert any("Model performance" in t.value for t in at.title)
    met = at.dataframe[0].value
    assert "XGBoost" in set(met["predictor"]) and "AUC ↑" in met.columns
    # live-eval section: either the "collecting" notice or a metrics table
    assert any("matured" in i.value for i in at.info) or len(at.dataframe) >= 3


def test_about_page_renders():
    at = _run("About")
    assert any("Darren Wong" in m.value for m in at.markdown)
