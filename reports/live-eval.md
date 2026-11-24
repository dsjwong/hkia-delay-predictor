# Live evaluation — predictions vs actuals

Generated 2026-11-24T03:57:29+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2859**.

Dates 2026-11-17..2026-11-24; observed P(delay > 15) = 0.1784; median lead time between last score and departure = 230.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6137 | 0.1467 | 0.4665 | 12.741 |
| baseline_airline_hour | 0.572 | 0.1556 | 0.4902 | 15.687 |
| naive_rate | 0.5 | 0.1466 | 0.4689 | 12.009 |

Coverage: **2859 of 3019** departures in the window (94.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2859 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0417 | [+0.0142, +0.0691] | **yes** |
| brier | -0.0089 | [-0.0120, -0.0055] | **yes** |
| logloss | -0.0237 | [-0.0323, -0.0142] | **yes** |
| mae | -2.95 | [-3.1965, -2.6749] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-17 † | 238 | 0.2311 | 0.6362 | 0.5621 | 0.1697 | 17.4 | 21.7 |
| 2026-11-18 | 409 | 0.2152 | 0.6962 | 0.6051 | 0.1520 | 12.7 | 15.7 |
| 2026-11-19 | 406 | 0.1478 | 0.5617 | 0.5470 | 0.1366 | 12.7 | 15.2 |
| 2026-11-20 | 424 | 0.2476 | 0.5754 | 0.5410 | 0.1892 | 14.3 | 15.3 |
| 2026-11-21 | 430 | 0.1605 | 0.5796 | 0.5807 | 0.1561 | 13.0 | 15.2 |
| 2026-11-22 | 427 | 0.1358 | 0.6490 | 0.5757 | 0.1155 | 10.5 | 14.7 |
| 2026-11-23 | 425 | 0.1412 | 0.6263 | 0.6116 | 0.1223 | 11.1 | 15.6 |
| 2026-11-24 † | 100 | 0.1500 | 0.5482 | 0.5008 | 0.1287 | 10.4 | 11.7 |

`†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 54 | 0.6852 | 0.7806 | 0.6789 | 50.9 |
| < 30 min | 160 | 0.1562 | 0.6240 | 0.5702 | 14.6 |
| 30–120 min | 577 | 0.2010 | 0.6068 | 0.5474 | 13.6 |
| 2–12 h | 1965 | 0.1623 | 0.6035 | 0.5670 | 11.5 |
| > 12 h | 103 | 0.1262 | 0.7256 | 0.6154 | 8.8 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 432 | 0.069 | 0.102 |
| 0.1-0.2 | 939 | 0.151 | 0.165 |
| 0.2-0.3 | 814 | 0.246 | 0.154 |
| 0.3-0.4 | 438 | 0.343 | 0.233 |
| 0.4-0.5 | 174 | 0.435 | 0.310 |
| 0.5-0.6 | 48 | 0.543 | 0.500 |
| 0.6-0.7 * | 10 | 0.630 | 0.300 |
| 0.7-0.8 * | 2 | 0.741 | 1.000 |
| 0.8-0.9 * | 1 | 0.854 | 1.000 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-17 | RNA | KTM | 0.85 | 47.8 | 188 min |
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |
| VJ 877 | 2026-11-21 | VJC | SGN | 0.67 | 35.5 | 90 min |
| OD 606 | 2026-11-18 | MXD | KUL | 0.63 | 41.4 | 264 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 794 | 2026-11-23 | CCA | HGH | 0.04 | 3.9 | 27 min |
| CZ 356 | 2026-11-17 | CSN | PKX | 0.04 | -5.7 | 23 min |
| UO 724 | 2026-11-23 | HKE | HKT | 0.04 | -0.2 | 116 min |
| RA 410 | 2026-11-21 | RNA | KTM | 0.91 | 54.4 | 12 min |
| JX 236 | 2026-11-21 | SJX | TPE | 0.66 | 23.1 | -1 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| e2c2178@2026-11-22T11:25:36+00:00 | 485 | 0.5946 | 0.1295 | 0.4233 | 11.5 | 2026-11-22T17:57:19+00:00 | 2026-11-23T13:47:59+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 2374 | 0.6169 | 0.1503 | 0.4753 | 13.0 | 2026-11-16T18:44:06+00:00 | 2026-11-22T10:28:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'e2c2178@2026-11-22T11:25:36+00:00': 485, 'f6ae66c@2026-11-01T10:28:21+00:00': 2374}
