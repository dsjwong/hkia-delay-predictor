# Live evaluation — predictions vs actuals

Generated 2026-10-22T21:33:25+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3057**.

Dates 2026-10-16..2026-10-23; observed P(delay > 15) = 0.1658; median lead time between last score and departure = 131.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6744 | 0.1339 | 0.4294 | 13.113 |
| baseline_airline_hour | 0.6657 | 0.1446 | 0.4641 | 16.856 |
| naive_rate | 0.5 | 0.1383 | 0.4492 | 12.562 |

Coverage: **3057 of 3094** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3057 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0087 | [-0.0099, +0.0280] | no — CI straddles 0 |
| brier | -0.0107 | [-0.0136, -0.0076] | **yes** |
| logloss | -0.0347 | [-0.0480, -0.0237] | **yes** |
| mae | -3.74 | [-4.0244, -3.4601] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-16 † | 411 | 0.1265 | 0.6092 | 0.6133 | 0.1233 | 12.6 | 16.2 |
| 2026-10-17 | 441 | 0.1678 | 0.7029 | 0.6981 | 0.1335 | 14.0 | 17.7 |
| 2026-10-18 | 439 | 0.1458 | 0.7372 | 0.7121 | 0.1197 | 12.6 | 16.7 |
| 2026-10-19 | 447 | 0.1365 | 0.6465 | 0.6142 | 0.1164 | 11.7 | 17.0 |
| 2026-10-20 | 431 | 0.1346 | 0.6420 | 0.7145 | 0.1215 | 11.9 | 15.6 |
| 2026-10-21 | 432 | 0.1505 | 0.7223 | 0.7706 | 0.1201 | 10.2 | 14.1 |
| 2026-10-22 | 420 | 0.2810 | 0.6632 | 0.6445 | 0.1913 | 19.0 | 21.1 |
| 2026-10-23 *† | 36 | 0.4167 | 0.5524 | 0.5762 | 0.2994 | 13.7 | 12.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 112 | 0.6607 | 0.6675 | 0.6469 | 44.2 |
| < 30 min | 323 | 0.1858 | 0.7327 | 0.6691 | 13.9 |
| 30–120 min | 1059 | 0.1653 | 0.6428 | 0.6347 | 12.4 |
| 2–12 h | 1537 | 0.1275 | 0.6757 | 0.6830 | 11.3 |
| > 12 h * | 26 | 0.0769 | 0.9375 | 0.9688 | 6.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 691 | 0.067 | 0.056 |
| 0.1-0.2 | 929 | 0.147 | 0.132 |
| 0.2-0.3 | 723 | 0.248 | 0.195 |
| 0.3-0.4 | 467 | 0.340 | 0.259 |
| 0.4-0.5 | 166 | 0.444 | 0.277 |
| 0.5-0.6 | 62 | 0.543 | 0.371 |
| 0.6-0.7 * | 11 | 0.630 | 0.818 |
| 0.7-0.8 * | 6 | 0.727 | 0.500 |
| 0.8-0.9 * | 2 | 0.854 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| VJ 985 | 2026-10-22 | VJC | PQC | 0.84 | 42.4 | 33 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |
| JX 236 | 2026-10-22 | SJX | TPE | 0.71 | 41.6 | 51 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 8 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (62%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3057 | 0.6744 | 0.1339 | 0.4294 | 13.1 | 2026-10-15T15:39:53+00:00 | 2026-10-22T17:24:17+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3057}
