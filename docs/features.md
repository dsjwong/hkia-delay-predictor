# Feature dictionary (M2) — `data/features.parquet`

Built by `python -m hkia.features` from `data/hkia.db` (tables `flights`, `metar_hist` + `metar`, `tc_signals`).
One row per HKIA passenger departure that either departed (label present) or was cancelled. Rows with a blank /
in-progress status (not yet departed) are dropped. Times in the parquet are UTC; features that mention "local" use HKT.

## Identity / label columns (not model inputs)
| column | meaning |
|---|---|
| `date` | HKIA calendar day of the scheduled departure (HKT) |
| `flight_no` | operating flight number, e.g. `CX 255` |
| `scheduled_ts`, `actual_ts` | UTC timestamps (source strings are +08:00) |
| `cancelled` | 1 if status was `Cancelled` (label columns are NaN for these rows) |
| `delay_min` | **regression label** = actual − scheduled in minutes; rows < −60 or > 600 are dropped and counted (44 in the first build: 1 low, 43 high) |
| `delayed15` | **classification label** = `delay_min > 15` |

## Model features (38) — `hkia.features.FEATURES`
Categorical (XGBoost native categoricals; categories fixed from the train split, unseen → missing):
| column | meaning |
|---|---|
| `airline` | ICAO code of the operating carrier (`UNK` if missing) |
| `dest` | first-leg destination IATA if in the top-30 by row count, else `OTHER` |
| `dest_region` | coarse region from `hkia.regions` (CN_MAINLAND, TAIWAN, JAPAN, KOREA, SE_ASIA, SOUTH_ASIA, OCEANIA, EUROPE, N_AMERICA, MIDDLE_EAST, AFRICA, CENTRAL_ASIA, RUSSIA, OTHER) |
| `terminal` | `T1` / `T2` / `UNK` |
| `flt_cat` | flight category of the joined METAR (VFR/MVFR/IFR/LIFR/UNK) |

Calendar (HKT):
| column | meaning |
|---|---|
| `sched_hour`, `sched_minute_of_day`, `sched_dow` (Mon=0), `is_weekend` | from scheduled time |
| `is_holiday` | HK general holiday (`hkia.holidays`, verified list for 2026; Sundays not flagged) |
| (`sched_month`) | present in the parquet but **excluded from FEATURES**: with 3 months of data it is a time proxy |

Congestion (from *all* scheduled rows incl. cancelled — the schedule is known in advance):
| column | meaning |
|---|---|
| `cong_pm60`, `cong_pm30` | other scheduled departures within ±60 / ±30 min |
| `cong_same_hour` | other departures scheduled in the same HKT clock hour |
| `n_dest_legs` | number of destination codes on the row (multi-leg flights) |

Weather — latest METAR **strictly before** scheduled time (as-of join, `allow_exact_matches=False`, 3 h tolerance).
Source = union of `metar_hist` (IEM ASOS archive, hourly, backfilled) and `metar` (live aviationweather, half-hourly);
duplicates by minute prefer the archive row.
| column | meaning |
|---|---|
| `temp_c`, `dewp_c`, `wdir`, `wspd_kt`, `wgst_kt` (0 if no gust) | as reported |
| `visib_sm` | visibility in statute miles (`6+` in the live feed → 6.21 = 9999 m) |
| `ceiling_ft` | lowest BKN/OVC/VV base; NaN when no ceiling (~99% of rows) |
| `wx_rain` (RA/DZ/SH), `wx_ts` (TS), `wx_fog` (FG/BR) | flags parsed from the present-weather string |
| `metar_age_min` | minutes between the observation and scheduled time |
| `tc_signal` | HKO tropical-cyclone signal in force at scheduled time (0/1/3/8/9/10) from `tc_signals` (HKO warning DB, HKT) |
| `msn_signal` | 1 if the Strong Monsoon Signal was in force |

Rolling delay features — **point-in-time**: only flights whose `actual_ts < scheduled_ts − 2 h` contribute
(`hkia.features.PIT_LAG`); outlier-labelled flights are excluded from the history. Tested in `tests/test_features.py`.
| column | meaning |
|---|---|
| `airline_prevday_mean_delay`, `airline_prevday_n` | mean delay / count of the same airline's flights dated the previous HKT day that had already departed by the cutoff |
| `airline_sameday_mean_delay`, `airline_sameday_n` | same, for the same day |
| `airport_sameday_mean_delay`, `airport_sameday_n` | all airlines, same day |

Inbound aircraft (turnaround) — from `aircraft_links` (`method='stand_gate'` only; `method='adsb_hex'` links are validation-only,
see [`inbound-feature.md`](inbound-feature.md)) joined to `arrivals` for the inbound's scheduled arrival.
**Same point-in-time cutoff as the rolling block**: the inbound counts only if it was **on blocks strictly before
`scheduled_ts − 2 h`**. An inbound that goes on blocks after the cutoff, one that never lands, and a departure with no
link at all are all encoded identically — because at the cutoff the model knew the same thing about all three (nothing).
| column | meaning |
|---|---|
| `inbound_known` | 1 if the linked inbound was on blocks before the cutoff, else 0. **Always 0/1, never NaN and never imputed** — missingness is the signal, so it gets its own feature |
| `inbound_actual_slack_min` | scheduled departure − inbound on-blocks, i.e. the turnaround the aircraft actually got |
| `inbound_lateness_min` | inbound on-blocks − inbound scheduled arrival (signed; NaN when the arrivals row is absent) |
| `inbound_sched_slack_min` | scheduled departure − inbound scheduled arrival, i.e. the *planned* turnaround |
| `inbound_confidence` | link confidence from `hkia.rotations` (1.0 unambiguous, 0.6 when two departures fitted one arrival) |

