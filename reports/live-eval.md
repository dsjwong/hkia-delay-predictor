# Live evaluation — predictions vs actuals

Generated 2026-09-19T20:37:30+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2833**.

Dates 2026-09-13..2026-09-20; observed P(delay > 15) = 0.137; median lead time between last score and departure = 128.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.7045 | 0.1131 | 0.3745 | 11.479 |
| baseline_airline_hour | 0.6582 | 0.1364 | 0.4424 | 16.918 |
| naive_rate | 0.5 | 0.1182 | 0.3994 | 11.33 |

Coverage: **2833 of 2868** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2833 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0463 | [+0.0235, +0.0702] | **yes** |
| brier | -0.0233 | [-0.0267, -0.0200] | **yes** |
| logloss | -0.0679 | [-0.0773, -0.0587] | **yes** |
| mae | -5.44 | [-5.7633, -5.1317] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-13 † | 378 | 0.2063 | 0.7195 | 0.6886 | 0.1477 | 14.7 | 18.4 |
| 2026-09-14 | 402 | 0.1617 | 0.6549 | 0.6332 | 0.1327 | 14.9 | 19.4 |
| 2026-09-15 | 386 | 0.0855 | 0.6674 | 0.6061 | 0.0914 | 9.9 | 16.2 |
| 2026-09-16 | 389 | 0.1260 | 0.7551 | 0.6831 | 0.1005 | 9.6 | 15.9 |
| 2026-09-17 | 399 | 0.1203 | 0.7270 | 0.6686 | 0.1020 | 11.0 | 17.1 |
| 2026-09-18 | 418 | 0.1148 | 0.6810 | 0.6624 | 0.1007 | 8.8 | 14.6 |
| 2026-09-19 | 424 | 0.1486 | 0.6913 | 0.6467 | 0.1193 | 11.9 | 17.1 |
| 2026-09-20 *† | 37 | 0.1081 | 0.7879 | 0.7273 | 0.0917 | 8.4 | 13.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 109 | 0.6789 | 0.6255 | 0.6137 | 49.1 |
| < 30 min | 292 | 0.1473 | 0.7249 | 0.6022 | 9.9 |
| 30–120 min | 1019 | 0.1305 | 0.7021 | 0.6378 | 10.6 |
| 2–12 h | 1401 | 0.0985 | 0.6792 | 0.6595 | 9.6 |
| > 12 h * | 12 | 0.0000 | — | — | 4.9 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 788 | 0.063 | 0.046 |
| 0.1-0.2 | 1003 | 0.148 | 0.109 |
| 0.2-0.3 | 649 | 0.247 | 0.200 |
| 0.3-0.4 | 273 | 0.343 | 0.256 |
| 0.4-0.5 | 83 | 0.438 | 0.277 |
| 0.5-0.6 * | 26 | 0.546 | 0.538 |
| 0.6-0.7 * | 7 | 0.649 | 0.571 |
| 0.7-0.8 * | 3 | 0.739 | 0.333 |
| 0.8-0.9 * | 1 | 0.821 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-13 | SWR | ZRH | 0.82 | 31.8 | 34 min |
| RA 410 | 2026-09-19 | RNA | KTM | 0.78 | 52.8 | 55 min |
| CX 725 | 2026-09-14 | CPA | KUL | 0.68 | 27.4 | 290 min |
| VJ 877 | 2026-09-13 | VJC | SGN | 0.66 | 27.6 | 39 min |
| CX 852 | 2026-09-14 | CPA | SEA | 0.65 | 23.7 | 101 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (50%).

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
| 4a4212f@2026-08-25T09:35:34+00:00 | 2833 | 0.7045 | 0.1131 | 0.3745 | 11.5 | 2026-09-12T19:57:24+00:00 | 2026-09-19T17:34:24+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2833}
