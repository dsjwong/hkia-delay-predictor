# Live evaluation — predictions vs actuals

Generated 2026-10-21T21:40:06+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3058**.

Dates 2026-10-15..2026-10-22; observed P(delay > 15) = 0.1406; median lead time between last score and departure = 130.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6826 | 0.1193 | 0.3922 | 11.736 |
| baseline_airline_hour | 0.6872 | 0.1336 | 0.439 | 16.036 |
| naive_rate | 0.5 | 0.1208 | 0.4061 | 11.136 |

Coverage: **3058 of 3096** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3058 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | -0.0046 | [-0.0245, +0.0149] | no — CI straddles 0 |
| brier | -0.0143 | [-0.0176, -0.0112] | **yes** |
| logloss | -0.0468 | [-0.0605, -0.0354] | **yes** |
| mae | -4.30 | [-4.5762, -4.0162] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-15 † | 383 | 0.1123 | 0.7302 | 0.6948 | 0.0958 | 9.3 | 15.4 |
| 2026-10-16 | 448 | 0.1250 | 0.6116 | 0.6268 | 0.1205 | 12.3 | 15.9 |
| 2026-10-17 | 441 | 0.1678 | 0.7029 | 0.6981 | 0.1335 | 14.0 | 17.7 |
| 2026-10-18 | 439 | 0.1458 | 0.7372 | 0.7121 | 0.1197 | 12.6 | 16.7 |
| 2026-10-19 | 447 | 0.1365 | 0.6465 | 0.6142 | 0.1164 | 11.7 | 17.0 |
| 2026-10-20 | 431 | 0.1346 | 0.6420 | 0.7145 | 0.1215 | 11.9 | 15.6 |
| 2026-10-21 | 432 | 0.1505 | 0.7223 | 0.7706 | 0.1201 | 10.2 | 14.1 |
| 2026-10-22 *† | 37 | 0.2432 | 0.7817 | 0.6746 | 0.1756 | 10.9 | 12.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 93 | 0.6344 | 0.6451 | 0.6493 | 44.9 |
| < 30 min | 328 | 0.1524 | 0.7327 | 0.6619 | 12.9 |
| 30–120 min | 1071 | 0.1466 | 0.6649 | 0.6639 | 10.6 |
| 2–12 h | 1537 | 0.1054 | 0.6896 | 0.7211 | 10.4 |
| > 12 h * | 29 | 0.0690 | 0.9444 | 0.9722 | 6.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 776 | 0.065 | 0.046 |
| 0.1-0.2 | 985 | 0.146 | 0.116 |
| 0.2-0.3 | 684 | 0.247 | 0.177 |
| 0.3-0.4 | 405 | 0.341 | 0.235 |
| 0.4-0.5 | 149 | 0.444 | 0.275 |
| 0.5-0.6 | 47 | 0.540 | 0.298 |
| 0.6-0.7 * | 8 | 0.634 | 0.750 |
| 0.7-0.8 * | 3 | 0.724 | 0.667 |
| 0.8-0.9 * | 1 | 0.870 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |
| LX 139 | 2026-10-17 | SWR | ZRH | 0.68 | 21.5 | 32 min |
| NH 812 | 2026-10-21 | ANA | NRT | 0.64 | 24.7 | 46 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| KE 2006 | 2026-10-18 | KAL | ICN | 0.04 | -0.2 | 145 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3058 | 0.6826 | 0.1193 | 0.3922 | 11.7 | 2026-10-13T21:38:41+00:00 | 2026-10-21T15:29:08+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3058}
