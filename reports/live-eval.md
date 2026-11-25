# Live evaluation — predictions vs actuals

Generated 2026-11-25T02:23:08+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2827**.

Dates 2026-11-18..2026-11-25; observed P(delay > 15) = 0.1737; median lead time between last score and departure = 219.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6314 | 0.1441 | 0.4583 | 12.624 |
| baseline_airline_hour | 0.579 | 0.1539 | 0.4858 | 15.413 |
| naive_rate | 0.5 | 0.1435 | 0.4617 | 11.559 |

Coverage: **2827 of 2960** departures in the window (95.5%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2827 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0524 | [+0.0224, +0.0796] | **yes** |
| brier | -0.0098 | [-0.0129, -0.0065] | **yes** |
| logloss | -0.0275 | [-0.0361, -0.0184] | **yes** |
| mae | -2.79 | [-3.0304, -2.5278] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-18 † | 276 | 0.2500 | 0.7365 | 0.6053 | 0.1627 | 14.9 | 17.9 |
| 2026-11-19 | 406 | 0.1478 | 0.5617 | 0.5470 | 0.1366 | 12.7 | 15.2 |
| 2026-11-20 | 424 | 0.2476 | 0.5754 | 0.5410 | 0.1892 | 14.3 | 15.3 |
| 2026-11-21 | 430 | 0.1605 | 0.5796 | 0.5807 | 0.1561 | 13.0 | 15.2 |
| 2026-11-22 | 427 | 0.1358 | 0.6490 | 0.5757 | 0.1155 | 10.5 | 14.7 |
| 2026-11-23 | 425 | 0.1412 | 0.6263 | 0.6116 | 0.1223 | 11.1 | 15.6 |
| 2026-11-24 | 404 | 0.1634 | 0.6589 | 0.5917 | 0.1365 | 12.9 | 15.2 |
| 2026-11-25 *† | 35 | 0.1143 | 0.7903 | 0.8508 | 0.0922 | 8.5 | 10.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 57 | 0.7018 | 0.7603 | 0.6956 | 48.6 |
| < 30 min | 167 | 0.1677 | 0.6520 | 0.6005 | 11.1 |
| 30–120 min | 601 | 0.1930 | 0.6218 | 0.5518 | 13.1 |
| 2–12 h | 1931 | 0.1543 | 0.6222 | 0.5757 | 11.7 |
| > 12 h * | 71 | 0.1268 | 0.8047 | 0.6093 | 7.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 378 | 0.069 | 0.077 |
| 0.1-0.2 | 869 | 0.151 | 0.148 |
| 0.2-0.3 | 826 | 0.247 | 0.157 |
| 0.3-0.4 | 499 | 0.343 | 0.230 |
| 0.4-0.5 | 185 | 0.436 | 0.314 |
| 0.5-0.6 | 54 | 0.540 | 0.426 |
| 0.6-0.7 * | 13 | 0.627 | 0.385 |
| 0.7-0.8 * | 2 | 0.741 | 1.000 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |
| VJ 877 | 2026-11-21 | VJC | SGN | 0.67 | 35.5 | 90 min |
| OD 606 | 2026-11-18 | MXD | KUL | 0.63 | 41.4 | 264 min |
| VJ 877 | 2026-11-24 | VJC | SGN | 0.62 | 29.0 | 45 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 3 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (67%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 794 | 2026-11-23 | CCA | HGH | 0.04 | 3.9 | 27 min |
| CA 412 | 2026-11-24 | CCA | TFU | 0.04 | 2.6 | 23 min |
| UO 724 | 2026-11-23 | HKE | HKT | 0.04 | -0.2 | 116 min |
| RA 410 | 2026-11-21 | RNA | KTM | 0.91 | 54.4 | 12 min |
| JX 236 | 2026-11-21 | SJX | TPE | 0.66 | 23.1 | -1 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| e2c2178@2026-11-22T11:25:36+00:00 | 824 | 0.6340 | 0.1315 | 0.4251 | 12.2 | 2026-11-22T17:57:19+00:00 | 2026-11-24T11:12:27+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 2003 | 0.6309 | 0.1493 | 0.4720 | 12.8 | 2026-11-17T19:28:42+00:00 | 2026-11-22T10:28:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'e2c2178@2026-11-22T11:25:36+00:00': 824, 'f6ae66c@2026-11-01T10:28:21+00:00': 2003}
