"""About page."""
from __future__ import annotations

import streamlit as st

REPO = "https://github.com/dsjwong/hkia-delay-predictor"


def render() -> None:
    st.markdown(
        "For every HKIA passenger departure: the probability it leaves more than 15 min late and the expected delay in minutes, "
        "from live schedule + weather data, with an honest evaluation page. Departures only (v1).")
    c1, c2 = st.columns([3, 2], gap="large")
    c1.markdown("#### Architecture")
    c1.markdown(f"""
1. GitHub Actions cron (`ingest.yml`, every 30 min, $0) checks out this repo and pulls the live SQLite db from the repo's `data` GitHub Release (`hkia.dbsync`).
2. `hkia.ingest_flights` pulls yesterday/today/tomorrow's departures from the Airport Authority flight-info API on data.gov.hk (scheduled vs actual = the label).
3. `hkia.ingest_weather` pulls the latest VHHH METAR (aviationweather.gov) and HKO current readings + warnings (typhoon signals) into SQLite `data/hkia.db`.
4. `hkia.features` builds the same 33 features for training and inference (calendar, airline/destination, congestion, as-of weather, point-in-time rolling delays).
5. `hkia.train` (offline, occasionally) fits baselines + XGBoost on a date-ordered split → `models/`, `reports/M2-results.md`.
6. `hkia.predict` (every cron run) scores every not-yet-departed flight for today + tomorrow → table `predictions` (history kept).
7. A daily job (`backfill.yml`) tops up METAR history (IEM) + typhoon-signal history and runs `hkia.evaluate` (last score before departure vs actual).
8. The bot uploads `data/hkia.db` back to the release (single writer; checksum + row-count guard) and commits only the small JSON snapshots the web app reads.
9. `hkia.api` (FastAPI) serves the same tables read-only; this Streamlit page downloads the db on start and re-checks a 1 KB sidecar every 10 min.
10. Streamlit Community Cloud redeploys from `main` on code changes; data refreshes without a redeploy.
""")
    c2.markdown("#### Data sources")
    c2.markdown(f"""
- [HKIA flight information — data.gov.hk / Airport Authority](https://data.gov.hk/en-data/dataset/aahk-team1-flight-info) (real-time + ~91-day history)
- [Hong Kong Observatory Open Data API](https://data.gov.hk/en-data/dataset/hk-hko-rss-current-weather-report) (current readings, warnings, TC signals) and the [HKO warning database](https://www.hko.gov.hk/en/wxinfo/climat/warndb/warndb1.shtml)
- Live ADS-B positions for the map from [adsb.lol](https://api.adsb.lol/) → [OpenSky](https://opensky-network.org/) → [adsb.fi](https://adsb.fi/) → [airplanes.live](https://airplanes.live/) (first non-empty wins; free, no key; display only, not a model input)
- [aviationweather.gov METAR](https://aviationweather.gov/data/api/) for VHHH; historical METAR from the [IEM ASOS archive](https://mesonet.agron.iastate.edu/request/download.phtml)
""")
    c2.markdown("#### Code and author")
    c2.markdown(f"""
[{REPO.replace('https://', '')}]({REPO}) — README has the run book, `reports/M2-results.md` the numbers, `docs/features.md` the feature dictionary, `docs/design.md` the design system.

**Darren Wong**, HKUST CS + AI. Built as a genuine-interest aviation + ML project and an ML-engineering showcase.
""")
