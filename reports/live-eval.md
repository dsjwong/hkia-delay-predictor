# Live evaluation — predictions vs actuals

Generated 2026-11-14T22:20:16+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2827**.

Dates 2026-11-08..2026-11-15; observed P(delay > 15) = 0.1394; median lead time between last score and departure = 203.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6608 | 0.119 | 0.3935 | 11.361 |
| baseline_airline_hour | 0.6232 | 0.1382 | 0.4483 | 15.97 |
| naive_rate | 0.5 | 0.1199 | 0.4038 | 10.691 |

Coverage: **2827 of 2863** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2827 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0376 | [+0.0084, +0.0689] | **yes** |
| brier | -0.0192 | [-0.0229, -0.0154] | **yes** |
| logloss | -0.0548 | [-0.0650, -0.0436] | **yes** |
| mae | -4.61 | [-4.8990, -4.2873] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-08 † | 377 | 0.1512 | 0.6592 | 0.5897 | 0.1255 | 12.8 | 17.5 |
| 2026-11-09 | 404 | 0.1287 | 0.7165 | 0.6587 | 0.1052 | 9.9 | 15.6 |
| 2026-11-10 | 391 | 0.1714 | 0.7526 | 0.6521 | 0.1272 | 11.7 | 16.1 |
| 2026-11-11 | 396 | 0.1010 | 0.6205 | 0.6142 | 0.0955 | 10.2 | 16.1 |
| 2026-11-12 | 396 | 0.1212 | 0.6581 | 0.6283 | 0.1036 | 8.7 | 14.7 |
| 2026-11-13 | 416 | 0.1298 | 0.6018 | 0.6843 | 0.1168 | 10.2 | 14.7 |
| 2026-11-14 | 416 | 0.1659 | 0.6539 | 0.5838 | 0.1521 | 15.9 | 17.4 |
| 2026-11-15 *† | 31 | 0.2258 | 0.4167 | 0.1964 | 0.1981 | 12.2 | 14.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 72 | 0.6528 | 0.6604 | 0.5494 | 43.4 |
| < 30 min | 186 | 0.1505 | 0.7584 | 0.6137 | 12.0 |
| 30–120 min | 677 | 0.1477 | 0.6733 | 0.6426 | 9.7 |
| 2–12 h | 1773 | 0.1168 | 0.6317 | 0.5975 | 10.8 |
| > 12 h | 119 | 0.1008 | 0.7780 | 0.5962 | 9.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 686 | 0.070 | 0.052 |
| 0.1-0.2 | 1041 | 0.149 | 0.134 |
| 0.2-0.3 | 673 | 0.244 | 0.147 |
| 0.3-0.4 | 278 | 0.339 | 0.284 |
| 0.4-0.5 | 102 | 0.440 | 0.216 |
| 0.5-0.6 | 34 | 0.543 | 0.382 |
| 0.6-0.7 * | 9 | 0.624 | 0.333 |
| 0.7-0.8 * | 3 | 0.756 | 0.667 |
| 0.9-1.0 * | 1 | 0.912 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-14 | RNA | KTM | 0.91 | 55.8 | 83 min |
| LX 139 | 2026-11-14 | SWR | ZRH | 0.79 | 32.6 | 30 min |
| VJ 985 | 2026-11-14 | VJC | PQC | 0.74 | 34.4 | 219 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| OD 606 | 2026-11-14 | MXD | KUL | 0.61 | 44.9 | 22 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-11-12 | HKE | HND | 0.03 | -4.9 | 33 min |
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| UO 132 | 2026-11-10 | HKE | KHH | 0.05 | -1.1 | 36 min |
| QF 128 | 2026-11-14 | QFA | SYD | 0.73 | 30.4 | 15 min |
| JX 236 | 2026-11-14 | SJX | TPE | 0.67 | 24.8 | 9 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2827 | 0.6608 | 0.1190 | 0.3935 | 11.4 | 2026-11-07T07:25:23+00:00 | 2026-11-14T12:21:40+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2827}
