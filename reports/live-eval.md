# Live evaluation — predictions vs actuals

Generated 2026-11-27T01:42:06+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2864**.

Dates 2026-11-20..2026-11-27; observed P(delay > 15) = 0.1721; median lead time between last score and departure = 217.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6398 | 0.1424 | 0.4526 | 12.504 |
| baseline_airline_hour | 0.6021 | 0.1515 | 0.4795 | 15.082 |
| naive_rate | 0.5 | 0.1425 | 0.4593 | 11.168 |

Coverage: **2864 of 2978** departures in the window (96.2%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2864 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0377 | [+0.0108, +0.0639] | **yes** |
| brier | -0.0091 | [-0.0124, -0.0058] | **yes** |
| logloss | -0.0269 | [-0.0357, -0.0176] | **yes** |
| mae | -2.58 | [-2.8154, -2.3329] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-20 † | 310 | 0.2871 | 0.5638 | 0.5205 | 0.2074 | 15.8 | 16.8 |
| 2026-11-21 | 430 | 0.1605 | 0.5796 | 0.5807 | 0.1561 | 13.0 | 15.2 |
| 2026-11-22 | 427 | 0.1358 | 0.6490 | 0.5757 | 0.1155 | 10.5 | 14.7 |
| 2026-11-23 | 425 | 0.1412 | 0.6263 | 0.6116 | 0.1223 | 11.1 | 15.6 |
| 2026-11-24 | 404 | 0.1634 | 0.6589 | 0.5917 | 0.1365 | 12.9 | 15.2 |
| 2026-11-25 | 411 | 0.1411 | 0.7359 | 0.6809 | 0.1116 | 9.6 | 13.4 |
| 2026-11-26 | 410 | 0.2220 | 0.5964 | 0.6257 | 0.1740 | 15.8 | 15.6 |
| 2026-11-27 *† | 47 | 0.0426 | 0.5333 | 0.4000 | 0.0603 | 9.2 | 10.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 48 | 0.7292 | 0.6220 | 0.6165 | 47.2 |
| < 30 min | 164 | 0.1951 | 0.6561 | 0.5794 | 13.1 |
| 30–120 min | 581 | 0.1790 | 0.6650 | 0.5984 | 11.5 |
| 2–12 h | 1987 | 0.1560 | 0.6260 | 0.5995 | 12.1 |
| > 12 h * | 84 | 0.1429 | 0.7593 | 0.6233 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 487 | 0.068 | 0.074 |
| 0.1-0.2 | 878 | 0.152 | 0.145 |
| 0.2-0.3 | 797 | 0.247 | 0.181 |
| 0.3-0.4 | 437 | 0.344 | 0.224 |
| 0.4-0.5 | 184 | 0.436 | 0.299 |
| 0.5-0.6 | 54 | 0.541 | 0.370 |
| 0.6-0.7 * | 20 | 0.633 | 0.400 |
| 0.7-0.8 * | 4 | 0.732 | 1.000 |
| 0.8-0.9 * | 2 | 0.828 | 0.500 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-11-26 | VJC | PQC | 0.80 | 44.7 | 101 min |
| QF 128 | 2026-11-26 | QFA | SYD | 0.75 | 32.4 | 26 min |
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| VJ 877 | 2026-11-26 | VJC | SGN | 0.73 | 42.6 | 19 min |
| JX 236 | 2026-11-26 | SJX | TPE | 0.70 | 28.3 | 22 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 7 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (71%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 794 | 2026-11-23 | CCA | HGH | 0.04 | 3.9 | 27 min |
| GA 873 | 2026-11-25 | GIA | CGK | 0.04 | 3.7 | 18 min |
| CA 412 | 2026-11-24 | CCA | TFU | 0.04 | 2.6 | 23 min |
| RA 410 | 2026-11-21 | RNA | KTM | 0.91 | 54.4 | 12 min |
| RA 410 | 2026-11-25 | RNA | KTM | 0.85 | 50.9 | -7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| e2c2178@2026-11-22T11:25:36+00:00 | 1657 | 0.6483 | 0.1359 | 0.4355 | 12.4 | 2026-11-22T17:57:19+00:00 | 2026-11-26T15:31:37+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 1207 | 0.6318 | 0.1514 | 0.4760 | 12.6 | 2026-11-19T17:28:55+00:00 | 2026-11-22T10:28:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'e2c2178@2026-11-22T11:25:36+00:00': 1657, 'f6ae66c@2026-11-01T10:28:21+00:00': 1207}
