# Live evaluation — predictions vs actuals

Generated 2026-11-06T23:06:01+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2867**.

Dates 2026-10-31..2026-11-07; observed P(delay > 15) = 0.1263; median lead time between last score and departure = 208.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6311 | 0.1083 | 0.3715 | 9.857 |
| baseline_airline_hour | 0.6177 | 0.1332 | 0.4392 | 15.458 |
| naive_rate | 0.5 | 0.1103 | 0.3792 | 9.8 |

Coverage: **2867 of 2906** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2867 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0134 | [-0.0126, +0.0388] | no — CI straddles 0 |
| brier | -0.0249 | [-0.0284, -0.0213] | **yes** |
| logloss | -0.0677 | [-0.0776, -0.0569] | **yes** |
| mae | -5.60 | [-5.9272, -5.2768] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-31 † | 394 | 0.1168 | 0.7035 | 0.6800 | 0.1002 | 10.0 | 15.5 |
| 2026-11-01 | 418 | 0.1172 | 0.6891 | 0.6486 | 0.0984 | 9.9 | 15.7 |
| 2026-11-02 | 406 | 0.1478 | 0.6486 | 0.6369 | 0.1172 | 10.6 | 15.9 |
| 2026-11-03 | 400 | 0.1450 | 0.5864 | 0.5885 | 0.1219 | 10.8 | 16.7 |
| 2026-11-04 | 395 | 0.1114 | 0.6438 | 0.6115 | 0.0980 | 8.9 | 15.4 |
| 2026-11-05 | 398 | 0.1332 | 0.5643 | 0.5821 | 0.1207 | 10.0 | 14.7 |
| 2026-11-06 | 418 | 0.1124 | 0.6627 | 0.6070 | 0.1003 | 8.6 | 14.4 |
| 2026-11-07 *† | 38 | 0.1316 | 0.4424 | 0.4091 | 0.1254 | 12.5 | 15.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 53 | 0.5472 | 0.5589 | 0.5503 | 35.4 |
| < 30 min | 223 | 0.1345 | 0.5842 | 0.6288 | 9.5 |
| 30–120 min | 653 | 0.1133 | 0.6709 | 0.6285 | 9.1 |
| 2–12 h | 1751 | 0.1199 | 0.6347 | 0.6266 | 9.6 |
| > 12 h | 187 | 0.1016 | 0.6010 | 0.5797 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 760 | 0.070 | 0.079 |
| 0.1-0.2 | 1235 | 0.148 | 0.113 |
| 0.2-0.3 | 651 | 0.240 | 0.143 |
| 0.3-0.4 | 173 | 0.338 | 0.243 |
| 0.4-0.5 | 31 | 0.441 | 0.452 |
| 0.5-0.6 * | 12 | 0.550 | 0.833 |
| 0.6-0.7 * | 4 | 0.647 | 0.500 |
| 0.7-0.8 * | 1 | 0.793 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-31 | RNA | KTM | 0.79 | 41.3 | 55 min |
| LX 139 | 2026-11-02 | SWR | ZRH | 0.68 | 27.3 | 40 min |
| LX 139 | 2026-11-01 | SWR | ZRH | 0.64 | 27.3 | 40 min |
| OD 606 | 2026-11-02 | MXD | KUL | 0.60 | 39.1 | 92 min |
| LX 139 | 2026-10-31 | SWR | ZRH | 0.57 | 21.6 | 42 min |

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
| 42715b6@2026-10-29T14:57:07+00:00 | 819 | 0.6962 | 0.0995 | 0.3451 | 10.0 | 2026-10-30T02:44:37+00:00 | 2026-11-01T09:29:58+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 2048 | 0.6094 | 0.1118 | 0.3821 | 9.8 | 2026-11-01T16:14:42+00:00 | 2026-11-06T16:26:49+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 819, 'f6ae66c@2026-11-01T10:28:21+00:00': 2048}
