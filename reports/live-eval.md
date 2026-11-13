# Live evaluation — predictions vs actuals

Generated 2026-11-13T23:31:05+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2818**.

Dates 2026-11-07..2026-11-14; observed P(delay > 15) = 0.1359; median lead time between last score and departure = 210.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6723 | 0.1129 | 0.3779 | 10.391 |
| baseline_airline_hour | 0.624 | 0.1368 | 0.445 | 15.64 |
| naive_rate | 0.5 | 0.1174 | 0.3975 | 10.186 |

Coverage: **2818 of 2860** departures in the window (98.5%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2818 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0483 | [+0.0183, +0.0775] | **yes** |
| brier | -0.0239 | [-0.0275, -0.0203] | **yes** |
| logloss | -0.0671 | [-0.0767, -0.0562] | **yes** |
| mae | -5.25 | [-5.5453, -4.9584] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-07 † | 369 | 0.1274 | 0.7122 | 0.6171 | 0.1028 | 8.8 | 15.2 |
| 2026-11-08 | 413 | 0.1525 | 0.6713 | 0.5853 | 0.1249 | 12.9 | 17.5 |
| 2026-11-09 | 404 | 0.1287 | 0.7165 | 0.6587 | 0.1052 | 9.9 | 15.6 |
| 2026-11-10 | 391 | 0.1714 | 0.7526 | 0.6521 | 0.1272 | 11.7 | 16.1 |
| 2026-11-11 | 396 | 0.1010 | 0.6205 | 0.6142 | 0.0955 | 10.2 | 16.1 |
| 2026-11-12 | 396 | 0.1212 | 0.6581 | 0.6283 | 0.1036 | 8.7 | 14.7 |
| 2026-11-13 | 416 | 0.1298 | 0.6018 | 0.6843 | 0.1168 | 10.2 | 14.7 |
| 2026-11-14 *† | 33 | 0.3636 | 0.7262 | 0.5040 | 0.2688 | 12.0 | 11.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 70 | 0.6571 | 0.6495 | 0.5195 | 45.6 |
| < 30 min | 166 | 0.1386 | 0.7242 | 0.6662 | 8.9 |
| 30–120 min | 630 | 0.1381 | 0.6880 | 0.6554 | 9.1 |
| 2–12 h | 1828 | 0.1182 | 0.6519 | 0.5959 | 9.7 |
| > 12 h | 124 | 0.0887 | 0.7506 | 0.6581 | 8.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 751 | 0.070 | 0.055 |
| 0.1-0.2 | 1138 | 0.148 | 0.130 |
| 0.2-0.3 | 673 | 0.242 | 0.162 |
| 0.3-0.4 | 199 | 0.336 | 0.317 |
| 0.4-0.5 | 39 | 0.442 | 0.308 |
| 0.5-0.6 * | 13 | 0.552 | 0.538 |
| 0.6-0.7 * | 4 | 0.632 | 0.500 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| LX 139 | 2026-11-13 | SWR | ZRH | 0.59 | 21.8 | 31 min |
| LX 139 | 2026-11-12 | SWR | ZRH | 0.57 | 23.2 | 32 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-11-12 | HKE | HND | 0.03 | -4.9 | 33 min |
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| UO 132 | 2026-11-10 | HKE | KHH | 0.05 | -1.1 | 36 min |
| VJ 985 | 2026-11-10 | VJC | PQC | 0.63 | 32.9 | 0 min |
| OD 606 | 2026-11-10 | MXD | KUL | 0.62 | 43.9 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2818 | 0.6723 | 0.1129 | 0.3779 | 10.4 | 2026-11-06T08:41:41+00:00 | 2026-11-13T11:18:31+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2818}
