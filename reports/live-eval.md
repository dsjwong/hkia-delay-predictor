# Live evaluation — predictions vs actuals

Generated 2026-10-06T22:39:03+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3143**.

Dates 2026-09-30..2026-10-07; observed P(delay > 15) = 0.1775; median lead time between last score and departure = 177.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6603 | 0.1437 | 0.4531 | 13.487 |
| baseline_airline_hour | 0.6452 | 0.1516 | 0.4764 | 17.15 |
| naive_rate | 0.5 | 0.146 | 0.4676 | 12.952 |

Coverage: **3143 of 3183** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3143 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0151 | [-0.0080, +0.0381] | no — CI straddles 0 |
| brier | -0.0079 | [-0.0112, -0.0046] | **yes** |
| logloss | -0.0233 | [-0.0320, -0.0144] | **yes** |
| mae | -3.66 | [-3.9499, -3.3951] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-30 † | 412 | 0.1481 | 0.6075 | 0.6290 | 0.1332 | 12.9 | 17.3 |
| 2026-10-01 | 454 | 0.1740 | 0.6791 | 0.6630 | 0.1376 | 10.2 | 14.3 |
| 2026-10-02 | 454 | 0.2819 | 0.6236 | 0.6199 | 0.1973 | 13.6 | 15.9 |
| 2026-10-03 | 437 | 0.1831 | 0.6382 | 0.5936 | 0.1584 | 15.6 | 18.6 |
| 2026-10-04 | 448 | 0.1786 | 0.7096 | 0.6825 | 0.1381 | 13.6 | 17.2 |
| 2026-10-05 | 451 | 0.1086 | 0.6805 | 0.6774 | 0.1019 | 11.1 | 16.6 |
| 2026-10-06 | 449 | 0.1782 | 0.6253 | 0.6585 | 0.1469 | 18.0 | 20.8 |
| 2026-10-07 *† | 38 | 0.0263 | 0.9459 | 0.9730 | 0.0403 | 6.6 | 9.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 101 | 0.7624 | 0.5950 | 0.5024 | 57.6 |
| < 30 min | 236 | 0.2203 | 0.7235 | 0.6750 | 11.4 |
| 30–120 min | 827 | 0.1427 | 0.6867 | 0.6115 | 10.9 |
| 2–12 h | 1910 | 0.1597 | 0.6282 | 0.6409 | 12.7 |
| > 12 h * | 69 | 0.0870 | 0.7526 | 0.7037 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 582 | 0.066 | 0.053 |
| 0.1-0.2 | 959 | 0.148 | 0.149 |
| 0.2-0.3 | 733 | 0.249 | 0.203 |
| 0.3-0.4 | 485 | 0.347 | 0.221 |
| 0.4-0.5 | 255 | 0.438 | 0.275 |
| 0.5-0.6 | 88 | 0.545 | 0.352 |
| 0.6-0.7 | 30 | 0.639 | 0.600 |
| 0.7-0.8 * | 8 | 0.745 | 0.750 |
| 0.8-0.9 * | 3 | 0.833 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-03 | RNA | KTM | 0.85 | 63.2 | 598 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| VJ 985 | 2026-10-01 | VJC | PQC | 0.79 | 34.6 | 27 min |
| CX 302 | 2026-10-04 | CPA | PVG | 0.77 | 32.0 | 79 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 11 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (82%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| UO 622 | 2026-09-30 | HKE | HND | 0.02 | -4.3 | 59 min |
| NH 814 | 2026-10-01 | ANA | HND | 0.04 | -3.6 | 25 min |
| OD 606 | 2026-10-03 | MXD | KUL | 0.77 | 60.0 | 7 min |
| LX 139 | 2026-09-30 | SWR | ZRH | 0.72 | 23.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3143 | 0.6603 | 0.1437 | 0.4531 | 13.5 | 2026-09-29T00:43:39+00:00 | 2026-10-06T13:45:06+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3143}
