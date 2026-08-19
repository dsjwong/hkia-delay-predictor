"""About page."""
from __future__ import annotations

import streamlit as st

REPO = "https://github.com/dsjwong/hkia-delay-predictor"


def render() -> None:
    st.markdown("### About")
    st.markdown(f"""
**What** — for every HKIA passenger departure, the probability it leaves more than 15 min late and the expected delay in minutes,
from live schedule + weather data, with an honest evaluation page. Departures only (v1).

**Architecture (10 lines)**
1. GitHub Actions cron (`ingest.yml`, every 30 min, $0) checks out this repo.
2. `hkia.ingest_flights` pulls yesterday/today/tomorrow's departures from the Airport Authority flight-info API on data.gov.hk (scheduled vs actual = the label).
3. `hkia.ingest_weather` pulls the latest VHHH METAR (aviationweather.gov) and HKO current readings + warnings (typhoon signals) into SQLite `data/hkia.db`.
4. `hkia.features` builds the same 33 features for training and inference (calendar, airline/destination, congestion, as-of weather, point-in-time rolling delays).
5. `hkia.train` (offline, occasionally) fits baselines + XGBoost on a date-ordered split → `models/`, `reports/M2-results.md`.
6. `hkia.predict` (every cron run) scores every not-yet-departed flight for today + tomorrow → table `predictions` (history kept).
7. A daily job (`backfill.yml`) tops up METAR history (IEM) + typhoon-signal history and runs `hkia.evaluate` (last score before departure vs actual).
8. The bot commits `data/hkia.db` back to `main` — the db in git *is* the data store.
9. `hkia.api` (FastAPI) serves the same tables read-only; this Streamlit page reads the db directly.
10. Streamlit Community Cloud redeploys from `main`, so each bot commit refreshes this page.

**Data sources**
- [HKIA flight information — data.gov.hk / Airport Authority](https://data.gov.hk/en-data/dataset/aahk-team1-flight-info) (real-time + ~91-day history)
- [Hong Kong Observatory Open Data API](https://data.gov.hk/en-data/dataset/hk-hko-rss-current-weather-report) (current readings, warnings, TC signals) and the [HKO warning database](https://www.hko.gov.hk/en/wxinfo/climat/warndb/warndb1.shtml)
- [adsb.lol](https://api.adsb.lol/) live ADS-B positions for the map (community feed, free, no key) — display only, not a model input
- [aviationweather.gov METAR](https://aviationweather.gov/data/api/) for VHHH; historical METAR from the [IEM ASOS archive](https://mesonet.agron.iastate.edu/request/download.phtml)

**Code** — [{REPO.replace('https://', '')}]({REPO}) · README has the run book, `reports/M2-results.md` the numbers, `docs/features.md` the feature dictionary.

**Author** — Darren Wong, HKUST CS + AI. Built as a genuine-interest aviation + ML project and an ML-engineering showcase.
""")
