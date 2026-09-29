# Live evaluation — predictions vs actuals

Generated 2026-09-29T22:13:11+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3047**.

Dates 2026-09-23..2026-09-30; observed P(delay > 15) = 0.1963; median lead time between last score and departure = 148.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6859 | 0.1462 | 0.4604 | 13.763 |
| baseline_airline_hour | 0.648 | 0.1567 | 0.4891 | 17.483 |
| naive_rate | 0.5 | 0.1577 | 0.4952 | 13.885 |

Coverage: **3047 of 3085** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3047 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0379 | [+0.0165, +0.0588] | **yes** |
| brier | -0.0105 | [-0.0135, -0.0074] | **yes** |
| logloss | -0.0287 | [-0.0379, -0.0196] | **yes** |
| mae | -3.72 | [-4.0128, -3.4144] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-23 † | 386 | 0.1451 | 0.5945 | 0.6654 | 0.1258 | 10.5 | 15.2 |
| 2026-09-24 | 429 | 0.1702 | 0.6566 | 0.6505 | 0.1362 | 12.3 | 16.8 |
| 2026-09-25 | 447 | 0.1790 | 0.7152 | 0.6696 | 0.1362 | 12.5 | 15.9 |
| 2026-09-26 | 436 | 0.2271 | 0.6941 | 0.6609 | 0.1595 | 13.6 | 17.2 |
| 2026-09-27 | 441 | 0.2336 | 0.6558 | 0.6288 | 0.1685 | 15.8 | 18.3 |
| 2026-09-28 | 438 | 0.1895 | 0.7088 | 0.6497 | 0.1411 | 15.2 | 19.3 |
| 2026-09-29 | 434 | 0.2258 | 0.7049 | 0.6335 | 0.1557 | 16.5 | 20.1 |
| 2026-09-30 *† | 36 | 0.1667 | 0.7361 | 0.6694 | 0.1204 | 7.7 | 10.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 124 | 0.7661 | 0.6682 | 0.5626 | 63.8 |
| < 30 min | 296 | 0.2061 | 0.6456 | 0.5895 | 13.8 |
| 30–120 min | 926 | 0.2192 | 0.7280 | 0.6666 | 12.2 |
| 2–12 h | 1675 | 0.1421 | 0.6584 | 0.6254 | 11.0 |
| > 12 h * | 26 | 0.0385 | 0.4400 | 0.7400 | 6.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 592 | 0.067 | 0.084 |
| 0.1-0.2 | 909 | 0.149 | 0.123 |
| 0.2-0.3 | 711 | 0.247 | 0.232 |
| 0.3-0.4 | 511 | 0.345 | 0.256 |
| 0.4-0.5 | 221 | 0.439 | 0.330 |
| 0.5-0.6 | 69 | 0.539 | 0.565 |
| 0.6-0.7 * | 22 | 0.640 | 0.864 |
| 0.7-0.8 * | 6 | 0.730 | 0.500 |
| 0.8-0.9 * | 6 | 0.835 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-27 | SWR | ZRH | 0.85 | 31.7 | 38 min |
| LX 139 | 2026-09-29 | SWR | ZRH | 0.85 | 33.3 | 23 min |
| VJ 985 | 2026-09-29 | VJC | PQC | 0.84 | 39.4 | 35 min |
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| VJ 985 | 2026-09-26 | VJC | PQC | 0.82 | 38.0 | 78 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 12 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| UO 670 | 2026-09-29 | HKE | NGO | 0.03 | -3.8 | 19 min |
| SQ 895 | 2026-09-29 | SIA | SIN | 0.03 | -0.3 | 28 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| OD 606 | 2026-09-28 | MXD | KUL | 0.72 | 64.2 | -7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3047 | 0.6859 | 0.1462 | 0.4604 | 13.8 | 2026-09-21T20:03:07+00:00 | 2026-09-29T13:10:30+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3047}
