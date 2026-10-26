# Live evaluation — predictions vs actuals

Generated 2026-10-26T22:38:38+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2977**.

Dates 2026-10-20..2026-10-27; observed P(delay > 15) = 0.1874; median lead time between last score and departure = 140.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6589 | 0.1457 | 0.4599 | 14.282 |
| baseline_airline_hour | 0.6412 | 0.1557 | 0.4909 | 17.968 |
| naive_rate | 0.5 | 0.1523 | 0.4825 | 14.066 |

Coverage: **2977 of 3015** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2977 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0177 | [-0.0033, +0.0380] | no — CI straddles 0 |
| brier | -0.0100 | [-0.0132, -0.0069] | **yes** |
| logloss | -0.0310 | [-0.0425, -0.0203] | **yes** |
| mae | -3.69 | [-3.9862, -3.3838] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-20 † | 394 | 0.1472 | 0.6221 | 0.6928 | 0.1306 | 12.4 | 15.9 |
| 2026-10-21 | 432 | 0.1505 | 0.7223 | 0.7706 | 0.1201 | 10.2 | 14.1 |
| 2026-10-22 | 420 | 0.2810 | 0.6632 | 0.6445 | 0.1913 | 19.0 | 21.1 |
| 2026-10-23 | 396 | 0.1919 | 0.6007 | 0.5620 | 0.1556 | 14.8 | 18.4 |
| 2026-10-24 | 429 | 0.2191 | 0.6541 | 0.6057 | 0.1625 | 17.3 | 20.7 |
| 2026-10-25 | 439 | 0.1868 | 0.6740 | 0.6543 | 0.1432 | 15.4 | 19.2 |
| 2026-10-26 | 430 | 0.1419 | 0.6094 | 0.6095 | 0.1206 | 11.3 | 16.8 |
| 2026-10-27 *† | 37 | 0.1081 | 0.3939 | 0.4015 | 0.1075 | 10.0 | 11.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 110 | 0.6909 | 0.6443 | 0.5695 | 56.8 |
| < 30 min | 309 | 0.1909 | 0.7693 | 0.7490 | 13.5 |
| 30–120 min | 988 | 0.1923 | 0.6482 | 0.6040 | 14.2 |
| 2–12 h | 1543 | 0.1491 | 0.6278 | 0.6198 | 11.6 |
| > 12 h * | 27 | 0.1111 | 0.6806 | 0.7778 | 8.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 610 | 0.069 | 0.069 |
| 0.1-0.2 | 948 | 0.148 | 0.165 |
| 0.2-0.3 | 784 | 0.248 | 0.204 |
| 0.3-0.4 | 436 | 0.341 | 0.266 |
| 0.4-0.5 | 132 | 0.441 | 0.379 |
| 0.5-0.6 | 47 | 0.543 | 0.468 |
| 0.6-0.7 * | 12 | 0.643 | 0.667 |
| 0.7-0.8 * | 6 | 0.735 | 0.500 |
| 0.8-0.9 * | 2 | 0.854 | 0.500 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-10-22 | VJC | PQC | 0.84 | 42.4 | 33 min |
| VJ 985 | 2026-10-24 | VJC | PQC | 0.79 | 43.9 | 22 min |
| VJ 877 | 2026-10-23 | VJC | SGN | 0.72 | 34.3 | 34 min |
| JX 236 | 2026-10-22 | SJX | TPE | 0.71 | 41.6 | 51 min |
| VJ 877 | 2026-10-25 | VJC | SGN | 0.68 | 26.8 | 85 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 8 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| EK 381 | 2026-10-26 | UAE | DXB | 0.04 | -1.7 | 19 min |
| EK 385 | 2026-10-26 | UAE | BKK | 0.04 | 2.6 | 47 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2977 | 0.6589 | 0.1457 | 0.4599 | 14.3 | 2026-10-18T23:57:58+00:00 | 2026-10-26T13:42:00+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2977}
