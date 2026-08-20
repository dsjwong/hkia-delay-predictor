# Deploying — Streamlit Community Cloud (dashboard) and GitHub Pages (web app)

Two front-ends read the same data: the Streamlit dashboard (`app/`, Streamlit Community Cloud — first section) and the static React web app
(`web/`, GitHub Pages — [second section](#web-app-github-pages)). Both stay up; the Streamlit app is the fallback.

## Dashboard — Streamlit Community Cloud

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

## Web app — GitHub Pages

The static app in `web/` is built by `.github/workflows/pages.yml` (Node 22, `npm ci && npm run lint && npm test -- --run && npm run build`,
smoke check that `dist/index.html` has the root and `dist/data/meta.json` exists, then `actions/upload-pages-artifact` + `actions/deploy-pages`).
URL: **https://darrenwongsj.dev/hkia-delay-predictor/** (Vite `base: '/hkia-delay-predictor/'`, hash router so deep links work without a 404 rule).

### Assets
Everything the page needs is in the Pages artifact: Inter is bundled from `@fontsource-variable/inter` (no font CDN), the CARTO dark-matter
basemap style/tiles and the data JSON are the only runtime requests besides the ADS-B feed. Design tokens: `docs/design.md`.

### One-time setup
- Pages source must be **GitHub Actions**. Done on 2026-08-19 via `gh api -X POST repos/dsjwong/hkia-delay-predictor/pages -f build_type=workflow`.
  If it ever needs redoing by hand: repo → Settings → Pages → Build and deployment → Source: *GitHub Actions*.
- Optional but recommended — a relay for the live ADS-B feed (see "CORS" below): `cd web/worker && npx wrangler login && npx wrangler deploy`
  (Cloudflare Workers free tier, ~1 min), then repo → Settings → Secrets and variables → Actions → **Variables** → `ADSB_PROXY_URL` =
  `https://hkia-adsb-proxy.<your-subdomain>.workers.dev/`, and re-run `pages.yml` (Actions → pages → Run workflow). The build reads it as
  `VITE_ADSB_URL`. No secret is involved; the worker only forwards one fixed upstream URL.

### How fresh data reaches the page without rebuilding
- `ingest.yml` (every 30 min) and `backfill.yml` (daily) run `python -m hkia.export_json` and commit `web/public/data/*.json` next to the DB.
- The deployed page fetches those files from `https://raw.githubusercontent.com/dsjwong/hkia-delay-predictor/main/web/public/data/` (sends
  `access-control-allow-origin: *`, `cache-control: max-age=300`; the app adds a 5-minute cache-bust bucket) and re-polls every 5 minutes while
  open. If raw.githubusercontent is unreachable it falls back to the copy bundled into the Pages artifact (`/data/`, as of the last build).
- Pushes made by the bot with `GITHUB_TOKEN` do **not** trigger other workflows (GitHub rule), so the 48 data commits/day never rebuild Pages —
  that is intended. `pages.yml` runs on human pushes touching `web/**` (and `workflow_dispatch`). Rebuilding costs ~1 min of Actions time; the
  repo is public, so Actions minutes are free anyway.
- Alternative considered: copying the JSON into the Pages artifact from the cron jobs (rebuild 48×/day). Rejected as the chattier option; the
  raw-CDN read is simpler and the bundled copy still makes the artifact self-contained.

### CORS and the live aircraft feed
`api.adsb.lol`, `opendata.adsb.fi`, `api.airplanes.live` and anonymous OpenSky return no `Access-Control-Allow-Origin` (OpenSky echoes only its
own origin), verified 2026-08-19 with `curl -H "Origin: https://dsjwong.github.io"` and from a real Chrome tab (all `Failed to fetch`). The
Streamlit app does not have this problem because it fetches server-side. The web app's order of attempts (`web/src/lib/adsb.ts`):
1. `VITE_ADSB_URL` — your relay (above). Polled every 8 s.
2. the direct adsb.lol URL (in case they add CORS upstream). 8 s.
3. `https://api.cors.lol/?url=…` public proxy — works but rate-limits to roughly one request per minute (429 otherwise), so it is polled
   every 60 s with exponential backoff on failures; the badge says "via public CORS proxy". Icons still glide (dead-reckoning, capped at 90 s).
Whichever route works is kept (sticky). With nothing working the map shows the basemap, the rings and a notice with the fix; everything
else on the site (snapshots, charts, flight cards) works regardless.

### Local check
```
cd web && npm ci
npm run dev                   # http://localhost:5173/hkia-delay-predictor/ (reads web/public/data/)
npm test -- --run && npm run lint && npm run build && npm run preview
```
Optional: a captured feed frame (`curl https://api.adsb.lol/v2/lat/22.308/lon/113.918/dist/100 -o web/public/_adsb_sample.json`, git-ignored)
plus `VITE_ADSB_URL=/hkia-delay-predictor/_adsb_sample.json npm run dev` shows real aircraft in dev without any CORS relay.

### After a deploy
- `gh run list --workflow=pages.yml` — build + deploy take ~1 min; `curl -s -o /dev/null -w "%{http_code}" https://darrenwongsj.dev/hkia-delay-predictor/` → 200.
- A browser that still has the previous `index.html` open may fail to load a renamed chunk right after a deploy; the app's error boundary
  reloads once in that case.
