# Live evaluation — predictions vs actuals

Generated 2026-10-24T20:45:31+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2991**.

Dates 2026-10-18..2026-10-25; observed P(delay > 15) = 0.1789; median lead time between last score and departure = 136.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6728 | 0.1402 | 0.4446 | 13.857 |
| baseline_airline_hour | 0.654 | 0.1514 | 0.4803 | 17.594 |
| naive_rate | 0.5 | 0.1469 | 0.4697 | 13.559 |

Coverage: **2991 of 3030** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2991 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0188 | [+0.0000, +0.0380] | **yes** |
| brier | -0.0112 | [-0.0142, -0.0082] | **yes** |
| logloss | -0.0357 | [-0.0493, -0.0249] | **yes** |
| mae | -3.74 | [-4.0194, -3.4430] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-18 † | 401 | 0.1521 | 0.7323 | 0.7149 | 0.1235 | 12.9 | 17.1 |
| 2026-10-19 | 447 | 0.1365 | 0.6465 | 0.6142 | 0.1164 | 11.7 | 17.0 |
| 2026-10-20 | 431 | 0.1346 | 0.6420 | 0.7145 | 0.1215 | 11.9 | 15.6 |
| 2026-10-21 | 432 | 0.1505 | 0.7223 | 0.7706 | 0.1201 | 10.2 | 14.1 |
| 2026-10-22 | 420 | 0.2810 | 0.6632 | 0.6445 | 0.1913 | 19.0 | 21.1 |
| 2026-10-23 | 396 | 0.1919 | 0.6007 | 0.5620 | 0.1556 | 14.8 | 18.4 |
| 2026-10-24 | 429 | 0.2191 | 0.6541 | 0.6057 | 0.1625 | 17.3 | 20.7 |
| 2026-10-25 *† | 35 | 0.0571 | 0.8636 | 0.7197 | 0.0551 | 7.6 | 9.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 103 | 0.6893 | 0.6554 | 0.5632 | 49.3 |
| < 30 min | 316 | 0.2152 | 0.7834 | 0.7340 | 13.9 |
| 30–120 min | 1016 | 0.1831 | 0.6578 | 0.6234 | 13.7 |
| 2–12 h | 1530 | 0.1359 | 0.6404 | 0.6325 | 11.7 |
| > 12 h * | 26 | 0.0769 | 0.8542 | 0.9896 | 6.1 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 627 | 0.068 | 0.053 |
| 0.1-0.2 | 929 | 0.148 | 0.155 |
| 0.2-0.3 | 748 | 0.249 | 0.198 |
| 0.3-0.4 | 470 | 0.340 | 0.260 |
| 0.4-0.5 | 142 | 0.442 | 0.359 |
| 0.5-0.6 | 55 | 0.545 | 0.455 |
| 0.6-0.7 * | 11 | 0.639 | 0.636 |
| 0.7-0.8 * | 7 | 0.736 | 0.571 |
| 0.8-0.9 * | 2 | 0.854 | 0.500 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-10-22 | VJC | PQC | 0.84 | 42.4 | 33 min |
| VJ 985 | 2026-10-24 | VJC | PQC | 0.79 | 43.9 | 22 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 877 | 2026-10-23 | VJC | SGN | 0.72 | 34.3 | 34 min |
| JX 236 | 2026-10-22 | SJX | TPE | 0.71 | 41.6 | 51 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (56%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| KE 2006 | 2026-10-18 | KAL | ICN | 0.04 | -0.2 | 145 min |
| CA 420 | 2026-10-19 | CCA | CKG | 0.04 | -2.9 | 131 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2991 | 0.6728 | 0.1402 | 0.4446 | 13.9 | 2026-10-17T16:01:07+00:00 | 2026-10-24T16:08:19+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2991}
