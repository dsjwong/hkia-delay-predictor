# Live evaluation — predictions vs actuals

Generated 2026-09-13T20:47:35+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2801**.

Dates 2026-09-07..2026-09-14; observed P(delay > 15) = 0.1342; median lead time between last score and departure = 125.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.7074 | 0.1096 | 0.3668 | 10.902 |
| baseline_airline_hour | 0.6875 | 0.132 | 0.4325 | 16.497 |
| naive_rate | 0.5 | 0.1162 | 0.3944 | 10.619 |

Coverage: **2801 of 2838** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2801 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0199 | [-0.0056, +0.0467] | no — CI straddles 0 |
| brier | -0.0224 | [-0.0260, -0.0186] | **yes** |
| logloss | -0.0657 | [-0.0762, -0.0544] | **yes** |
| mae | -5.59 | [-5.9079, -5.2641] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-07 † | 363 | 0.0964 | 0.7240 | 0.7203 | 0.0909 | 10.2 | 17.2 |
| 2026-09-08 | 384 | 0.0885 | 0.6350 | 0.6201 | 0.0833 | 9.6 | 17.0 |
| 2026-09-09 | 384 | 0.1016 | 0.7097 | 0.7427 | 0.0860 | 10.6 | 17.8 |
| 2026-09-10 | 397 | 0.1537 | 0.6538 | 0.6665 | 0.1244 | 10.7 | 15.9 |
| 2026-09-11 | 416 | 0.1587 | 0.7125 | 0.6779 | 0.1227 | 10.0 | 14.4 |
| 2026-09-12 | 406 | 0.1429 | 0.7051 | 0.7068 | 0.1160 | 10.8 | 15.7 |
| 2026-09-13 | 413 | 0.1961 | 0.7214 | 0.7004 | 0.1430 | 14.5 | 18.1 |
| 2026-09-14 *† | 38 | 0.0526 | 0.7500 | 0.5417 | 0.0633 | 8.0 | 12.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 97 | 0.6804 | 0.6163 | 0.5826 | 49.1 |
| < 30 min | 303 | 0.1485 | 0.7550 | 0.6333 | 9.0 |
| 30–120 min | 996 | 0.1145 | 0.6975 | 0.6650 | 9.6 |
| 2–12 h | 1393 | 0.1084 | 0.7268 | 0.7374 | 9.6 |
| > 12 h * | 12 | 0.0000 | — | — | 6.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 880 | 0.063 | 0.050 |
| 0.1-0.2 | 1014 | 0.146 | 0.113 |
| 0.2-0.3 | 591 | 0.242 | 0.203 |
| 0.3-0.4 | 209 | 0.341 | 0.249 |
| 0.4-0.5 | 74 | 0.436 | 0.378 |
| 0.5-0.6 * | 25 | 0.532 | 0.480 |
| 0.6-0.7 * | 4 | 0.625 | 1.000 |
| 0.7-0.8 * | 3 | 0.716 | 0.000 |
| 0.8-0.9 * | 1 | 0.821 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-13 | SWR | ZRH | 0.82 | 31.8 | 34 min |
| VJ 877 | 2026-09-13 | VJC | SGN | 0.66 | 27.6 | 39 min |
| LX 139 | 2026-09-11 | SWR | ZRH | 0.63 | 23.9 | 61 min |
| LX 139 | 2026-09-09 | SWR | ZRH | 0.61 | 20.9 | 33 min |
| LX 139 | 2026-09-12 | SWR | ZRH | 0.60 | 24.7 | 38 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (25%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 700 | 2026-09-10 | HKE | BKK | 0.01 | -4.3 | 26 min |
| UO 670 | 2026-09-10 | HKE | NGO | 0.02 | -5.8 | 48 min |
| CX 334 | 2026-09-08 | CPA | PEK | 0.04 | -3.3 | 32 min |
| OD 606 | 2026-09-13 | MXD | KUL | 0.73 | 50.7 | -1 min |
| NH 812 | 2026-09-07 | ANA | NRT | 0.71 | 30.8 | -5 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2801 | 0.7074 | 0.1096 | 0.3668 | 10.9 | 2026-09-06T17:59:29+00:00 | 2026-09-13T16:31:21+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2801}