The four value columns are **NaN whenever `inbound_known` is 0** and ride XGBoost's native missing branch; zeros are
never imputed. Because the stand is published only ~2–3 h ahead and the cutoff is 2 h, this block is a *long-turnaround
indicator* for short-horizon scoring — it is blind to an inbound that is still in the air. Training compensates for the
coverage gap with `hkia.train --inbound-dropout`; the ship decision is gated by `scripts/inbound_gate.py`.

## Weather backfill (`python -m hkia.backfill_weather`)
- `metar_hist`: IEM ASOS `asos.py` request, `station=VHHH`, `report_type=3` (routine hourly METAR), `tz=Etc/UTC`, fetched in monthly
  chunks with retry on the frequent "server over capacity" 503. First run: 2,249 obs, 2026-05-15T00Z .. 2026-08-16T16Z (99.7% of hours).
  Temperatures converted °F→°C, wind kt as-is, `flt_cat` derived from visibility + ceiling with the standard VFR/MVFR/IFR/LIFR thresholds.
- `tc_signals`: HKO's warning database file `https://www.hko.gov.hk/dps/wxinfo/climat/warndb/tc.dat` (tab-separated, since 1946, incl.
  provisional 2026 rows and Strong Monsoon Signal rows). Loaded whole (2,504 rows). In the flight window: signal 1 on 2–4 Jul, and
  Severe Typhoon Noul 24–26 Jul (1 → 3 → 8NW → 9 → 8SW → 3 → 1). HKO `warnsum` snapshots (`hko_warnings`) accrue from 2026-08-15 only and are not yet used.
- Idempotent: `INSERT OR REPLACE` on `report_time` / `(signal, start_ts)`.

## Inference (`python -m hkia.predict`)
Same `build_features` call over the whole flights table with `keep_unlabelled=True` and `top_dest` = the destination categories the model
was trained with, so congestion, calendar and point-in-time rolling features are computed identically. Differences that are inherent to
scoring ahead of time: (1) rows scheduled after "now" get the latest METAR observation instead of the as-of observation, with
`metar_age_min` capped at 180; (2) the rolling delay features only see flights that have already departed as of scoring time, which for a
flight several hours out is fewer than the training-time cutoff of scheduled − 2 h. (3) The inbound block is additionally **gated on "now"**:
`build_features(..., now=<scoring time>)` uses inbound state only for flights whose scheduled − 2 h cutoff has already been reached, so a
flight scored five hours out gets the same all-missing block an unlinked flight gets — never a value the airport had not published yet.
Serve-time inbound coverage per forecast-horizon bucket is logged to `ingest_log` on every run, which is the drift monitor for the
`--inbound-dropout` rate the model was trained with. Predictions are appended to `predictions`
(`features_hash` = md5 of the feature vector; a flight is re-scored only when it changes) and evaluated by `hkia.evaluate`.

## Per-flight explanations (`hkia.explain`)
The same scoring pass asks the booster for local SHAP values (`Booster.predict(..., pred_contribs=True)`, one contribution per feature
plus a bias term, in log-odds, summing exactly to the margin) and keeps the **top 3 by |contribution|** for each flight.

- **Units.** The apps show probability points, linearised at the flight's own prediction: `pp = 100 · c · p · (1 − p)`. First-order
  approximation — the three numbers do not add up to `p − p_base`; the exact log-odds value is stored and is what the ranking uses.
- **Text.** One hand-written template per feature in `hkia.explain.TEMPLATES` (every name in the table above has one; a missing value
  gets its own line from `MISSING`, e.g. `ceiling_ft` → "no cloud ceiling reported"). `tests/test_explain.py` asserts the coverage
  against this file, so a new feature must arrive with its template. A stored item carries a 4th element when the row *has* a
  categorical value the model never saw (`to_matrix` maps unseen categories to missing) — it renders as "XYZ: airline not in the
  model's training data" rather than falsely claiming the flight has no airline.
- **Storage.** Table `explanations` — `PRIMARY KEY (date, flight_no, scheduled_ts)`, i.e. **the latest score only**, `INSERT OR
  REPLACE`d on every re-score and pruned to `today − 1 … tomorrow` (`hkia.explain.KEEP_DAYS`); a row whose probability and
  attributions are unchanged is not rewritten at all, so an idle cron run leaves the db byte-identical. It stores `[[feature, value,
  logodds], …]`, not the rendered sentence, so editing a template changes what the apps show without re-scoring anything.
- **Publication.** `hkia.export_json` renders the templates and adds `"why": [[direction, one-liner, pp], …]` to each **not-yet-departed**
  flight of `departures_*.json` (direction is `+1` when the feature pushed P up). Older snapshots simply have no `why` key; both
  frontends render an empty state.
- **What it is not.** A SHAP value describes this model's output, not the world: it is not a causal effect and not a what-if.
