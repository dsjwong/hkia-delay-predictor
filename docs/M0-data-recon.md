# M0 — Data recon (2026-08-15)

All URLs below were actually called on 2026-08-15 (HKT evening). Raw samples are in `data/raw/`.

## 1. HKIA flight information (Airport Authority via data.gov.hk)

- Dataset page: https://data.gov.hk/en-data/dataset/aahk-team1-flight-info (update frequency listed as "Daily (updated to previous calendar day)"; in practice the endpoint is live — see below).
- Spec PDF: https://www.hongkongairport.com/iwov-resources/misc/opendata/Flight_Information_DataSpec_en.pdf
- Endpoint (departures, passenger):
  `https://www.hongkongairport.com/flightinfo-rest/rest/flights/past?date=YYYY-MM-DD&lang=en&cargo=false&arrival=false`
  (`arrival=true` for arrivals, `cargo=true` for cargo — out of scope for v1.)
- Response: JSON list of day-objects `{date, arrival, cargo, list:[...], lastUpdatedTime}`. Usually one day-object for the requested date, sometimes a second small object for the previous date (late-night flights that departed after midnight — 4 rows for 2026-08-13 in the `date=2026-08-14` response).
- Row fields: `time` ("HH:MM", scheduled, HKT), `flight` (list of `{no, airline}` — first entry is the operating flight, others are codeshares), `status` (free text), `statusCode` (always null in samples), `destination` (list of IATA codes, multi-leg possible), `terminal`, `aisle` (check-in), `gate`.
- Status vocabulary observed:
  - Past days: `Dep HH:MM` (450/462), `Dep HH:MM (DD/MM/YYYY)` when actual departure is on a different calendar day, `Cancelled`.
  - Today (in-progress): `Dep HH:MM`, `Boarding Soon`, `Boarding`, `Final Call`, `Gate Closed`, `Delayed`, `Est at HH:MM [(date)]`, `Cancelled`, `""` (not yet started).
  - Future dates (`date=tomorrow` returns 200 with 454 rows, status mostly `""`) — i.e. the schedule for upcoming days IS available, which is what M3 needs.
- Volume: ~400–460 passenger departures/day.
- **Historical depth (probed empirically):** `date=` works from today back to **91 days** (2026-05-16 → 200 OK, 406 rows). 92+ days back → **HTTP 400** with empty body. So the endpoint is a rolling ~3-month window.
- Refresh cadence: `Cache-Control: public, max-age=30`; `lastUpdatedTime` in the payload looked stale/odd (said 17:12 while rows showed 23:xx departures) — do not trust it, record our own `fetched_at`.
- Rate limits / terms: none stated in the spec; data.gov.hk standard terms of use. Gotcha: a request with `User-Agent: Python-urllib/3.14` (stdlib urllib default) gets **HTTP 403** from the WAF; `requests` default UA and curl are fine. Ingest sets an explicit UA.
- Timezone: all times are HKT (UTC+8) with no offset in the string. Scheduled = `date` + `time`. Actual = parsed from `Dep HH:MM [(DD/MM/YYYY)]`; when no date suffix, actual date = row date (verified: `Dep 00:23 (14/08/2026)` appears for a 23:15 flight on the 13th, so cross-midnight cases are marked explicitly).

## 2. Hong Kong Observatory open data

Base: `https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=<T>&lang=en`

| dataType | what | notes |
|---|---|---|
| `rhrread` | current readings | `temperature.data[]` has 26 stations incl. **"Chek Lap Kok"** (= HKIA). `rainfall.data[]` is per district — "Islands District" covers the airport. `humidity` only for HKO HQ. Also `warningMessage`, `tcmessage`, `uvindex`, `icon`. `updateTime`/`recordTime` are ISO with `+08:00`. Updated every ~10 min (recordTime on the hour/10-min). No wind in this feed (METAR covers wind). |
| `warnsum` | warning summary | returns `{}` when no warnings in force (as today). When active: `{"WTCSGNL": {code, name, actionCode, issueTime, updateTime, ...}, ...}` — `WTCSGNL` = tropical cyclone signal (TC1/TC3/TC8NE...), `WRAIN` = rainstorm (amber/red/black), `WTS` thunderstorm etc. Poll every run and store raw. |
| `warningInfo` | warning details | `{}` when none. |
| `flw` | local forecast text | `generalSituation`, `forecastPeriod`, `forecastDesc`, `tcInfo`, `fireDangerWarning`, `updateTime`. |
| `fnd` | 9-day forecast | `weatherForecast[]` per day: wind text, weather text, min/max temp & RH, PSR (rain probability class). |

