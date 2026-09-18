# Live evaluation — predictions vs actuals

Generated 2026-09-18T20:53:19+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2809**.

Dates 2026-09-12..2026-09-19; observed P(delay > 15) = 0.1353; median lead time between last score and departure = 126.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.7053 | 0.1123 | 0.373 | 11.309 |
| baseline_airline_hour | 0.6665 | 0.1351 | 0.4394 | 16.694 |
| naive_rate | 0.5 | 0.117 | 0.3963 | 11.142 |

Coverage: **2809 of 2849** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2809 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0388 | [+0.0139, +0.0636] | **yes** |
| brier | -0.0228 | [-0.0261, -0.0195] | **yes** |
| logloss | -0.0664 | [-0.0758, -0.0568] | **yes** |
| mae | -5.38 | [-5.7000, -5.0758] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-12 † | 366 | 0.1475 | 0.6977 | 0.6893 | 0.1197 | 10.7 | 15.9 |
| 2026-09-13 | 413 | 0.1961 | 0.7214 | 0.7004 | 0.1430 | 14.5 | 18.1 |
| 2026-09-14 | 402 | 0.1617 | 0.6549 | 0.6332 | 0.1327 | 14.9 | 19.4 |
| 2026-09-15 | 386 | 0.0855 | 0.6674 | 0.6061 | 0.0914 | 9.9 | 16.2 |
| 2026-09-16 | 389 | 0.1260 | 0.7551 | 0.6831 | 0.1005 | 9.6 | 15.9 |
| 2026-09-17 | 399 | 0.1203 | 0.7270 | 0.6686 | 0.1020 | 11.0 | 17.1 |
| 2026-09-18 | 418 | 0.1148 | 0.6810 | 0.6624 | 0.1007 | 8.8 | 14.6 |
| 2026-09-19 *† | 36 | 0.0556 | 0.6912 | 0.6765 | 0.0593 | 7.8 | 11.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 107 | 0.6822 | 0.6180 | 0.6088 | 50.4 |
| < 30 min | 287 | 0.1463 | 0.7163 | 0.5921 | 9.5 |
| 30–120 min | 1021 | 0.1303 | 0.6942 | 0.6510 | 10.4 |
| 2–12 h | 1382 | 0.0955 | 0.7112 | 0.6948 | 9.4 |
| > 12 h * | 12 | 0.0000 | — | — | 4.9 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 779 | 0.063 | 0.047 |
| 0.1-0.2 | 975 | 0.148 | 0.102 |
| 0.2-0.3 | 648 | 0.247 | 0.201 |
| 0.3-0.4 | 280 | 0.343 | 0.246 |
| 0.4-0.5 | 85 | 0.437 | 0.259 |
| 0.5-0.6 | 32 | 0.541 | 0.531 |
| 0.6-0.7 * | 6 | 0.640 | 0.833 |
| 0.7-0.8 * | 3 | 0.715 | 0.000 |
| 0.8-0.9 * | 1 | 0.821 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-13 | SWR | ZRH | 0.82 | 31.8 | 34 min |
| CX 725 | 2026-09-14 | CPA | KUL | 0.68 | 27.4 | 290 min |
| VJ 877 | 2026-09-13 | VJC | SGN | 0.66 | 27.6 | 39 min |
| CX 852 | 2026-09-14 | CPA | SEA | 0.65 | 23.7 | 101 min |
| HB 320 | 2026-09-14 | HGB | NRT | 0.61 | 26.2 | 83 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (25%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-09-18 | JNA | CJU | 0.03 | -1.2 | 20 min |
| EK 381 | 2026-09-16 | UAE | DXB | 0.03 | -1.1 | 18 min |
| EK 385 | 2026-09-17 | UAE | BKK | 0.04 | 0.0 | 20 min |
| OD 606 | 2026-09-13 | MXD | KUL | 0.73 | 50.7 | -1 min |
| VJ 985 | 2026-09-15 | VJC | PQC | 0.71 | 30.3 | -6 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2809 | 0.7053 | 0.1123 | 0.3730 | 11.3 | 2026-09-11T17:24:36+00:00 | 2026-09-18T15:21:47+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2809}
