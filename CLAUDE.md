# HKIA Flight Delay Predictor

Live flight-delay prediction for Hong Kong International Airport departures, using real flight and weather data, served through a public dashboard. Owner: Darren (final-year HKUST CS + AI). Purpose: genuine-interest project (aviation + ML) that doubles as an ML-engineering showcase for job applications — especially Cathay Pacific D&IT and bank/quant tech interviews. Target: one project finished deeply — deployed, documented, with real data and honest evaluation numbers.

## What "done" looks like (v1)
A public URL showing: today's HKIA departures, each with a predicted delay probability/expected delay, model confidence, and the live weather context — refreshed automatically — plus an honest "model performance" page (baseline vs model, evaluation methodology). A README good enough that an interviewer can understand the architecture in 2 minutes.

## Scope guardrails (important)
- v1 = HKIA **departures only**. No arrivals, no other airports, no gate predictions.
- Exactly 3 data sources for v1 (below). Resist adding more until deployed.
- Baseline model first (gradient boosting). No deep learning until the baseline is deployed and beaten.

## Data sources (all free)
1. **HKIA flight info** — data.gov.hk hosts the Airport Authority's real-time + historical flight information API (departures with scheduled vs actual times, airline, destination, status). This is the ground-truth label source (delay = actual − scheduled).
2. **Weather** — Hong Kong Observatory open data API on data.gov.hk (current + forecast), plus METAR/TAF for VHHH from aviationweather.gov for aviation-specific conditions (visibility, wind, ceiling).
3. **ADS-B (stretch, can defer past v1)** — OpenSky Network API (free, historical + live) for actual aircraft movements: inbound-aircraft lateness is a strong predictor of departure delay (late inbound = late turnaround). adsb.lol as fallback.

Verify each API's current terms/rate limits before building against it.

## Architecture (keep boring and cheap)
- **Ingestion**: Python jobs on a scheduler (cron on the host, or GitHub Actions on a schedule for free) polling flight + weather APIs into **SQLite → migrate to Postgres only if needed**.
- **Feature/label builder**: batch job producing a training table. Candidate features: scheduled hour/day-of-week, airline, destination region, aircraft turnaround proxy, rolling airport congestion (departures scheduled in ±1h window), HKO weather at scheduled time, METAR visibility/wind, typhoon signal flags, holiday calendar, and (stretch) inbound-aircraft delay from ADS-B.
- **Model**: scikit-learn/XGBoost. Two targets to try: (a) classification — P(delay > 15 min); (b) regression on delay minutes. Proper time-based train/test split (never random — leakage). Baseline to beat: "predict the airline+hour historical average".
- **Serving**: FastAPI endpoint scoring today's schedule; predictions cached in the DB.
- **Dashboard**: Streamlit for fastest v1 (deployable free on Streamlit Community Cloud) — or Next.js later if it deserves polish. Charts: today's departures table with predictions, delay-by-hour heatmap, model performance page.
- **Deploy**: Streamlit Cloud / Fly.io / Render free tier. Ingestion via GitHub Actions cron keeps it $0.

## Milestones
- **M0 — Data recon (1 evening)**: hit all 3 APIs, confirm fields/limits, save raw samples. Decision point: is scheduled-vs-actual reliably available historically? How far back?
- **M1 — Dataset builder (2–3 evenings)**: ingestion jobs + accumulating SQLite of flights & weather. Start it early — labeled data accrues while you do other things (job apps!).
- **M2 — Baseline + model (2–3 evenings)**: feature table, time-split evaluation, XGBoost vs naive baseline. Honest metrics (AUC / MAE, calibration).
- **M3 — Live service (2 evenings)**: FastAPI scoring of today's schedule on a schedule.
- **M4 — Public dashboard + deploy (2–3 evenings)**.
- **M5 — README + writeup (1 evening)**: architecture diagram, findings (e.g., "typhoon signal 3 adds X min expected delay"), limitations. Then a CV bullet with real numbers.

## Working notes for Claude sessions in this repo
- Python 3.12+, venv in `.venv/`. Keep secrets in `.env` (git-ignored) — API keys never committed.
- Prefer small verifiable steps: every milestone ends with something runnable.
- Owner's time is scarce (job application season, ~2 evenings/week max here). When asked "what next", pick the smallest step that advances the current milestone; push back on scope creep — v1 guardrails above win arguments.
- Context: owner's job-hunt materials live in `~/Desktop/Job Hunting 2026-2027/` (tracker + prep plan). This project feeds the Cathay Pacific D&IT application (opens ~Sept 2026) — a working M2 with honest numbers by early October is worth more than a perfect M4 in December.
