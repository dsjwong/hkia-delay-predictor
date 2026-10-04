# Live evaluation — predictions vs actuals

Generated 2026-10-04T21:21:35+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3119**.

Dates 2026-09-28..2026-10-05; observed P(delay > 15) = 0.1959; median lead time between last score and departure = 162.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6739 | 0.1507 | 0.4707 | 13.869 |
| baseline_airline_hour | 0.6392 | 0.1582 | 0.4922 | 17.384 |
| naive_rate | 0.5 | 0.1575 | 0.4947 | 13.826 |

Coverage: **3119 of 3159** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3119 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0347 | [+0.0122, +0.0554] | **yes** |
| brier | -0.0075 | [-0.0105, -0.0043] | **yes** |
| logloss | -0.0215 | [-0.0298, -0.0127] | **yes** |
| mae | -3.52 | [-3.7729, -3.2571] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-28 † | 398 | 0.1910 | 0.7107 | 0.6481 | 0.1421 | 15.6 | 19.9 |
| 2026-09-29 | 434 | 0.2258 | 0.7049 | 0.6335 | 0.1557 | 16.5 | 20.1 |
| 2026-09-30 | 452 | 0.1438 | 0.6223 | 0.6383 | 0.1286 | 12.5 | 16.8 |
| 2026-10-01 | 454 | 0.1740 | 0.6791 | 0.6630 | 0.1376 | 10.2 | 14.3 |
| 2026-10-02 | 454 | 0.2819 | 0.6236 | 0.6199 | 0.1973 | 13.6 | 15.9 |
| 2026-10-03 | 437 | 0.1831 | 0.6382 | 0.5936 | 0.1584 | 15.6 | 18.6 |
| 2026-10-04 | 448 | 0.1786 | 0.7096 | 0.6825 | 0.1381 | 13.6 | 17.2 |
| 2026-10-05 *† | 42 | 0.1190 | 0.7865 | 0.7027 | 0.1135 | 12.0 | 10.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 115 | 0.7739 | 0.6262 | 0.4589 | 63.9 |
| < 30 min | 261 | 0.2682 | 0.7144 | 0.6353 | 13.8 |
| 30–120 min | 859 | 0.1653 | 0.7268 | 0.6532 | 11.8 |
| 2–12 h | 1845 | 0.1669 | 0.6268 | 0.6229 | 11.9 |
| > 12 h * | 39 | 0.0513 | 0.8649 | 0.7973 | 6.9 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 497 | 0.069 | 0.068 |
| 0.1-0.2 | 893 | 0.147 | 0.133 |
| 0.2-0.3 | 687 | 0.249 | 0.223 |
| 0.3-0.4 | 582 | 0.347 | 0.229 |
| 0.4-0.5 | 309 | 0.438 | 0.304 |
| 0.5-0.6 | 101 | 0.543 | 0.436 |
| 0.6-0.7 | 34 | 0.636 | 0.618 |
| 0.7-0.8 * | 11 | 0.739 | 0.727 |
| 0.8-0.9 * | 5 | 0.835 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-29 | SWR | ZRH | 0.85 | 33.3 | 23 min |
| RA 410 | 2026-10-03 | RNA | KTM | 0.85 | 63.2 | 598 min |
| VJ 985 | 2026-09-29 | VJC | PQC | 0.84 | 39.4 | 35 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| LX 139 | 2026-09-28 | SWR | ZRH | 0.81 | 28.1 | 47 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 16 calls published at P ≥ 70%**, 13 were actually more than 15 minutes late (81%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-09-30 | HKE | HND | 0.02 | -4.3 | 59 min |
| UO 670 | 2026-09-29 | HKE | NGO | 0.03 | -3.8 | 19 min |
| SQ 895 | 2026-09-29 | SIA | SIN | 0.03 | -0.3 | 28 min |
| OD 606 | 2026-10-03 | MXD | KUL | 0.77 | 60.0 | 7 min |
| LX 139 | 2026-09-30 | SWR | ZRH | 0.72 | 23.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3119 | 0.6739 | 0.1507 | 0.4707 | 13.9 | 2026-09-27T19:23:35+00:00 | 2026-10-04T17:54:55+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3119}