- No history endpoint on this API — it is current-only. Historical HKO data exists as separate daily CSV datasets on data.gov.hk (not needed for v1: METAR history covers airport-relevant weather better).
- Terms: free, data.gov.hk terms; no key.

## 3. METAR / TAF for VHHH (aviationweather.gov)

- METAR: `https://aviationweather.gov/api/data/metar?ids=VHHH&format=json&hours=24` → 54 records/24h (half-hourly). Fields: `rawOb`, `reportTime` (UTC, ISO), `obsTime` (unix), `temp`, `dewp`, `wdir`, `wspd` (kt), `wgst` when gusting, `visib` ("6+" statute miles or a number), `altim`, `clouds[] {cover, base(ft)}`, `cover`, `fltCat` (VFR/MVFR/IFR/LIFR), `wxString` (e.g. `-SHRA`, `TS`), `qcField`.
- TAF: `https://aviationweather.gov/api/data/taf?ids=VHHH&format=json` → `rawTAF`, `validTimeFrom/To`, `fcsts[]`.
- **History:** `hours=` is capped at ~400 records (≈8 days for VHHH); a `date=` param returned 400. So aviationweather is live-only for our purposes.
- Historical METAR backfill option (verified working, not built yet): Iowa Environmental Mesonet ASOS archive, e.g.
  `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=VHHH&data=metar&year1=2026&month1=5&day1=15&year2=2026&month2=5&day2=16&tz=Etc/UTC&format=onlycomma&report_type=3` → CSV `station,valid,metar` (hourly). Use this in M2 to attach weather to the 91-day flight backfill.
- Timezone gotcha: METAR is **UTC**; flights are HKT. Convert before joining (`scheduled_ts` is stored as ISO with `+08:00`, METAR `reportTime` as `Z`).
- Terms: free, no key, be polite (they ask for reasonable request rates; every 30 min is fine).

## 4. OpenSky (stretch — deferred, not built)

- Docs: https://openskynetwork.github.io/opensky-api/rest.html (checked today). REST: `https://opensky-network.org/api/states/all?lamin=&lomin=&lamax=&lomax=` — anonymous GET around the HKIA bbox returned 200 today.
- Auth: **OAuth2 client-credentials only** (username/password basic auth no longer accepted); create an API client in the OpenSky account page, exchange for a token. Credits: anonymous 400/day (live states only, 10 s resolution), standard user 4,000/day, active feeder 8,000/day; separate buckets for `/states`, `/tracks`, `/flights`. Historical `/flights/arrival?airport=VHHH&begin=&end=` needs an account. Fallback: adsb.lol. Not touched in v1.

## DECISION

- **Scheduled-vs-actual departure times are reliably available historically for a rolling ~91-day window** (~400–460 passenger departures/day → roughly **40k labelled departures available immediately** on first backfill). Labels: `actual − scheduled` from `Dep HH:MM`; `Cancelled` is a separate class; anything else on a past day is treated as unlabelled.
- We do **not** have to wait weeks to reach 5k labels — one backfill run exceeds it. We must still accumulate our own history because the window rolls: after ~3 months anything not ingested is gone. The GitHub Actions cron (every 30 min) also snapshots in-progress statuses (`Est at`, `Delayed`, `Boarding`...) which are useful later for "live" features.
- Weather history: METAR from aviationweather only ~8 days; backfill via IEM archive in M2 for the 91-day flight window. HKO current readings/warnings are current-only, so those features start accruing from today. Typhoon-signal history can be reconstructed from HKO's public warning archive if needed (not verified).
- Cargo flights and arrivals are deliberately excluded (v1 guardrail), though the same endpoint serves them.

## Post-backfill sanity (M1, 2026-08-15)
- Backfill 2026-05-16 → 2026-08-16: **40,030 rows, 39,066 with `actual_ts`, 499 Cancelled**, 93 distinct dates.
- Raw delay = actual − scheduled: mean 18.2 min, 31% of departures > 15 min, range −115 min … +2013 min. Negative outliers exist (e.g. CX 181 on 2026-06-12 scheduled 00:45, "Dep 22:50 (11/06/2026)" — retimed earlier); treat < −60 min as retimed/dirty in M2 rather than as early departures.
