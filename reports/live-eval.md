# Live evaluation — predictions vs actuals

Generated 2026-10-01T22:39:34+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3104**.

Dates 2026-09-25..2026-10-02; observed P(delay > 15) = 0.1978; median lead time between last score and departure = 157.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6869 | 0.1476 | 0.4633 | 13.738 |
| baseline_airline_hour | 0.6472 | 0.1578 | 0.4918 | 17.35 |
| naive_rate | 0.5 | 0.1587 | 0.4974 | 13.859 |

Coverage: **3104 of 3140** departures in the window (98.9%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3104 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0397 | [+0.0195, +0.0602] | **yes** |
| brier | -0.0102 | [-0.0132, -0.0073] | **yes** |
| logloss | -0.0285 | [-0.0369, -0.0203] | **yes** |
| mae | -3.61 | [-3.8871, -3.3264] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-25 † | 411 | 0.1898 | 0.7145 | 0.6586 | 0.1414 | 12.8 | 16.2 |
| 2026-09-26 | 436 | 0.2271 | 0.6941 | 0.6609 | 0.1595 | 13.6 | 17.2 |
| 2026-09-27 | 441 | 0.2336 | 0.6558 | 0.6288 | 0.1685 | 15.8 | 18.3 |
| 2026-09-28 | 438 | 0.1895 | 0.7088 | 0.6497 | 0.1411 | 15.2 | 19.3 |
| 2026-09-29 | 434 | 0.2258 | 0.7049 | 0.6335 | 0.1557 | 16.5 | 20.1 |
| 2026-09-30 | 452 | 0.1438 | 0.6223 | 0.6383 | 0.1286 | 12.5 | 16.8 |
| 2026-10-01 | 454 | 0.1740 | 0.6791 | 0.6630 | 0.1376 | 10.2 | 14.3 |
| 2026-10-02 *† | 38 | 0.2368 | 0.7471 | 0.8027 | 0.1628 | 9.2 | 10.1 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 107 | 0.7757 | 0.7013 | 0.5906 | 68.5 |
| < 30 min | 276 | 0.2029 | 0.6960 | 0.5881 | 12.7 |
| 30–120 min | 913 | 0.2092 | 0.7438 | 0.6669 | 12.0 |
| 2–12 h | 1769 | 0.1594 | 0.6371 | 0.6319 | 11.6 |
| > 12 h * | 39 | 0.0513 | 0.8514 | 0.7230 | 7.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 531 | 0.068 | 0.075 |
| 0.1-0.2 | 928 | 0.148 | 0.127 |
| 0.2-0.3 | 683 | 0.249 | 0.223 |
| 0.3-0.4 | 587 | 0.346 | 0.247 |
| 0.4-0.5 | 264 | 0.439 | 0.330 |
| 0.5-0.6 | 76 | 0.541 | 0.566 |
| 0.6-0.7 * | 23 | 0.648 | 0.870 |
| 0.7-0.8 * | 7 | 0.735 | 0.571 |
| 0.8-0.9 * | 5 | 0.836 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-27 | SWR | ZRH | 0.85 | 31.7 | 38 min |
| LX 139 | 2026-09-29 | SWR | ZRH | 0.85 | 33.3 | 23 min |
| VJ 985 | 2026-09-29 | VJC | PQC | 0.84 | 39.4 | 35 min |
| VJ 985 | 2026-09-26 | VJC | PQC | 0.82 | 38.0 | 78 min |
| LX 139 | 2026-09-28 | SWR | ZRH | 0.81 | 28.1 | 47 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 12 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-09-30 | HKE | HND | 0.02 | -4.3 | 59 min |
| UO 670 | 2026-09-29 | HKE | NGO | 0.03 | -3.8 | 19 min |
| SQ 895 | 2026-09-29 | SIA | SIN | 0.03 | -0.3 | 28 min |
| LX 139 | 2026-09-30 | SWR | ZRH | 0.72 | 23.4 | 15 min |
| OD 606 | 2026-09-28 | MXD | KUL | 0.72 | 64.2 | -7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3104 | 0.6869 | 0.1476 | 0.4633 | 13.7 | 2026-09-24T17:23:58+00:00 | 2026-10-01T16:34:59+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3104}
