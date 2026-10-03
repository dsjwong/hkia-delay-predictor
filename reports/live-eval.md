# Live evaluation — predictions vs actuals

Generated 2026-10-03T21:12:53+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3110**.

Dates 2026-09-27..2026-10-04; observed P(delay > 15) = 0.2039; median lead time between last score and departure = 160.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6679 | 0.1549 | 0.481 | 13.945 |
| baseline_airline_hour | 0.6337 | 0.1618 | 0.5008 | 17.36 |
| naive_rate | 0.5 | 0.1623 | 0.5057 | 13.963 |

Coverage: **3110 of 3148** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3110 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0342 | [+0.0133, +0.0561] | **yes** |
| brier | -0.0069 | [-0.0101, -0.0040] | **yes** |
| logloss | -0.0198 | [-0.0286, -0.0114] | **yes** |
| mae | -3.42 | [-3.6761, -3.1538] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-27 † | 403 | 0.2432 | 0.6574 | 0.6288 | 0.1724 | 16.2 | 18.7 |
| 2026-09-28 | 438 | 0.1895 | 0.7088 | 0.6497 | 0.1411 | 15.2 | 19.3 |
| 2026-09-29 | 434 | 0.2258 | 0.7049 | 0.6335 | 0.1557 | 16.5 | 20.1 |
| 2026-09-30 | 452 | 0.1438 | 0.6223 | 0.6383 | 0.1286 | 12.5 | 16.8 |
| 2026-10-01 | 454 | 0.1740 | 0.6791 | 0.6630 | 0.1376 | 10.2 | 14.3 |
| 2026-10-02 | 454 | 0.2819 | 0.6236 | 0.6199 | 0.1973 | 13.6 | 15.9 |
| 2026-10-03 | 436 | 0.1812 | 0.6337 | 0.5884 | 0.1587 | 14.4 | 17.4 |
| 2026-10-04 *† | 39 | 0.1026 | 0.6714 | 0.8429 | 0.0876 | 6.8 | 10.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 106 | 0.7547 | 0.5490 | 0.3930 | 69.1 |
| < 30 min | 276 | 0.2645 | 0.6921 | 0.6197 | 13.7 |
| 30–120 min | 885 | 0.1955 | 0.7307 | 0.6657 | 12.1 |
| 2–12 h | 1803 | 0.1697 | 0.6251 | 0.6164 | 11.8 |
| > 12 h * | 40 | 0.0500 | 0.8816 | 0.7763 | 6.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 492 | 0.069 | 0.073 |
| 0.1-0.2 | 858 | 0.148 | 0.140 |
| 0.2-0.3 | 715 | 0.248 | 0.231 |
| 0.3-0.4 | 591 | 0.347 | 0.239 |
| 0.4-0.5 | 310 | 0.439 | 0.310 |
| 0.5-0.6 | 100 | 0.540 | 0.430 |
| 0.6-0.7 | 31 | 0.637 | 0.742 |
| 0.7-0.8 * | 8 | 0.743 | 0.625 |
| 0.8-0.9 * | 5 | 0.836 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-27 | SWR | ZRH | 0.85 | 31.7 | 38 min |
| LX 139 | 2026-09-29 | SWR | ZRH | 0.85 | 33.3 | 23 min |
| VJ 985 | 2026-09-29 | VJC | PQC | 0.84 | 39.4 | 35 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| LX 139 | 2026-09-28 | SWR | ZRH | 0.81 | 28.1 | 47 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 13 calls published at P ≥ 70%**, 10 were actually more than 15 minutes late (77%).

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
| 4a4212f@2026-08-25T09:35:34+00:00 | 3110 | 0.6679 | 0.1549 | 0.4810 | 13.9 | 2026-09-26T20:00:00+00:00 | 2026-10-03T16:50:41+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3110}
