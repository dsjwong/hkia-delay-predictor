# Live evaluation — predictions vs actuals

Generated 2026-09-24T21:30:05+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2940**.

Dates 2026-09-18..2026-09-25; observed P(delay > 15) = 0.1435; median lead time between last score and departure = 127.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6616 | 0.1189 | 0.3948 | 11.072 |
| baseline_airline_hour | 0.6527 | 0.1382 | 0.4466 | 16.204 |
| naive_rate | 0.5 | 0.1229 | 0.4113 | 11.079 |

Coverage: **2940 of 2977** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2940 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0089 | [-0.0132, +0.0305] | no — CI straddles 0 |
| brier | -0.0193 | [-0.0227, -0.0158] | **yes** |
| logloss | -0.0518 | [-0.0621, -0.0412] | **yes** |
| mae | -5.13 | [-5.4566, -4.8104] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-18 † | 382 | 0.1204 | 0.7012 | 0.6626 | 0.1024 | 9.1 | 15.2 |
| 2026-09-19 | 424 | 0.1486 | 0.6913 | 0.6467 | 0.1193 | 11.9 | 17.1 |
| 2026-09-20 | 423 | 0.1253 | 0.6765 | 0.6537 | 0.1082 | 11.8 | 17.2 |
| 2026-09-21 | 412 | 0.1311 | 0.5944 | 0.5875 | 0.1182 | 10.4 | 15.8 |
| 2026-09-22 | 410 | 0.1756 | 0.7213 | 0.6813 | 0.1305 | 11.7 | 16.7 |
| 2026-09-23 | 424 | 0.1392 | 0.6118 | 0.6791 | 0.1197 | 10.3 | 14.9 |
| 2026-09-24 | 429 | 0.1702 | 0.6566 | 0.6505 | 0.1362 | 12.3 | 16.8 |
| 2026-09-25 *† | 36 | 0.0556 | 0.5294 | 0.8529 | 0.0773 | 8.6 | 11.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 119 | 0.7227 | 0.5377 | 0.5160 | 49.5 |
| < 30 min | 324 | 0.1574 | 0.6983 | 0.6778 | 11.1 |
| 30–120 min | 1032 | 0.1240 | 0.6438 | 0.6166 | 9.1 |
| 2–12 h | 1449 | 0.1084 | 0.6405 | 0.6306 | 9.4 |
| > 12 h * | 16 | 0.0000 | — | — | 5.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 857 | 0.064 | 0.077 |
| 0.1-0.2 | 1036 | 0.148 | 0.114 |
| 0.2-0.3 | 692 | 0.244 | 0.197 |
| 0.3-0.4 | 255 | 0.339 | 0.231 |
| 0.4-0.5 | 63 | 0.439 | 0.365 |
| 0.5-0.6 * | 24 | 0.544 | 0.583 |
| 0.6-0.7 * | 10 | 0.629 | 0.400 |
| 0.7-0.8 * | 2 | 0.764 | 0.500 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| RA 410 | 2026-09-19 | RNA | KTM | 0.78 | 52.8 | 55 min |
| VJ 985 | 2026-09-22 | VJC | PQC | 0.65 | 29.8 | 40 min |
| NZ 080 | 2026-09-24 | ANZ | AKL | 0.61 | 23.8 | 19 min |
| CX 520 | 2026-09-20 | CPA | NRT | 0.60 | 25.4 | 62 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 3 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (67%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| UO 604 | 2026-09-21 | HKE | PUS | 0.03 | -6.9 | 26 min |
| NH 814 | 2026-09-20 | ANA | HND | 0.04 | -4.3 | 149 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| VJ 985 | 2026-09-19 | VJC | PQC | 0.70 | 34.0 | 0 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2940 | 0.6616 | 0.1189 | 0.3948 | 11.1 | 2026-09-17T17:49:24+00:00 | 2026-09-24T17:23:58+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2940}
