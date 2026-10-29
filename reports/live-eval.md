# Live evaluation — predictions vs actuals

Generated 2026-10-29T22:43:31+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2946**.

Dates 2026-10-23..2026-10-30; observed P(delay > 15) = 0.1612; median lead time between last score and departure = 162.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6542 | 0.1302 | 0.4235 | 12.867 |
| baseline_airline_hour | 0.6315 | 0.1468 | 0.4721 | 17.889 |
| naive_rate | 0.5 | 0.1352 | 0.4417 | 12.896 |

Coverage: **2946 of 2984** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2946 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0227 | [-0.0021, +0.0477] | no — CI straddles 0 |
| brier | -0.0166 | [-0.0204, -0.0130] | **yes** |
| logloss | -0.0486 | [-0.0621, -0.0363] | **yes** |
| mae | -5.02 | [-5.3520, -4.6707] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-23 † | 359 | 0.1727 | 0.6335 | 0.5958 | 0.1438 | 14.6 | 18.6 |
| 2026-10-24 | 429 | 0.2191 | 0.6541 | 0.6088 | 0.1625 | 17.3 | 20.6 |
| 2026-10-25 | 439 | 0.1868 | 0.6740 | 0.6673 | 0.1432 | 15.4 | 19.2 |
| 2026-10-26 | 430 | 0.1419 | 0.6094 | 0.6251 | 0.1206 | 11.3 | 16.6 |
| 2026-10-27 | 419 | 0.1527 | 0.6685 | 0.6110 | 0.1243 | 9.6 | 15.5 |
| 2026-10-28 | 420 | 0.1119 | 0.6963 | 0.6810 | 0.0947 | 10.8 | 17.9 |
| 2026-10-29 | 414 | 0.1498 | 0.5928 | 0.6339 | 0.1273 | 11.7 | 17.2 |
| 2026-10-30 *† | 36 | 0.0833 | 0.6364 | 0.7525 | 0.0774 | 6.4 | 11.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 79 | 0.6456 | 0.5728 | 0.4751 | 68.7 |
| < 30 min | 261 | 0.1303 | 0.7827 | 0.7190 | 11.4 |
| 30–120 min | 858 | 0.1667 | 0.6801 | 0.6291 | 11.8 |
| 2–12 h | 1696 | 0.1439 | 0.6143 | 0.6156 | 11.2 |
| > 12 h * | 52 | 0.0577 | 0.5918 | 0.4762 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 764 | 0.067 | 0.073 |
| 0.1-0.2 | 1121 | 0.148 | 0.148 |
| 0.2-0.3 | 677 | 0.243 | 0.198 |
| 0.3-0.4 | 274 | 0.338 | 0.255 |
| 0.4-0.5 | 79 | 0.439 | 0.418 |
| 0.5-0.6 * | 20 | 0.538 | 0.600 |
| 0.6-0.7 * | 7 | 0.660 | 0.286 |
| 0.7-0.8 * | 3 | 0.741 | 0.667 |
| 0.8-0.9 * | 1 | 0.871 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-10-24 | VJC | PQC | 0.79 | 43.9 | 22 min |
| VJ 877 | 2026-10-23 | VJC | SGN | 0.72 | 34.3 | 34 min |
| VJ 877 | 2026-10-25 | VJC | SGN | 0.68 | 26.8 | 85 min |
| JX 236 | 2026-10-24 | SJX | TPE | 0.67 | 35.2 | 43 min |
| VJ 877 | 2026-10-26 | VJC | SGN | 0.59 | 23.0 | 78 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-29 | KAL | ICN | 0.02 | -3.7 | 41 min |
| QR 817 | 2026-10-29 | QTR | DOH | 0.03 | 3.0 | 19 min |
| CA 118 | 2026-10-27 | CCA | PEK | 0.03 | -2.9 | 19 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| OD 606 | 2026-10-23 | MXD | KUL | 0.72 | 76.1 | 14 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2946 | 0.6542 | 0.1302 | 0.4235 | 12.9 | 2026-10-22T17:24:17+00:00 | 2026-10-29T13:25:39+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2946}
