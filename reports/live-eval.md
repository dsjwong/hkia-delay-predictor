# Live evaluation — predictions vs actuals

Generated 2026-10-13T22:42:15+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3075**.

Dates 2026-10-07..2026-10-14; observed P(delay > 15) = 0.1525; median lead time between last score and departure = 193.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6888 | 0.1237 | 0.4024 | 12.006 |
| baseline_airline_hour | 0.6639 | 0.1401 | 0.4501 | 16.736 |
| naive_rate | 0.5 | 0.1293 | 0.4271 | 11.388 |

Coverage: **3075 of 3114** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3075 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0249 | [+0.0050, +0.0443] | **yes** |
| brier | -0.0164 | [-0.0194, -0.0130] | **yes** |
| logloss | -0.0477 | [-0.0565, -0.0382] | **yes** |
| mae | -4.73 | [-5.0198, -4.4456] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-07 † | 415 | 0.1928 | 0.6583 | 0.5949 | 0.1495 | 15.6 | 19.9 |
| 2026-10-08 | 444 | 0.1532 | 0.6788 | 0.6782 | 0.1266 | 12.5 | 16.8 |
| 2026-10-09 | 449 | 0.1180 | 0.6776 | 0.6584 | 0.1111 | 12.3 | 16.8 |
| 2026-10-10 | 436 | 0.2271 | 0.6730 | 0.6612 | 0.1657 | 14.6 | 18.2 |
| 2026-10-11 | 437 | 0.1236 | 0.6972 | 0.6659 | 0.1094 | 9.8 | 15.1 |
| 2026-10-12 | 434 | 0.1267 | 0.6957 | 0.6393 | 0.1026 | 9.6 | 15.5 |
| 2026-10-13 | 423 | 0.1371 | 0.7361 | 0.7383 | 0.1091 | 10.3 | 15.5 |
| 2026-10-14 *† | 37 | 0.0541 | 0.8000 | 0.9143 | 0.0447 | 5.5 | 10.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 76 | 0.7368 | 0.6411 | 0.5625 | 47.6 |
| < 30 min | 201 | 0.2239 | 0.6972 | 0.6325 | 11.1 |
| 30–120 min | 737 | 0.1628 | 0.6943 | 0.6620 | 11.4 |
| 2–12 h | 1997 | 0.1237 | 0.6836 | 0.6546 | 11.2 |
| > 12 h * | 64 | 0.0156 | 0.5873 | 0.6905 | 6.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 857 | 0.065 | 0.055 |
| 0.1-0.2 | 939 | 0.145 | 0.119 |
| 0.2-0.3 | 740 | 0.247 | 0.222 |
| 0.3-0.4 | 391 | 0.341 | 0.235 |
| 0.4-0.5 | 115 | 0.439 | 0.339 |
| 0.5-0.6 * | 29 | 0.536 | 0.414 |
| 0.6-0.7 * | 2 | 0.638 | 0.500 |
| 0.7-0.8 * | 1 | 0.731 | 1.000 |
| 0.8-0.9 * | 1 | 0.873 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-10 | RNA | KTM | 0.87 | 58.7 | 195 min |
| VJ 985 | 2026-10-13 | VJC | PQC | 0.73 | 30.9 | 33 min |
| OD 606 | 2026-10-11 | MXD | KUL | 0.61 | 48.8 | 19 min |
| VJ 877 | 2026-10-12 | VJC | SGN | 0.59 | 21.6 | 40 min |
| TG 639 | 2026-10-10 | THA | BKK | 0.57 | 18.7 | 43 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| EK 381 | 2026-10-09 | UAE | DXB | 0.04 | 0.4 | 36 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |
| LX 139 | 2026-10-12 | SWR | ZRH | 0.59 | 16.7 | 11 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3075 | 0.6888 | 0.1237 | 0.4024 | 12.0 | 2026-10-06T13:45:06+00:00 | 2026-10-13T16:34:19+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3075}
