# Deploying the dashboard — Streamlit Community Cloud

The dashboard (`app/streamlit_app.py`) reads the committed `data/hkia.db` plus `models/MANIFEST.json`, `models/feature_importance.json`
and `reports/M2-results.md` straight from the repo checkout. Nothing is scored at request time, so the deploy needs no secrets,
no database server and no xgboost — just `requirements.txt` (pandas, numpy, streamlit, plotly, fastapi, uvicorn).

## Why Streamlit Community Cloud first
- $0, GitHub-native: it redeploys from `main` on every push — and the ingest bot pushes a fresh `data/hkia.db` every 30 min,
  so the app updates itself with no extra plumbing (the app also re-reads the db every 10 min via `st.cache_data(ttl=600)`).
- No Dockerfile / `Procfile` / `render.yaml` to maintain. Fly.io or Render would need a container plus a way to fetch the latest db
  (git pull in a cron, or object storage) — worth it only if we outgrow Cloud's limits (1 GB RAM, sleeps after inactivity, public apps).
- Streamlit is already the UI; the FastAPI service is optional (`uvicorn hkia.api:app`) and not deployed in v1.

## One-time steps (Darren, ~5 min)
1. Make sure `main` is green (`gh run list`) and the repo is **public** (or be ready to grant Streamlit access to the private repo
   during sign-in — Community Cloud can deploy private repos once the GitHub app is authorised for it).
2. Go to <https://share.streamlit.io> → **Sign in with GitHub** (account `dsjwong`) → authorise the Streamlit GitHub app for the repo.
3. **Create app** → *Deploy a public app from GitHub*:
   - Repository: `dsjwong/hkia-delay-predictor`
   - Branch: `main`
   - Main file path: `app/streamlit_app.py`
   - App URL: pick a subdomain, e.g. `hkia-delay-predictor` → the app lives at `https://hkia-delay-predictor.streamlit.app`
     (default pattern is `https://<subdomain>.streamlit.app`; if left blank Cloud generates `<repo>-<hash>.streamlit.app`).
   - Advanced settings: Python **3.12** (matches the Actions jobs; 3.11–3.13 all work). No secrets are needed.
4. Click **Deploy**. First build takes 2–4 min (installs `requirements.txt`, then runs the app with the repo's `.streamlit/config.toml`:
   headless, light theme, no usage stats).
5. Open the URL, check the sidebar shows **Data as of <recent HKT time>** and that *Today's departures* lists today's flights.
6. Paste the URL into the README's Dashboard section (`README.md`, "Live: …") and commit.

## What to expect afterwards
- Every bot commit (`ingest: …` every 30 min, `backfill: …` daily) triggers a Cloud redeploy (fast — dependencies are cached), so
  the page is never more than ~30 min behind the API. If you'd rather not redeploy that often, Cloud → app menu → *Settings* lets you
  reboot manually only, but then the app only sees new data on reboot; the default auto-redeploy is what we want.
- Db size: `data/hkia.db` is ~10 MB and grows a few hundred KB/day (`predictions` history + flights churn). Fine for git and for
  Cloud for months; the README limitations note the eventual move to Postgres/artifact storage.
- Sleep: public Community Cloud apps go to sleep after ~12 h without visitors and wake on the next visit (a few seconds).
- Logs: app menu → *Manage app* → logs, if a page errors. Locally the same page is `streamlit run app/streamlit_app.py`.

## Local check before deploying
```
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app/streamlit_app.py --server.headless true    # http://localhost:8501
.venv/bin/python -m pytest -q tests/test_app.py                          # AppTest smoke tests: all four pages render on the real db
```
