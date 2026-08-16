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

## Model features (33) — `hkia.features.FEATURES`
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

## Weather backfill (`python -m hkia.backfill_weather`)
- `metar_hist`: IEM ASOS `asos.py` request, `station=VHHH`, `report_type=3` (routine hourly METAR), `tz=Etc/UTC`, fetched in monthly
  chunks with retry on the frequent "server over capacity" 503. First run: 2,249 obs, 2026-05-15T00Z .. 2026-08-16T16Z (99.7% of hours).
  Temperatures converted °F→°C, wind kt as-is, `flt_cat` derived from visibility + ceiling with the standard VFR/MVFR/IFR/LIFR thresholds.
- `tc_signals`: HKO's warning database file `https://www.hko.gov.hk/dps/wxinfo/climat/warndb/tc.dat` (tab-separated, since 1946, incl.
  provisional 2026 rows and Strong Monsoon Signal rows). Loaded whole (2,504 rows). In the flight window: signal 1 on 2–4 Jul, and
  Severe Typhoon Noul 24–26 Jul (1 → 3 → 8NW → 9 → 8SW → 3 → 1). HKO `warnsum` snapshots (`hko_warnings`) accrue from 2026-08-15 only and are not yet used.
- Idempotent: `INSERT OR REPLACE` on `report_time` / `(signal, start_ts)`.
