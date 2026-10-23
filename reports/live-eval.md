# Live evaluation — predictions vs actuals

Generated 2026-10-23T21:22:30+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3001**.

Dates 2026-10-17..2026-10-24; observed P(delay > 15) = 0.1723; median lead time between last score and departure = 132.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6771 | 0.1367 | 0.4356 | 13.314 |
| baseline_airline_hour | 0.6655 | 0.1473 | 0.4705 | 17.102 |
| naive_rate | 0.5 | 0.1426 | 0.4595 | 12.894 |

Coverage: **3001 of 3044** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3001 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0116 | [-0.0075, +0.0322] | no — CI straddles 0 |
| brier | -0.0106 | [-0.0138, -0.0077] | **yes** |
| logloss | -0.0349 | [-0.0485, -0.0243] | **yes** |
| mae | -3.79 | [-4.0831, -3.5063] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-17 † | 398 | 0.1709 | 0.6988 | 0.6931 | 0.1366 | 13.8 | 17.5 |
| 2026-10-18 | 439 | 0.1458 | 0.7372 | 0.7121 | 0.1197 | 12.6 | 16.7 |
| 2026-10-19 | 447 | 0.1365 | 0.6465 | 0.6142 | 0.1164 | 11.7 | 17.0 |
| 2026-10-20 | 431 | 0.1346 | 0.6420 | 0.7145 | 0.1215 | 11.9 | 15.6 |
| 2026-10-21 | 432 | 0.1505 | 0.7223 | 0.7706 | 0.1201 | 10.2 | 14.1 |
| 2026-10-22 | 420 | 0.2810 | 0.6632 | 0.6445 | 0.1913 | 19.0 | 21.1 |
| 2026-10-23 | 396 | 0.1919 | 0.6007 | 0.5620 | 0.1556 | 14.8 | 18.4 |
| 2026-10-24 *† | 38 | 0.1842 | 0.6406 | 0.6429 | 0.1334 | 9.2 | 12.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 112 | 0.6607 | 0.7038 | 0.6259 | 38.4 |
| < 30 min | 321 | 0.1994 | 0.7565 | 0.6904 | 13.9 |
| 30–120 min | 1038 | 0.1782 | 0.6522 | 0.6394 | 13.3 |
| 2–12 h | 1505 | 0.1276 | 0.6578 | 0.6611 | 11.5 |
| > 12 h * | 25 | 0.0800 | 0.8913 | 0.9891 | 6.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 637 | 0.068 | 0.050 |
| 0.1-0.2 | 906 | 0.147 | 0.143 |
| 0.2-0.3 | 742 | 0.249 | 0.190 |
| 0.3-0.4 | 479 | 0.341 | 0.261 |
| 0.4-0.5 | 162 | 0.444 | 0.321 |
| 0.5-0.6 | 54 | 0.542 | 0.426 |
| 0.6-0.7 * | 11 | 0.634 | 0.727 |
| 0.7-0.8 * | 8 | 0.724 | 0.500 |
| 0.8-0.9 * | 2 | 0.854 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| VJ 985 | 2026-10-22 | VJC | PQC | 0.84 | 42.4 | 33 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 877 | 2026-10-23 | VJC | SGN | 0.72 | 34.3 | 34 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 10 calls published at P ≥ 70%**, 6 were actually more than 15 minutes late (60%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| KE 2006 | 2026-10-18 | KAL | ICN | 0.04 | -0.2 | 145 min |
| CA 420 | 2026-10-19 | CCA | CKG | 0.04 | -2.9 | 131 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3001 | 0.6771 | 0.1367 | 0.4356 | 13.3 | 2026-10-16T21:32:04+00:00 | 2026-10-23T17:35:55+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3001}
