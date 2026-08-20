"""HKIA departure-delay dashboard (M4). Reads the committed SQLite db + models/ artefacts; never scores.

  streamlit run app/streamlit_app.py --server.headless true

Pages: Live map | Today | Patterns | Model | About. Times in HKT. Design system (zinc dark): app/theme.py + docs/design.md;
charts: app/charts.py; live aircraft map (ADS-B provider chain): app/live_map.py; page bodies: app/page_*.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
import theme as T  # noqa: E402

REPO = "https://github.com/dsjwong/hkia-delay-predictor"
PAGES = ["Live map", "Today", "Patterns", "Model", "About"]
SUBTITLES = {
    "Live map": "Aircraft within 100 nm of VHHH · HKIA departures coloured by P(delay > 15)",
    "Today": "Every HKIA departure with its latest P(delay > 15 min) and predicted minutes",
    "Patterns": "Delay patterns over the rolling 91-day window",
    "Model": "XGBoost vs the airline × hour baseline on a date-ordered test split, plus live evaluation",
    "About": "What this is, how it is built, where the data comes from",
}

st.set_page_config(page_title="HKIA delay predictor", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")
T.register_template()
T.inject_css()

if not D.db_available():
    st.error(f"Database not found at `{D.DB_PATH}`. On Streamlit Cloud this is the committed `data/hkia.db`; locally run "
             "`python scripts/ingest_all.py --backfill` first.")
    st.stop()

fresh = D.freshness()

# ------------------------------------------------------------------ sidebar
st.sidebar.markdown('<div class="hk-brand"><div class="mark">HK</div><div><div class="name">HKIA delay predictor</div>'
                    '<small>VHHH departures</small></div></div>', unsafe_allow_html=True)
# ?page=Model deep-links a single page (used by the README links and the screenshot job); unknown values fall back to the map
_want = (st.query_params.get("page") or "").strip().lower()
_start = next((i for i, p in enumerate(PAGES) if p.lower() == _want), 0)
page = st.sidebar.radio("Page", PAGES, index=_start, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<div class="hk-side-kv"><span class="k">Data as of</span><span class="v">{D.fmt_hkt(fresh["last_ingest"])}</span>'
    f'<span class="k">Last score · METAR</span><span class="v">{D.fmt_hkt(fresh["pred_scored"], "%H:%M")} · '
    f'{D.fmt_hkt(fresh["metar_report"], "%H:%M")}</span>'
    f'<span class="k">On file</span>{fresh["n_flights"]:,} departures, {fresh["date_min"]} → {fresh["date_max"]}</div>',
    unsafe_allow_html=True)
st.sidebar.caption("Refreshed by a GitHub Actions cron every 30 min; the page re-reads the db every 10 min. "
                   "Live map: ADS-B every 10–30 s.")
st.sidebar.markdown(f"[Source on GitHub]({REPO})")

# ------------------------------------------------------------------ title row + page
as_of = D.fmt_hkt(fresh["last_ingest"], "%H:%M")
_t = pd.Timestamp(fresh["last_ingest"]) if fresh["last_ingest"] else None
_t = (_t.tz_localize("UTC") if _t is not None and _t.tzinfo is None else _t)
stale_h = (pd.Timestamp.now(tz="UTC") - _t).total_seconds() / 3600 if _t is not None else 99
T.title_row(page, SUBTITLES[page], f"data as of {as_of}", live=stale_h < 2)

if page == PAGES[0]:
    import live_map
    live_map.render()
elif page == PAGES[1]:
    import page_today
    page_today.render(fresh)
elif page == PAGES[2]:
    import page_patterns
    page_patterns.render()
elif page == PAGES[3]:
    import page_model
    page_model.render()
else:
    import page_about
    page_about.render()
