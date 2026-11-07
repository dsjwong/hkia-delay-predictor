# Live evaluation — predictions vs actuals

Generated 2026-11-07T21:46:39+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2843**.

Dates 2026-11-01..2026-11-08; observed P(delay > 15) = 0.1277; median lead time between last score and departure = 218.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6325 | 0.1086 | 0.3727 | 9.64 |
| baseline_airline_hour | 0.6096 | 0.1341 | 0.4412 | 15.35 |
| naive_rate | 0.5 | 0.1114 | 0.382 | 9.674 |

Coverage: **2843 of 2879** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2843 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0229 | [-0.0037, +0.0496] | no — CI straddles 0 |
| brier | -0.0255 | [-0.0291, -0.0220] | **yes** |
| logloss | -0.0685 | [-0.0793, -0.0582] | **yes** |
| mae | -5.71 | [-6.0431, -5.3820] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-01 † | 382 | 0.1204 | 0.6976 | 0.6469 | 0.1003 | 9.7 | 15.7 |
| 2026-11-02 | 406 | 0.1478 | 0.6486 | 0.6369 | 0.1172 | 10.6 | 15.9 |
| 2026-11-03 | 400 | 0.1450 | 0.5864 | 0.5885 | 0.1219 | 10.8 | 16.7 |
| 2026-11-04 | 395 | 0.1114 | 0.6438 | 0.6115 | 0.0980 | 8.9 | 15.4 |
| 2026-11-05 | 398 | 0.1332 | 0.5643 | 0.5821 | 0.1207 | 10.0 | 14.7 |
| 2026-11-06 | 418 | 0.1124 | 0.6627 | 0.6070 | 0.1003 | 8.6 | 14.4 |
| 2026-11-07 | 411 | 0.1241 | 0.6909 | 0.6096 | 0.1021 | 9.1 | 15.1 |
| 2026-11-08 *† | 33 | 0.1212 | 0.6724 | 0.5172 | 0.1074 | 7.9 | 10.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 44 | 0.5227 | 0.4565 | 0.4710 | 31.3 |
| < 30 min | 200 | 0.1550 | 0.5782 | 0.6119 | 9.8 |
| 30–120 min | 614 | 0.1091 | 0.6898 | 0.6433 | 8.9 |
| 2–12 h | 1793 | 0.1244 | 0.6428 | 0.6111 | 9.5 |
| > 12 h | 192 | 0.0990 | 0.6089 | 0.6048 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 743 | 0.070 | 0.082 |
| 0.1-0.2 | 1235 | 0.148 | 0.110 |
| 0.2-0.3 | 652 | 0.237 | 0.149 |
| 0.3-0.4 | 163 | 0.340 | 0.252 |
| 0.4-0.5 | 34 | 0.443 | 0.441 |
| 0.5-0.6 * | 11 | 0.548 | 0.818 |
| 0.6-0.7 * | 4 | 0.643 | 0.750 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-02 | SWR | ZRH | 0.68 | 27.3 | 40 min |
| LX 139 | 2026-11-01 | SWR | ZRH | 0.64 | 27.3 | 40 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| OD 606 | 2026-11-02 | MXD | KUL | 0.60 | 39.1 | 92 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| EK 381 | 2026-11-02 | UAE | DXB | 0.03 | -0.4 | 26 min |
| QR 817 | 2026-11-02 | QTR | DOH | 0.03 | 4.3 | 37 min |
| 3U 8396 | 2026-11-01 | CSC | CTU | 0.04 | -4.3 | 132 min |
| LX 139 | 2026-11-05 | SWR | ZRH | 0.62 | 23.1 | 9 min |
| VJ 985 | 2026-11-03 | VJC | PQC | 0.56 | 23.3 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 389 | 0.6969 | 0.1006 | 0.3480 | 9.8 | 2026-10-31T00:15:26+00:00 | 2026-11-01T09:29:58+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 2454 | 0.6243 | 0.1099 | 0.3766 | 9.6 | 2026-11-01T16:14:42+00:00 | 2026-11-07T14:15:06+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 389, 'f6ae66c@2026-11-01T10:28:21+00:00': 2454}
