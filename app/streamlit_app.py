"""HKIA departure-delay dashboard (M4). Reads the committed SQLite db + models/ artefacts; never scores.

  streamlit run app/streamlit_app.py --server.headless true

Pages: Live map | Today | Patterns | Model | About. Times in HKT. Dark ops look: app/theme.py; charts: app/charts.py;
live aircraft map (adsb.lol): app/live_map.py; page bodies: app/page_*.py.
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
PAGES = ["🛰️ Live map", "🛫 Today", "📊 Patterns", "🎯 Model", "ℹ️ About"]

st.set_page_config(page_title="HKIA delay predictor", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")
T.register_template()
T.inject_css()

if not D.db_available():
    st.error(f"Database not found at `{D.DB_PATH}`. On Streamlit Cloud this is the committed `data/hkia.db`; locally run "
             "`python scripts/ingest_all.py --backfill` first.")
    st.stop()

fresh = D.freshness()

# ------------------------------------------------------------------ sidebar
st.sidebar.markdown('<div class="hk-brand">HKIA delay predictor<small>VHHH departures · live ops view</small></div>', unsafe_allow_html=True)
page = st.sidebar.radio("Page", PAGES, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data as of** {D.fmt_hkt(fresh['last_ingest'])}  \n"
                    f"last score {D.fmt_hkt(fresh['pred_scored'], '%H:%M')} · METAR {D.fmt_hkt(fresh['metar_report'], '%H:%M')}")
st.sidebar.caption(f"{fresh['n_flights']:,} departures on file, {fresh['date_min']} → {fresh['date_max']}. "
                   "Refreshed by a GitHub Actions cron every 30 min; the page re-reads the db every 10 min. Live map: adsb.lol, every 10 s.")
st.sidebar.markdown(f"[Source on GitHub]({REPO})")

# ------------------------------------------------------------------ header + page
as_of = D.fmt_hkt(fresh["last_ingest"], "%H:%M")
_t = pd.Timestamp(fresh["last_ingest"]) if fresh["last_ingest"] else None
_t = (_t.tz_localize("UTC") if _t is not None and _t.tzinfo is None else _t)
stale_h = (pd.Timestamp.now(tz="UTC") - _t).total_seconds() / 3600 if _t is not None else 99
T.header("HKIA departures", page.split(" ", 1)[1].upper(), f"data as of {as_of}", live=stale_h < 2)

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
