# Live evaluation — predictions vs actuals

Generated 2026-11-05T23:37:10+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2866**.

Dates 2026-10-30..2026-11-06; observed P(delay > 15) = 0.1333; median lead time between last score and departure = 205.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.653 | 0.1108 | 0.3764 | 10.24 |
| baseline_airline_hour | 0.6355 | 0.1345 | 0.4419 | 15.666 |
| naive_rate | 0.5 | 0.1155 | 0.3926 | 10.27 |

Coverage: **2866 of 2908** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2866 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0175 | [-0.0079, +0.0425] | no — CI straddles 0 |
| brier | -0.0237 | [-0.0273, -0.0199] | **yes** |
| logloss | -0.0655 | [-0.0760, -0.0544] | **yes** |
| mae | -5.43 | [-5.7587, -5.0907] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-30 † | 382 | 0.1780 | 0.7505 | 0.6875 | 0.1283 | 12.2 | 16.7 |
| 2026-10-31 | 433 | 0.1085 | 0.7025 | 0.6898 | 0.0958 | 9.7 | 15.0 |
| 2026-11-01 | 418 | 0.1172 | 0.6891 | 0.6486 | 0.0984 | 9.9 | 15.7 |
| 2026-11-02 | 406 | 0.1478 | 0.6486 | 0.6369 | 0.1172 | 10.6 | 15.9 |
| 2026-11-03 | 400 | 0.1450 | 0.5864 | 0.5885 | 0.1219 | 10.8 | 16.7 |
| 2026-11-04 | 395 | 0.1114 | 0.6438 | 0.6115 | 0.0980 | 8.9 | 15.4 |
| 2026-11-05 | 398 | 0.1332 | 0.5643 | 0.5821 | 0.1207 | 10.0 | 14.7 |
| 2026-11-06 *† | 34 | 0.0882 | 0.3871 | 0.2903 | 0.0853 | 7.3 | 10.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 58 | 0.6207 | 0.5442 | 0.5492 | 49.3 |
| < 30 min | 234 | 0.1282 | 0.6215 | 0.6685 | 9.0 |
| 30–120 min | 685 | 0.1124 | 0.6871 | 0.6578 | 9.3 |
| 2–12 h | 1707 | 0.1289 | 0.6638 | 0.6487 | 9.7 |
| > 12 h | 182 | 0.1044 | 0.5568 | 0.5053 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 784 | 0.069 | 0.079 |
| 0.1-0.2 | 1242 | 0.148 | 0.114 |
| 0.2-0.3 | 633 | 0.240 | 0.166 |
| 0.3-0.4 | 166 | 0.339 | 0.301 |
| 0.4-0.5 * | 26 | 0.439 | 0.500 |
| 0.5-0.6 * | 9 | 0.557 | 0.778 |
| 0.6-0.7 * | 5 | 0.652 | 0.600 |
| 0.7-0.8 * | 1 | 0.793 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-31 | RNA | KTM | 0.79 | 41.3 | 55 min |
| LX 139 | 2026-11-02 | SWR | ZRH | 0.68 | 27.3 | 40 min |
| LX 139 | 2026-10-30 | SWR | ZRH | 0.67 | 27.1 | 39 min |
| LX 139 | 2026-11-01 | SWR | ZRH | 0.64 | 27.3 | 40 min |
| OD 606 | 2026-11-02 | MXD | KUL | 0.60 | 39.1 | 92 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| EK 381 | 2026-11-02 | UAE | DXB | 0.03 | -0.4 | 26 min |
| QR 817 | 2026-11-02 | QTR | DOH | 0.03 | 4.3 | 37 min |
| 3U 8396 | 2026-11-01 | CSC | CTU | 0.04 | -4.3 | 132 min |
| VJ 985 | 2026-10-31 | VJC | PQC | 0.65 | 26.4 | -3 min |
| LX 139 | 2026-11-05 | SWR | ZRH | 0.62 | 23.1 | 9 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 1238 | 0.7169 | 0.1069 | 0.3626 | 10.6 | 2026-10-29T19:04:17+00:00 | 2026-11-01T09:29:58+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 * | 2 | — | 0.0390 | 0.2030 | 4.0 | 2026-10-29T13:25:39+00:00 | 2026-10-29T13:25:39+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 1626 | 0.6080 | 0.1139 | 0.3871 | 10.0 | 2026-11-01T16:14:42+00:00 | 2026-11-05T15:41:04+00:00 |

`*` = thin (< 100 flights — AUC standard error is large, treat as noise). Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 1238, '4a4212f@2026-08-25T09:35:34+00:00': 2, 'f6ae66c@2026-11-01T10:28:21+00:00': 1626}
