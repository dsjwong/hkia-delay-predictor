# Live evaluation — predictions vs actuals

Generated 2026-09-30T22:13:39+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3080**.

Dates 2026-09-24..2026-10-01; observed P(delay > 15) = 0.1964; median lead time between last score and departure = 154.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6861 | 0.1468 | 0.4611 | 14.069 |
| baseline_airline_hour | 0.6468 | 0.157 | 0.4892 | 17.748 |
| naive_rate | 0.5 | 0.1578 | 0.4954 | 14.159 |

Coverage: **3080 of 3119** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3080 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0393 | [+0.0198, +0.0597] | **yes** |
| brier | -0.0102 | [-0.0131, -0.0074] | **yes** |
| logloss | -0.0281 | [-0.0364, -0.0202] | **yes** |
| mae | -3.68 | [-3.9591, -3.4180] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-24 † | 390 | 0.1769 | 0.6707 | 0.6567 | 0.1384 | 12.6 | 17.3 |
| 2026-09-25 | 447 | 0.1790 | 0.7152 | 0.6696 | 0.1362 | 12.5 | 15.9 |
| 2026-09-26 | 436 | 0.2271 | 0.6941 | 0.6609 | 0.1595 | 13.6 | 17.2 |
| 2026-09-27 | 441 | 0.2336 | 0.6558 | 0.6288 | 0.1685 | 15.8 | 18.3 |
| 2026-09-28 | 438 | 0.1895 | 0.7088 | 0.6497 | 0.1411 | 15.2 | 19.3 |
| 2026-09-29 | 434 | 0.2258 | 0.7049 | 0.6335 | 0.1557 | 16.5 | 20.1 |
| 2026-09-30 | 452 | 0.1438 | 0.6223 | 0.6383 | 0.1286 | 12.5 | 16.8 |
| 2026-10-01 *† | 42 | 0.1905 | 0.6985 | 0.6507 | 0.1404 | 10.3 | 12.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 116 | 0.8103 | 0.6871 | 0.5924 | 73.1 |
| < 30 min | 287 | 0.1916 | 0.6522 | 0.5556 | 13.0 |
| 30–120 min | 917 | 0.2072 | 0.7442 | 0.6664 | 12.0 |
| 2–12 h | 1724 | 0.1537 | 0.6403 | 0.6320 | 11.5 |
| > 12 h * | 36 | 0.0278 | 0.9429 | 0.7429 | 6.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 560 | 0.068 | 0.080 |
| 0.1-0.2 | 908 | 0.148 | 0.118 |
| 0.2-0.3 | 710 | 0.248 | 0.237 |
| 0.3-0.4 | 555 | 0.345 | 0.252 |
| 0.4-0.5 | 238 | 0.439 | 0.311 |
| 0.5-0.6 | 74 | 0.540 | 0.568 |
| 0.6-0.7 * | 22 | 0.643 | 0.909 |
| 0.7-0.8 * | 7 | 0.729 | 0.429 |
| 0.8-0.9 * | 6 | 0.835 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-27 | SWR | ZRH | 0.85 | 31.7 | 38 min |
| LX 139 | 2026-09-29 | SWR | ZRH | 0.85 | 33.3 | 23 min |
| VJ 985 | 2026-09-29 | VJC | PQC | 0.84 | 39.4 | 35 min |
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| VJ 985 | 2026-09-26 | VJC | PQC | 0.82 | 38.0 | 78 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 13 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (69%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-09-30 | HKE | HND | 0.02 | -4.3 | 59 min |
| UO 670 | 2026-09-29 | HKE | NGO | 0.03 | -3.8 | 19 min |
| SQ 895 | 2026-09-29 | SIA | SIN | 0.03 | -0.3 | 28 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| LX 139 | 2026-09-30 | SWR | ZRH | 0.72 | 23.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3080 | 0.6861 | 0.1468 | 0.4611 | 14.1 | 2026-09-22T17:06:51+00:00 | 2026-09-30T14:23:16+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3080}
