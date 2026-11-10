# Live evaluation — predictions vs actuals

Generated 2026-11-10T23:17:02+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2825**.

Dates 2026-11-04..2026-11-11; observed P(delay > 15) = 0.132; median lead time between last score and departure = 211.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6751 | 0.1101 | 0.3718 | 10.149 |
| baseline_airline_hour | 0.6206 | 0.1356 | 0.4429 | 15.586 |
| naive_rate | 0.5 | 0.1146 | 0.3902 | 10.055 |

Coverage: **2825 of 2861** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2825 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0545 | [+0.0260, +0.0821] | **yes** |
| brier | -0.0255 | [-0.0290, -0.0220] | **yes** |
| logloss | -0.0711 | [-0.0810, -0.0614] | **yes** |
| mae | -5.44 | [-5.7469, -5.1248] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-04 † | 359 | 0.1031 | 0.6818 | 0.6639 | 0.0914 | 8.8 | 15.8 |
| 2026-11-05 | 398 | 0.1332 | 0.5643 | 0.5821 | 0.1207 | 10.0 | 14.7 |
| 2026-11-06 | 418 | 0.1124 | 0.6627 | 0.6070 | 0.1003 | 8.6 | 14.4 |
| 2026-11-07 | 411 | 0.1241 | 0.6909 | 0.6096 | 0.1021 | 9.1 | 15.1 |
| 2026-11-08 | 413 | 0.1525 | 0.6713 | 0.5853 | 0.1249 | 12.9 | 17.5 |
| 2026-11-09 | 404 | 0.1287 | 0.7165 | 0.6587 | 0.1052 | 9.9 | 15.6 |
| 2026-11-10 | 391 | 0.1714 | 0.7526 | 0.6521 | 0.1272 | 11.7 | 16.1 |
| 2026-11-11 *† | 31 | 0.0968 | 0.8571 | 0.6964 | 0.0783 | 10.4 | 14.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 64 | 0.6875 | 0.5676 | 0.5028 | 48.6 |
| < 30 min | 175 | 0.1429 | 0.7037 | 0.6777 | 9.5 |
| 30–120 min | 621 | 0.1240 | 0.7024 | 0.6364 | 8.6 |
| 2–12 h | 1814 | 0.1174 | 0.6730 | 0.6017 | 9.6 |
| > 12 h | 151 | 0.0927 | 0.7534 | 0.6681 | 7.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 718 | 0.070 | 0.060 |
| 0.1-0.2 | 1168 | 0.148 | 0.113 |
| 0.2-0.3 | 685 | 0.242 | 0.166 |
| 0.3-0.4 | 197 | 0.337 | 0.294 |
| 0.4-0.5 | 37 | 0.445 | 0.378 |
| 0.5-0.6 * | 14 | 0.549 | 0.643 |
| 0.6-0.7 * | 5 | 0.629 | 0.400 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| OD 606 | 2026-11-04 | MXD | KUL | 0.56 | 39.2 | 20 min |
| VJ 877 | 2026-11-06 | VJC | SGN | 0.56 | 25.5 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 676 | 2026-11-05 | HKE | CJU | 0.04 | -4.6 | 34 min |
| KL 888 | 2026-11-04 | KLM | AMS | 0.05 | -1.8 | 18 min |
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| VJ 985 | 2026-11-10 | VJC | PQC | 0.63 | 32.9 | 0 min |
| OD 606 | 2026-11-10 | MXD | KUL | 0.62 | 43.9 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2825 | 0.6751 | 0.1101 | 0.3718 | 10.1 | 2026-11-02T22:02:28+00:00 | 2026-11-10T11:55:40+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2825}
