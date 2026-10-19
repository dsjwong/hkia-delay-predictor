# Live evaluation — predictions vs actuals

Generated 2026-10-19T22:19:47+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3041**.

Dates 2026-10-13..2026-10-20; observed P(delay > 15) = 0.1338; median lead time between last score and departure = 140.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6945 | 0.1148 | 0.3801 | 11.449 |
| baseline_airline_hour | 0.6822 | 0.1317 | 0.4354 | 16.113 |
| naive_rate | 0.5 | 0.1159 | 0.3936 | 10.939 |

Coverage: **3041 of 3076** departures in the window (98.9%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3041 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0123 | [-0.0087, +0.0329] | no — CI straddles 0 |
| brier | -0.0169 | [-0.0200, -0.0137] | **yes** |
| logloss | -0.0553 | [-0.0681, -0.0438] | **yes** |
| mae | -4.66 | [-4.9428, -4.3985] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-13 † | 388 | 0.1443 | 0.7211 | 0.7252 | 0.1146 | 10.4 | 15.6 |
| 2026-10-14 | 420 | 0.1071 | 0.7107 | 0.7070 | 0.1055 | 10.2 | 15.1 |
| 2026-10-15 | 421 | 0.1116 | 0.7419 | 0.7044 | 0.0940 | 9.1 | 15.1 |
| 2026-10-16 | 448 | 0.1250 | 0.6116 | 0.6268 | 0.1205 | 12.3 | 15.9 |
| 2026-10-17 | 441 | 0.1678 | 0.7029 | 0.6981 | 0.1335 | 14.0 | 17.7 |
| 2026-10-18 | 439 | 0.1458 | 0.7372 | 0.7121 | 0.1197 | 12.6 | 16.7 |
| 2026-10-19 | 447 | 0.1365 | 0.6465 | 0.6142 | 0.1164 | 11.7 | 17.0 |
| 2026-10-20 *† | 37 | 0.1081 | 0.5455 | 0.6061 | 0.0903 | 6.6 | 11.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 85 | 0.6471 | 0.5897 | 0.6415 | 44.5 |
| < 30 min | 314 | 0.1497 | 0.7528 | 0.6632 | 13.0 |
| 30–120 min | 995 | 0.1357 | 0.7059 | 0.6790 | 10.0 |
| 2–12 h | 1612 | 0.1042 | 0.6798 | 0.6946 | 10.4 |
| > 12 h * | 35 | 0.0571 | 0.6970 | 0.8258 | 7.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 787 | 0.064 | 0.036 |
| 0.1-0.2 | 952 | 0.146 | 0.107 |
| 0.2-0.3 | 706 | 0.247 | 0.180 |
| 0.3-0.4 | 392 | 0.338 | 0.227 |
| 0.4-0.5 | 145 | 0.444 | 0.262 |
| 0.5-0.6 | 44 | 0.541 | 0.318 |
| 0.6-0.7 * | 10 | 0.640 | 0.500 |
| 0.7-0.8 * | 4 | 0.726 | 0.750 |
| 0.8-0.9 * | 1 | 0.870 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 985 | 2026-10-13 | VJC | PQC | 0.73 | 30.9 | 33 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |
| NH 812 | 2026-10-14 | ANA | NRT | 0.70 | 24.0 | 35 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 5 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (80%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-20 | KAL | ICN | 0.03 | -2.0 | 16 min |
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3041 | 0.6945 | 0.1148 | 0.3801 | 11.4 | 2026-10-11T19:03:44+00:00 | 2026-10-19T15:45:55+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3041}
