# HKIA Flight Delay Predictor

Predicting departure delays at Hong Kong International Airport from live flight and weather data — an ML-engineering showcase built on real, free, public data. **Current status: M1 (data ingestion running; no model yet).**

- **What**: for each HKIA passenger departure, predict P(delay > 15 min) / expected delay minutes, served on a public dashboard with honest evaluation numbers. v1 = departures only.
- **Data** (3 sources, all free): Airport Authority flight info API via data.gov.hk (scheduled vs actual departure = label; ~91-day rolling history), Hong Kong Observatory open data (current readings, warnings incl. typhoon signals), METAR for VHHH from aviationweather.gov. OpenSky ADS-B is a deferred stretch.
- **Architecture**: `src/hkia/ingest_*.py` poll the APIs into SQLite `data/hkia.db` → feature/label builder (M2) → XGBoost vs naive baseline with time-based split (M2) → FastAPI scoring (M3) → Streamlit dashboard (M4). GitHub Actions cron runs ingestion every 30 min for $0.
- **Recon findings**: see `docs/M0-data-recon.md` (URLs, fields, historical depth, gotchas). Headline: ~450 departures/day, 91 days back → ~40k labelled departures on first backfill.

## Run
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/ingest_all.py --backfill   # first time: whole ~91-day window (~2 min)
.venv/bin/python scripts/ingest_all.py              # yesterday/today/tomorrow + weather; idempotent
sqlite3 data/hkia.db "select count(*), sum(actual_ts is not null) from flights"
```

## Known limitations
- The SQLite file is committed back to the repo by the Actions cron; at ~8 MB and growing this will bloat git history — migrate to Postgres/Supabase (or artifact storage) before it hurts.
- HKO/METAR history only accrues from the day ingestion started; historical METAR backfill via the IEM archive is planned for M2.
