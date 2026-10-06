# Live evaluation — predictions vs actuals

Generated 2026-10-06T00:01:56+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3114**.

Dates 2026-09-29..2026-10-06; observed P(delay > 15) = 0.1859; median lead time between last score and departure = 171.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6716 | 0.1461 | 0.4594 | 13.224 |
| baseline_airline_hour | 0.6377 | 0.155 | 0.485 | 17.004 |
| naive_rate | 0.5 | 0.1514 | 0.4803 | 13.076 |

Coverage: **3114 of 3167** departures in the window (98.3%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3114 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0339 | [+0.0125, +0.0561] | **yes** |
| brier | -0.0089 | [-0.0121, -0.0057] | **yes** |
| logloss | -0.0256 | [-0.0343, -0.0170] | **yes** |
| mae | -3.78 | [-4.0597, -3.5040] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-29 † | 381 | 0.2441 | 0.6832 | 0.6027 | 0.1668 | 17.0 | 20.7 |
| 2026-09-30 | 452 | 0.1438 | 0.6223 | 0.6383 | 0.1286 | 12.5 | 16.8 |
| 2026-10-01 | 454 | 0.1740 | 0.6791 | 0.6630 | 0.1376 | 10.2 | 14.3 |
| 2026-10-02 | 454 | 0.2819 | 0.6236 | 0.6199 | 0.1973 | 13.6 | 15.9 |
| 2026-10-03 | 437 | 0.1831 | 0.6382 | 0.5936 | 0.1584 | 15.6 | 18.6 |
| 2026-10-04 | 448 | 0.1786 | 0.7096 | 0.6825 | 0.1381 | 13.6 | 17.2 |
| 2026-10-05 | 451 | 0.1086 | 0.6805 | 0.6774 | 0.1019 | 11.1 | 16.6 |
| 2026-10-06 *† | 37 | 0.1351 | 0.6406 | 0.7438 | 0.1151 | 8.3 | 11.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 107 | 0.7290 | 0.6512 | 0.4907 | 60.1 |
| < 30 min | 250 | 0.2480 | 0.7121 | 0.6413 | 11.9 |
| 30–120 min | 829 | 0.1580 | 0.7212 | 0.6551 | 11.1 |
| 2–12 h | 1866 | 0.1618 | 0.6284 | 0.6180 | 11.8 |
| > 12 h * | 62 | 0.0968 | 0.7932 | 0.7649 | 7.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 524 | 0.067 | 0.061 |
| 0.1-0.2 | 945 | 0.148 | 0.133 |
| 0.2-0.3 | 706 | 0.249 | 0.212 |
| 0.3-0.4 | 525 | 0.347 | 0.236 |
| 0.4-0.5 | 274 | 0.438 | 0.288 |
| 0.5-0.6 | 97 | 0.544 | 0.402 |
| 0.6-0.7 | 30 | 0.639 | 0.600 |
| 0.7-0.8 * | 9 | 0.741 | 0.778 |
| 0.8-0.9 * | 4 | 0.840 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-29 | SWR | ZRH | 0.85 | 33.3 | 23 min |
| RA 410 | 2026-10-03 | RNA | KTM | 0.85 | 63.2 | 598 min |
| VJ 985 | 2026-09-29 | VJC | PQC | 0.84 | 39.4 | 35 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| VJ 985 | 2026-10-01 | VJC | PQC | 0.79 | 34.6 | 27 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 13 calls published at P ≥ 70%**, 11 were actually more than 15 minutes late (85%).

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
| 4a4212f@2026-08-25T09:35:34+00:00 | 3114 | 0.6716 | 0.1461 | 0.4594 | 13.2 | 2026-09-28T20:38:51+00:00 | 2026-10-05T09:45:18+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3114}
