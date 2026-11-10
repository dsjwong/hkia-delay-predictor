# Live evaluation — predictions vs actuals

Generated 2026-11-10T01:29:57+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2766**.

Dates 2026-11-03..2026-11-10; observed P(delay > 15) = 0.132; median lead time between last score and departure = 211.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6392 | 0.1121 | 0.3795 | 10.117 |
| baseline_airline_hour | 0.6025 | 0.1371 | 0.4474 | 15.698 |
| naive_rate | 0.5 | 0.1145 | 0.3901 | 10.074 |

Coverage: **2766 of 2873** departures in the window (96.3%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2766 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0367 | [+0.0083, +0.0657] | **yes** |
| brier | -0.0250 | [-0.0286, -0.0214] | **yes** |
| logloss | -0.0679 | [-0.0783, -0.0572] | **yes** |
| mae | -5.58 | [-5.9106, -5.2591] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-03 † | 293 | 0.1638 | 0.5930 | 0.5974 | 0.1344 | 11.9 | 18.0 |
| 2026-11-04 | 395 | 0.1114 | 0.6438 | 0.6115 | 0.0980 | 8.9 | 15.4 |
| 2026-11-05 | 398 | 0.1332 | 0.5643 | 0.5821 | 0.1207 | 10.0 | 14.7 |
| 2026-11-06 | 418 | 0.1124 | 0.6627 | 0.6070 | 0.1003 | 8.6 | 14.4 |
| 2026-11-07 | 411 | 0.1241 | 0.6909 | 0.6096 | 0.1021 | 9.1 | 15.1 |
| 2026-11-08 | 413 | 0.1525 | 0.6713 | 0.5853 | 0.1249 | 12.9 | 17.5 |
| 2026-11-09 | 404 | 0.1287 | 0.7165 | 0.6587 | 0.1052 | 9.9 | 15.6 |
| 2026-11-10 *† | 34 | 0.2059 | 0.5397 | 0.4709 | 0.1731 | 10.4 | 13.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 63 | 0.7143 | 0.4673 | 0.4389 | 48.7 |
| < 30 min | 174 | 0.1494 | 0.7032 | 0.6948 | 9.9 |
| 30–120 min | 618 | 0.1214 | 0.6707 | 0.6379 | 9.1 |
| 2–12 h | 1746 | 0.1145 | 0.6419 | 0.5864 | 9.3 |
| > 12 h | 165 | 0.1152 | 0.6312 | 0.5849 | 7.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 721 | 0.070 | 0.074 |
| 0.1-0.2 | 1155 | 0.148 | 0.121 |
| 0.2-0.3 | 665 | 0.240 | 0.158 |
| 0.3-0.4 | 169 | 0.338 | 0.243 |
| 0.4-0.5 | 37 | 0.444 | 0.378 |
| 0.5-0.6 * | 15 | 0.551 | 0.600 |
| 0.6-0.7 * | 3 | 0.630 | 0.667 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| OD 606 | 2026-11-04 | MXD | KUL | 0.56 | 39.2 | 20 min |
| CX 506 | 2026-11-03 | CPA | KIX | 0.56 | 20.0 | 93 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 676 | 2026-11-05 | HKE | CJU | 0.04 | -4.6 | 34 min |
| AF 185 | 2026-11-03 | AFR | CDG | 0.04 | 3.0 | 31 min |
| UO 622 | 2026-11-03 | HKE | HND | 0.05 | -5.1 | 21 min |
| LX 139 | 2026-11-05 | SWR | ZRH | 0.62 | 23.1 | 9 min |
| VJ 877 | 2026-11-08 | VJC | SGN | 0.59 | 32.2 | 2 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2766 | 0.6392 | 0.1121 | 0.3795 | 10.1 | 2026-11-02T00:00:52+00:00 | 2026-11-09T10:32:40+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2766}
