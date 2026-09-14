# Live evaluation — predictions vs actuals

Generated 2026-09-14T21:48:30+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2801**.

Dates 2026-09-08..2026-09-15; observed P(delay > 15) = 0.1453; median lead time between last score and departure = 125.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.698 | 0.1166 | 0.3853 | 11.646 |
| baseline_airline_hour | 0.6753 | 0.1367 | 0.4432 | 16.868 |
| naive_rate | 0.5 | 0.1242 | 0.4145 | 11.436 |

Coverage: **2801 of 2836** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2801 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0227 | [-0.0042, +0.0479] | no — CI straddles 0 |
| brier | -0.0201 | [-0.0238, -0.0160] | **yes** |
| logloss | -0.0579 | [-0.0687, -0.0464] | **yes** |
| mae | -5.22 | [-5.5519, -4.8884] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-08 † | 349 | 0.0946 | 0.6274 | 0.6057 | 0.0870 | 9.9 | 17.5 |
| 2026-09-09 | 384 | 0.1016 | 0.7097 | 0.7427 | 0.0860 | 10.6 | 17.8 |
| 2026-09-10 | 397 | 0.1537 | 0.6538 | 0.6665 | 0.1244 | 10.7 | 15.9 |
| 2026-09-11 | 416 | 0.1587 | 0.7125 | 0.6779 | 0.1227 | 10.0 | 14.4 |
| 2026-09-12 | 406 | 0.1429 | 0.7051 | 0.7068 | 0.1160 | 10.8 | 15.7 |
| 2026-09-13 | 413 | 0.1961 | 0.7214 | 0.7004 | 0.1430 | 14.5 | 18.1 |
| 2026-09-14 | 402 | 0.1617 | 0.6549 | 0.6332 | 0.1327 | 14.9 | 19.4 |
| 2026-09-15 *† | 34 | 0.1176 | 0.8250 | 0.8167 | 0.1008 | 10.4 | 11.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 108 | 0.7037 | 0.6102 | 0.5695 | 53.8 |
| < 30 min | 309 | 0.1456 | 0.7367 | 0.6206 | 9.8 |
| 30–120 min | 992 | 0.1240 | 0.6867 | 0.6464 | 10.1 |
| 2–12 h | 1381 | 0.1180 | 0.7107 | 0.7234 | 9.9 |
| > 12 h * | 11 | 0.0000 | — | — | 6.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 851 | 0.063 | 0.056 |
| 0.1-0.2 | 995 | 0.147 | 0.124 |
| 0.2-0.3 | 585 | 0.243 | 0.209 |
| 0.3-0.4 | 246 | 0.343 | 0.244 |
| 0.4-0.5 | 82 | 0.437 | 0.329 |
| 0.5-0.6 | 32 | 0.541 | 0.594 |
| 0.6-0.7 * | 7 | 0.633 | 1.000 |
| 0.7-0.8 * | 2 | 0.719 | 0.000 |
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

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 3 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (33%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 700 | 2026-09-10 | HKE | BKK | 0.01 | -4.3 | 26 min |
| UO 670 | 2026-09-10 | HKE | NGO | 0.02 | -5.8 | 48 min |
| CX 334 | 2026-09-08 | CPA | PEK | 0.04 | -3.3 | 32 min |
| OD 606 | 2026-09-13 | MXD | KUL | 0.73 | 50.7 | -1 min |
| VJ 985 | 2026-09-12 | VJC | PQC | 0.70 | 35.9 | 2 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2801 | 0.6980 | 0.1166 | 0.3853 | 11.6 | 2026-09-07T06:44:24+00:00 | 2026-09-14T13:28:26+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2801}
