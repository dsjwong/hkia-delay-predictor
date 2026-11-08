# Live evaluation — predictions vs actuals

Generated 2026-11-08T22:00:15+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2842**.

Dates 2026-11-02..2026-11-09; observed P(delay > 15) = 0.1309; median lead time between last score and departure = 213.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6366 | 0.1112 | 0.3788 | 10.074 |
| baseline_airline_hour | 0.6044 | 0.1361 | 0.4456 | 15.634 |
| naive_rate | 0.5 | 0.1138 | 0.3881 | 9.992 |

Coverage: **2842 of 2881** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2842 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0322 | [+0.0049, +0.0565] | **yes** |
| brier | -0.0249 | [-0.0282, -0.0212] | **yes** |
| logloss | -0.0668 | [-0.0770, -0.0565] | **yes** |
| mae | -5.56 | [-5.8742, -5.2257] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-02 † | 367 | 0.1444 | 0.6592 | 0.6519 | 0.1146 | 10.6 | 16.2 |
| 2026-11-03 | 400 | 0.1450 | 0.5864 | 0.5885 | 0.1219 | 10.8 | 16.7 |
| 2026-11-04 | 395 | 0.1114 | 0.6438 | 0.6115 | 0.0980 | 8.9 | 15.4 |
| 2026-11-05 | 398 | 0.1332 | 0.5643 | 0.5821 | 0.1207 | 10.0 | 14.7 |
| 2026-11-06 | 418 | 0.1124 | 0.6627 | 0.6070 | 0.1003 | 8.6 | 14.4 |
| 2026-11-07 | 411 | 0.1241 | 0.6909 | 0.6096 | 0.1021 | 9.1 | 15.1 |
| 2026-11-08 | 413 | 0.1525 | 0.6713 | 0.5853 | 0.1249 | 12.9 | 17.5 |
| 2026-11-09 *† | 40 | 0.0750 | 0.5991 | 0.5360 | 0.0783 | 6.8 | 11.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 63 | 0.6667 | 0.5028 | 0.4943 | 46.2 |
| < 30 min | 186 | 0.1613 | 0.6596 | 0.6409 | 10.1 |
| 30–120 min | 613 | 0.1077 | 0.6703 | 0.6357 | 8.8 |
| 2–12 h | 1798 | 0.1207 | 0.6434 | 0.6003 | 9.5 |
| > 12 h | 182 | 0.0934 | 0.5820 | 0.5651 | 7.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 713 | 0.070 | 0.077 |
| 0.1-0.2 | 1166 | 0.148 | 0.114 |
| 0.2-0.3 | 715 | 0.240 | 0.145 |
| 0.3-0.4 | 188 | 0.338 | 0.266 |
| 0.4-0.5 | 40 | 0.444 | 0.400 |
| 0.5-0.6 * | 15 | 0.551 | 0.667 |
| 0.6-0.7 * | 4 | 0.643 | 0.750 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-02 | SWR | ZRH | 0.68 | 27.3 | 40 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| OD 606 | 2026-11-02 | MXD | KUL | 0.60 | 39.1 | 92 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| QR 817 | 2026-11-02 | QTR | DOH | 0.03 | 4.3 | 37 min |
| UO 676 | 2026-11-05 | HKE | CJU | 0.04 | -4.6 | 34 min |
| CA 110 | 2026-11-02 | CCA | PEK | 0.04 | -2.0 | 31 min |
| LX 139 | 2026-11-05 | SWR | ZRH | 0.62 | 23.1 | 9 min |
| VJ 877 | 2026-11-08 | VJC | SGN | 0.59 | 32.2 | 2 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 * | 2 | — | 0.0072 | 0.0858 | 8.7 | 2026-11-01T02:28:35+00:00 | 2026-11-01T09:29:58+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 2840 | 0.6363 | 0.1113 | 0.3790 | 10.1 | 2026-11-01T16:14:42+00:00 | 2026-11-08T15:25:50+00:00 |

`*` = thin (< 100 flights — AUC standard error is large, treat as noise). Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 2, 'f6ae66c@2026-11-01T10:28:21+00:00': 2840}
