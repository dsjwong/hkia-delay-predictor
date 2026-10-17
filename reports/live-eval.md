# Live evaluation — predictions vs actuals

Generated 2026-10-17T20:34:05+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3024**.

Dates 2026-10-11..2026-10-18; observed P(delay > 15) = 0.1286; median lead time between last score and departure = 151.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.696 | 0.1111 | 0.3697 | 10.794 |
| baseline_airline_hour | 0.6804 | 0.1294 | 0.4263 | 15.707 |
| naive_rate | 0.5 | 0.1121 | 0.3838 | 10.347 |

Coverage: **3024 of 3060** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3024 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0156 | [-0.0070, +0.0368] | no — CI straddles 0 |
| brier | -0.0183 | [-0.0213, -0.0151] | **yes** |
| logloss | -0.0566 | [-0.0649, -0.0477] | **yes** |
| mae | -4.91 | [-5.1902, -4.6200] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-11 † | 401 | 0.1272 | 0.6834 | 0.6529 | 0.1134 | 10.0 | 15.3 |
| 2026-10-12 | 434 | 0.1267 | 0.6957 | 0.6393 | 0.1026 | 9.6 | 15.5 |
| 2026-10-13 | 423 | 0.1371 | 0.7361 | 0.7383 | 0.1091 | 10.3 | 15.5 |
| 2026-10-14 | 420 | 0.1071 | 0.7107 | 0.7070 | 0.1055 | 10.2 | 15.1 |
| 2026-10-15 | 421 | 0.1116 | 0.7419 | 0.7044 | 0.0940 | 9.1 | 15.1 |
| 2026-10-16 | 448 | 0.1250 | 0.6116 | 0.6268 | 0.1205 | 12.3 | 15.9 |
| 2026-10-17 | 441 | 0.1678 | 0.7029 | 0.6981 | 0.1335 | 14.0 | 17.7 |
| 2026-10-18 *† | 36 | 0.0833 | 0.8485 | 0.6465 | 0.0827 | 9.3 | 13.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 77 | 0.6234 | 0.6114 | 0.7026 | 46.2 |
| < 30 min | 277 | 0.1588 | 0.7087 | 0.6630 | 11.4 |
| 30–120 min | 918 | 0.1362 | 0.7055 | 0.6743 | 9.8 |
| 2–12 h | 1703 | 0.1004 | 0.6921 | 0.6839 | 9.8 |
| > 12 h * | 49 | 0.0204 | 0.4583 | 0.6458 | 6.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 834 | 0.063 | 0.037 |
| 0.1-0.2 | 999 | 0.145 | 0.106 |
| 0.2-0.3 | 657 | 0.246 | 0.189 |
| 0.3-0.4 | 349 | 0.341 | 0.206 |
| 0.4-0.5 | 135 | 0.443 | 0.281 |
| 0.5-0.6 | 36 | 0.539 | 0.250 |
| 0.6-0.7 * | 10 | 0.639 | 0.600 |
| 0.7-0.8 * | 3 | 0.722 | 0.667 |
| 0.8-0.9 * | 1 | 0.870 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| VJ 985 | 2026-10-13 | VJC | PQC | 0.73 | 30.9 | 33 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |
| NH 812 | 2026-10-14 | ANA | NRT | 0.70 | 24.0 | 35 min |
| LX 139 | 2026-10-17 | SWR | ZRH | 0.68 | 21.5 | 32 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| UO 130 | 2026-10-11 | HKE | KHH | 0.04 | 1.4 | 19 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3024 | 0.6960 | 0.1111 | 0.3697 | 10.8 | 2026-10-10T14:53:49+00:00 | 2026-10-17T16:01:07+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3024}
