# Live evaluation — predictions vs actuals

Generated 2026-09-15T21:18:53+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2804**.

Dates 2026-09-09..2026-09-16; observed P(delay > 15) = 0.1441; median lead time between last score and departure = 125.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6935 | 0.1174 | 0.387 | 11.636 |
| baseline_airline_hour | 0.6735 | 0.137 | 0.4438 | 16.757 |
| naive_rate | 0.5 | 0.1233 | 0.4123 | 11.311 |

Coverage: **2804 of 2839** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2804 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0200 | [-0.0061, +0.0457] | no — CI straddles 0 |
| brier | -0.0196 | [-0.0233, -0.0160] | **yes** |
| logloss | -0.0568 | [-0.0676, -0.0459] | **yes** |
| mae | -5.12 | [-5.4630, -4.7943] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-09 † | 349 | 0.1032 | 0.7050 | 0.7480 | 0.0873 | 10.9 | 18.4 |
| 2026-09-10 | 397 | 0.1537 | 0.6538 | 0.6665 | 0.1244 | 10.7 | 15.9 |
| 2026-09-11 | 416 | 0.1587 | 0.7125 | 0.6779 | 0.1227 | 10.0 | 14.4 |
| 2026-09-12 | 406 | 0.1429 | 0.7051 | 0.7068 | 0.1160 | 10.8 | 15.7 |
| 2026-09-13 | 413 | 0.1961 | 0.7214 | 0.7004 | 0.1430 | 14.5 | 18.1 |
| 2026-09-14 | 402 | 0.1617 | 0.6549 | 0.6332 | 0.1327 | 14.9 | 19.4 |
| 2026-09-15 | 386 | 0.0855 | 0.6674 | 0.6061 | 0.0914 | 9.9 | 16.2 |
| 2026-09-16 *† | 35 | 0.1143 | 0.5081 | 0.6008 | 0.1047 | 7.2 | 10.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 108 | 0.6759 | 0.6160 | 0.5838 | 50.3 |
| < 30 min | 309 | 0.1424 | 0.6976 | 0.6008 | 10.0 |
| 30–120 min | 1006 | 0.1262 | 0.6885 | 0.6538 | 10.2 |
| 2–12 h | 1378 | 0.1161 | 0.7059 | 0.7241 | 10.0 |
| > 12 h * | 3 | 0.0000 | — | — | 4.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 813 | 0.062 | 0.052 |
| 0.1-0.2 | 981 | 0.147 | 0.125 |
| 0.2-0.3 | 612 | 0.244 | 0.206 |
| 0.3-0.4 | 266 | 0.343 | 0.229 |
| 0.4-0.5 | 91 | 0.438 | 0.297 |
| 0.5-0.6 * | 29 | 0.540 | 0.586 |
| 0.6-0.7 * | 8 | 0.635 | 0.875 |
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
| LX 139 | 2026-09-11 | SWR | ZRH | 0.63 | 23.9 | 61 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (25%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 700 | 2026-09-10 | HKE | BKK | 0.01 | -4.3 | 26 min |
| UO 670 | 2026-09-10 | HKE | NGO | 0.02 | -5.8 | 48 min |
| EK 381 | 2026-09-16 | UAE | DXB | 0.03 | -1.1 | 18 min |
| OD 606 | 2026-09-13 | MXD | KUL | 0.73 | 50.7 | -1 min |
| VJ 985 | 2026-09-15 | VJC | PQC | 0.71 | 30.3 | -6 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2804 | 0.6935 | 0.1174 | 0.3870 | 11.6 | 2026-09-08T21:57:30+00:00 | 2026-09-15T15:20:20+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2804}
