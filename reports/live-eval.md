# Live evaluation — predictions vs actuals

Generated 2026-09-26T21:07:38+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2981**.

Dates 2026-09-20..2026-09-27; observed P(delay > 15) = 0.1654; median lead time between last score and departure = 135.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6735 | 0.1309 | 0.4244 | 11.866 |
| baseline_airline_hour | 0.6527 | 0.1457 | 0.4641 | 16.369 |
| naive_rate | 0.5 | 0.138 | 0.4485 | 11.897 |

Coverage: **2981 of 3019** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2981 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0208 | [-0.0011, +0.0436] | no — CI straddles 0 |
| brier | -0.0148 | [-0.0182, -0.0113] | **yes** |
| logloss | -0.0397 | [-0.0495, -0.0297] | **yes** |
| mae | -4.50 | [-4.8194, -4.1862] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-20 † | 386 | 0.1295 | 0.6696 | 0.6606 | 0.1114 | 12.1 | 17.6 |
| 2026-09-21 | 412 | 0.1311 | 0.5944 | 0.5875 | 0.1182 | 10.4 | 15.8 |
| 2026-09-22 | 410 | 0.1756 | 0.7213 | 0.6813 | 0.1305 | 11.7 | 16.7 |
| 2026-09-23 | 424 | 0.1392 | 0.6118 | 0.6791 | 0.1197 | 10.3 | 14.9 |
| 2026-09-24 | 429 | 0.1702 | 0.6566 | 0.6505 | 0.1362 | 12.3 | 16.8 |
| 2026-09-25 | 447 | 0.1790 | 0.7152 | 0.6696 | 0.1362 | 12.5 | 15.9 |
| 2026-09-26 | 436 | 0.2271 | 0.6941 | 0.6609 | 0.1595 | 13.6 | 17.2 |
| 2026-09-27 *† | 37 | 0.1622 | 0.5484 | 0.5108 | 0.1462 | 12.0 | 15.1 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 116 | 0.7672 | 0.6176 | 0.5633 | 53.5 |
| < 30 min | 313 | 0.1565 | 0.6477 | 0.6146 | 11.2 |
| 30–120 min | 987 | 0.1611 | 0.6711 | 0.6171 | 10.1 |
| 2–12 h | 1543 | 0.1270 | 0.6658 | 0.6431 | 10.1 |
| > 12 h * | 22 | 0.0000 | — | — | 6.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 733 | 0.065 | 0.079 |
| 0.1-0.2 | 1004 | 0.149 | 0.124 |
| 0.2-0.3 | 700 | 0.245 | 0.201 |
| 0.3-0.4 | 362 | 0.343 | 0.246 |
| 0.4-0.5 | 124 | 0.439 | 0.363 |
| 0.5-0.6 | 39 | 0.544 | 0.590 |
| 0.6-0.7 * | 15 | 0.639 | 0.733 |
| 0.7-0.8 * | 2 | 0.728 | 0.000 |
| 0.8-0.9 * | 2 | 0.827 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| VJ 985 | 2026-09-26 | VJC | PQC | 0.82 | 38.0 | 78 min |
| CX 520 | 2026-09-25 | CPA | NRT | 0.69 | 28.4 | 40 min |
| LX 139 | 2026-09-26 | SWR | ZRH | 0.68 | 21.2 | 79 min |
| VJ 877 | 2026-09-25 | VJC | SGN | 0.68 | 31.3 | 46 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| UO 604 | 2026-09-21 | HKE | PUS | 0.03 | -6.9 | 26 min |
| NH 814 | 2026-09-20 | ANA | HND | 0.04 | -4.3 | 149 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| OD 606 | 2026-09-26 | MXD | KUL | 0.70 | 60.1 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2981 | 0.6735 | 0.1309 | 0.4244 | 11.9 | 2026-09-19T19:43:23+00:00 | 2026-09-26T17:20:20+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2981}
