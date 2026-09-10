# Live evaluation — predictions vs actuals

Generated 2026-09-10T20:50:20+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2802**.

Dates 2026-09-04..2026-09-11; observed P(delay > 15) = 0.1313; median lead time between last score and departure = 120.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6899 | 0.1142 | 0.3776 | 10.976 |
| baseline_airline_hour | 0.6553 | 0.1336 | 0.4368 | 16.3 |
| naive_rate | 0.5 | 0.1141 | 0.3889 | 10.101 |

Coverage: **2802 of 2839** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2802 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0346 | [+0.0069, +0.0620] | **yes** |
| brier | -0.0194 | [-0.0234, -0.0156] | **yes** |
| logloss | -0.0592 | [-0.0705, -0.0479] | **yes** |
| mae | -5.32 | [-5.6732, -4.9860] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-04 † | 381 | 0.1759 | 0.7448 | 0.6382 | 0.1281 | 10.6 | 15.8 |
| 2026-09-05 | 410 | 0.1195 | 0.6704 | 0.6390 | 0.1133 | 10.8 | 16.3 |
| 2026-09-06 | 410 | 0.1732 | 0.6271 | 0.6146 | 0.1686 | 14.4 | 15.0 |
| 2026-09-07 | 400 | 0.0975 | 0.7261 | 0.7205 | 0.0904 | 9.9 | 16.5 |
| 2026-09-08 | 384 | 0.0885 | 0.6350 | 0.6201 | 0.0833 | 9.6 | 17.0 |
| 2026-09-09 | 384 | 0.1016 | 0.7097 | 0.7427 | 0.0860 | 10.6 | 17.8 |
| 2026-09-10 | 397 | 0.1537 | 0.6538 | 0.6665 | 0.1244 | 10.7 | 15.9 |
| 2026-09-11 *† | 36 | 0.2222 | 0.8839 | 0.7723 | 0.1424 | 12.4 | 14.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 90 | 0.6556 | 0.5519 | 0.4754 | 42.3 |
| < 30 min | 311 | 0.1125 | 0.6993 | 0.6126 | 9.0 |
| 30–120 min | 1058 | 0.1181 | 0.6923 | 0.6381 | 9.6 |
| 2–12 h | 1328 | 0.1122 | 0.7080 | 0.7132 | 10.5 |
| > 12 h * | 15 | 0.0000 | — | — | 6.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 860 | 0.062 | 0.048 |
| 0.1-0.2 | 967 | 0.145 | 0.120 |
| 0.2-0.3 | 562 | 0.243 | 0.180 |
| 0.3-0.4 | 220 | 0.340 | 0.255 |
| 0.4-0.5 | 99 | 0.447 | 0.273 |
| 0.5-0.6 | 56 | 0.550 | 0.286 |
| 0.6-0.7 * | 29 | 0.646 | 0.241 |
| 0.7-0.8 * | 9 | 0.726 | 0.444 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| HX 608 | 2026-09-06 | CRK | NRT | 0.75 | 31.4 | 24 min |
| HX 618 | 2026-09-06 | CRK | KIX | 0.74 | 35.0 | 25 min |
| NH 812 | 2026-09-06 | ANA | NRT | 0.72 | 30.4 | 23 min |
| CX 504 | 2026-09-06 | CPA | NRT | 0.72 | 36.3 | 64 min |
| CX 342 | 2026-09-06 | CPA | SHA | 0.68 | 34.2 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (44%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 700 | 2026-09-10 | HKE | BKK | 0.01 | -4.3 | 26 min |
| UO 670 | 2026-09-10 | HKE | NGO | 0.02 | -5.8 | 48 min |
| KE 2012 | 2026-09-05 | KAL | ICN | 0.03 | -2.5 | 161 min |
| DL 088 | 2026-09-06 | DAL | LAX | 0.74 | 38.0 | 10 min |
| OD 606 | 2026-09-06 | MXD | KUL | 0.73 | 69.3 | 0 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2802 | 0.6899 | 0.1142 | 0.3776 | 11.0 | 2026-09-03T05:17:35+00:00 | 2026-09-10T17:23:10+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2802}
