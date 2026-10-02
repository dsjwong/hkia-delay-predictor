# Live evaluation — predictions vs actuals

Generated 2026-10-02T22:11:44+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3107**.

Dates 2026-09-26..2026-10-03; observed P(delay > 15) = 0.2098; median lead time between last score and departure = 163.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6784 | 0.1549 | 0.4805 | 13.909 |
| baseline_airline_hour | 0.64 | 0.1633 | 0.5041 | 17.388 |
| naive_rate | 0.5 | 0.1658 | 0.5138 | 14.143 |

Coverage: **3107 of 3148** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3107 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0384 | [+0.0180, +0.0577] | **yes** |
| brier | -0.0084 | [-0.0111, -0.0053] | **yes** |
| logloss | -0.0236 | [-0.0313, -0.0154] | **yes** |
| mae | -3.48 | [-3.7344, -3.2005] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-26 † | 395 | 0.2354 | 0.7028 | 0.6493 | 0.1617 | 14.0 | 17.6 |
| 2026-09-27 | 441 | 0.2336 | 0.6558 | 0.6288 | 0.1685 | 15.8 | 18.3 |
| 2026-09-28 | 438 | 0.1895 | 0.7088 | 0.6497 | 0.1411 | 15.2 | 19.3 |
| 2026-09-29 | 434 | 0.2258 | 0.7049 | 0.6335 | 0.1557 | 16.5 | 20.1 |
| 2026-09-30 | 452 | 0.1438 | 0.6223 | 0.6383 | 0.1286 | 12.5 | 16.8 |
| 2026-10-01 | 454 | 0.1740 | 0.6791 | 0.6630 | 0.1376 | 10.2 | 14.3 |
| 2026-10-02 | 454 | 0.2819 | 0.6236 | 0.6199 | 0.1973 | 13.6 | 15.9 |
| 2026-10-03 *† | 39 | 0.0769 | 0.6389 | 0.6111 | 0.0946 | 10.3 | 13.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 108 | 0.7778 | 0.6235 | 0.4970 | 67.7 |
| < 30 min | 267 | 0.2472 | 0.7172 | 0.6173 | 13.0 |
| 30–120 min | 856 | 0.2009 | 0.7344 | 0.6728 | 12.1 |
| 2–12 h | 1833 | 0.1789 | 0.6370 | 0.6219 | 11.9 |
| > 12 h * | 43 | 0.0465 | 0.8902 | 0.7744 | 7.1 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 499 | 0.069 | 0.072 |
| 0.1-0.2 | 896 | 0.148 | 0.140 |
| 0.2-0.3 | 720 | 0.249 | 0.244 |
| 0.3-0.4 | 581 | 0.346 | 0.251 |
| 0.4-0.5 | 290 | 0.439 | 0.331 |
| 0.5-0.6 | 82 | 0.540 | 0.512 |
| 0.6-0.7 * | 26 | 0.645 | 0.808 |
| 0.7-0.8 * | 8 | 0.736 | 0.625 |
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

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 13 calls published at P ≥ 70%**, 10 were actually more than 15 minutes late (77%).

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
| 4a4212f@2026-08-25T09:35:34+00:00 | 3107 | 0.6784 | 0.1549 | 0.4805 | 13.9 | 2026-09-25T13:20:57+00:00 | 2026-10-02T13:59:24+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3107}
