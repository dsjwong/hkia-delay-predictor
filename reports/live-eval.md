# Live evaluation — predictions vs actuals

Generated 2026-09-28T23:15:01+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3024**.

Dates 2026-09-22..2026-09-29; observed P(delay > 15) = 0.1892; median lead time between last score and departure = 139.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6861 | 0.1425 | 0.4512 | 13.114 |
| baseline_airline_hour | 0.6559 | 0.1532 | 0.4808 | 17.013 |
| naive_rate | 0.5 | 0.1534 | 0.485 | 13.242 |

Coverage: **3024 of 3062** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3024 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0302 | [+0.0087, +0.0517] | **yes** |
| brier | -0.0107 | [-0.0141, -0.0077] | **yes** |
| logloss | -0.0296 | [-0.0396, -0.0206] | **yes** |
| mae | -3.90 | [-4.1921, -3.6028] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-22 † | 373 | 0.1903 | 0.7052 | 0.6602 | 0.1404 | 12.3 | 17.2 |
| 2026-09-23 | 424 | 0.1392 | 0.6118 | 0.6791 | 0.1197 | 10.3 | 14.9 |
| 2026-09-24 | 429 | 0.1702 | 0.6566 | 0.6505 | 0.1362 | 12.3 | 16.8 |
| 2026-09-25 | 447 | 0.1790 | 0.7152 | 0.6696 | 0.1362 | 12.5 | 15.9 |
| 2026-09-26 | 436 | 0.2271 | 0.6941 | 0.6609 | 0.1595 | 13.6 | 17.2 |
| 2026-09-27 | 441 | 0.2336 | 0.6558 | 0.6288 | 0.1685 | 15.8 | 18.3 |
| 2026-09-28 | 438 | 0.1895 | 0.7088 | 0.6497 | 0.1411 | 15.2 | 19.3 |
| 2026-09-29 *† | 36 | 0.1111 | 0.9297 | 0.7695 | 0.0797 | 7.0 | 10.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 124 | 0.7903 | 0.6397 | 0.5634 | 59.3 |
| < 30 min | 299 | 0.1806 | 0.6662 | 0.6449 | 13.4 |
| 30–120 min | 981 | 0.2049 | 0.7143 | 0.6482 | 11.4 |
| 2–12 h | 1598 | 0.1370 | 0.6586 | 0.6404 | 10.6 |
| > 12 h * | 22 | 0.0000 | — | — | 6.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 633 | 0.067 | 0.079 |
| 0.1-0.2 | 940 | 0.149 | 0.130 |
| 0.2-0.3 | 711 | 0.246 | 0.219 |
| 0.3-0.4 | 448 | 0.345 | 0.263 |
| 0.4-0.5 | 198 | 0.439 | 0.328 |
| 0.5-0.6 | 61 | 0.540 | 0.574 |
| 0.6-0.7 * | 24 | 0.641 | 0.833 |
| 0.7-0.8 * | 5 | 0.733 | 0.400 |
| 0.8-0.9 * | 4 | 0.830 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-27 | SWR | ZRH | 0.85 | 31.7 | 38 min |
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| VJ 985 | 2026-09-26 | VJC | PQC | 0.82 | 38.0 | 78 min |
| LX 139 | 2026-09-28 | SWR | ZRH | 0.81 | 28.1 | 47 min |
| VJ 877 | 2026-09-27 | VJC | SGN | 0.76 | 34.7 | 37 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 6 were actually more than 15 minutes late (67%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| CA 420 | 2026-09-23 | CCA | CKG | 0.04 | -3.5 | 18 min |
| CX 617 | 2026-09-22 | CPA | BKK | 0.04 | -0.4 | 22 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| OD 606 | 2026-09-28 | MXD | KUL | 0.72 | 64.2 | -7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3024 | 0.6861 | 0.1425 | 0.4512 | 13.1 | 2026-09-21T02:06:55+00:00 | 2026-09-28T14:15:56+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3024}
