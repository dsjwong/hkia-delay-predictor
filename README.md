# HKIA Flight Delay Predictor

Predicting departure delays at Hong Kong International Airport from live flight and weather data — an ML-engineering showcase built on real, free, public data. **Current status: M2 done (weather backfill, feature table, baselines vs XGBoost with a time-based split); M3 live scoring next.**

- **What**: for each HKIA passenger departure, predict P(delay > 15 min) / expected delay minutes, served on a public dashboard with honest evaluation numbers. v1 = departures only.
- **Data** (3 sources, all free): Airport Authority flight info API via data.gov.hk (scheduled vs actual departure = label; ~91-day rolling history), Hong Kong Observatory open data (current readings, warnings incl. typhoon signals), METAR for VHHH from aviationweather.gov. OpenSky ADS-B is a deferred stretch.
- **Architecture**: `src/hkia/ingest_*.py` poll the APIs into SQLite `data/hkia.db` (GitHub Actions cron every 30 min, $0) → `backfill_weather.py` adds historical METAR (IEM archive) + HKO typhoon-signal history → `features.py` builds `data/features.parquet` (33 features, point-in-time rolling stats, as-of weather join) → `train.py` fits baselines + XGBoost with a date-ordered 70/15/15 split and writes `models/` + `reports/M2-results.md` → FastAPI scoring (M3) → Streamlit dashboard (M4).
- **Headline numbers (test = last 14 days, 2026-08-03..16, 6,252 departures)**: P(delay > 15 min) AUC **0.661** (XGBoost) vs 0.623 (airline x hour baseline) vs 0.50 (global rate); log loss 0.575 / 0.585 / 0.604. Delay-minutes MAE **16.6** vs 18.5 (baseline) vs 17.4 (train median). Airline + destination + time of day explain most; weather adds ~+0.013 AUC; the point-in-time rolling delay features do not help AUC on test. Full tables, calibration and ablations: `reports/M2-results.md`; feature dictionary: `docs/features.md`.
- **Recon findings**: see `docs/M0-data-recon.md` (URLs, fields, historical depth, gotchas). Headline: ~450 departures/day, 91 days back → ~40k labelled departures on first backfill.

## Run
```
python3 -m venv .venv && .venv/bin/pip install -e .      # deps from requirements.txt; needs libomp on macOS for xgboost (brew install libomp)
.venv/bin/python scripts/ingest_all.py --backfill        # first time: whole ~91-day window (~2 min)
.venv/bin/python scripts/ingest_all.py                   # yesterday/today/tomorrow + weather; idempotent
.venv/bin/python -m hkia.backfill_weather                # IEM METAR history + HKO TC signals -> metar_hist, tc_signals (~2 min, retries on IEM 503)
.venv/bin/python -m hkia.features                        # -> data/features.parquet (not committed)
.venv/bin/python -m hkia.train                           # -> models/*.joblib, models/MANIFEST.json, reports/M2-results.md
.venv/bin/python -m pytest -q                            # feature-builder tests (leakage, as-of join, congestion)
```
The committed `data/hkia.db` only carries the live tables; run the backfill locally before building features.

## Known limitations
- The SQLite file is committed back to the repo by the Actions cron; at ~8 MB and growing this will bloat git history — migrate to Postgres/Supabase (or artifact storage) before it hurts.
- HKO current readings/warnings only accrue from 2026-08-15; historical METAR comes from the IEM ASOS archive (hourly) and typhoon-signal history from HKO's warning database (`docs/features.md`).
- 93 days of data in one season; the only typhoon (Noul, 25-26 Jul) falls in the validation split, so weather/typhoon effects are learned from a handful of days and unconfirmed on test. Numbers will move as data accrues — retrain and re-read the report before quoting them.
