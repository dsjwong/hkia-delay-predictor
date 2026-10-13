# Live evaluation — predictions vs actuals

Generated 2026-10-13T00:37:03+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3052**.

Dates 2026-10-06..2026-10-13; observed P(delay > 15) = 0.1596; median lead time between last score and departure = 189.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6719 | 0.1298 | 0.4186 | 13.211 |
| baseline_airline_hour | 0.6533 | 0.1442 | 0.4595 | 17.615 |
| naive_rate | 0.5 | 0.1341 | 0.439 | 12.301 |

Coverage: **3052 of 3138** departures in the window (97.3%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3052 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0186 | [-0.0005, +0.0381] | no — CI straddles 0 |
| brier | -0.0144 | [-0.0176, -0.0110] | **yes** |
| logloss | -0.0409 | [-0.0504, -0.0316] | **yes** |
| mae | -4.40 | [-4.6926, -4.1082] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-06 † | 363 | 0.2066 | 0.6018 | 0.6177 | 0.1663 | 20.4 | 23.1 |
| 2026-10-07 | 454 | 0.1784 | 0.6703 | 0.6263 | 0.1402 | 14.8 | 19.0 |
| 2026-10-08 | 444 | 0.1532 | 0.6788 | 0.6782 | 0.1266 | 12.5 | 16.8 |
| 2026-10-09 | 449 | 0.1180 | 0.6776 | 0.6584 | 0.1111 | 12.3 | 16.8 |
| 2026-10-10 | 436 | 0.2271 | 0.6730 | 0.6612 | 0.1657 | 14.6 | 18.2 |
| 2026-10-11 | 437 | 0.1236 | 0.6972 | 0.6659 | 0.1094 | 9.8 | 15.1 |
| 2026-10-12 | 434 | 0.1267 | 0.6957 | 0.6393 | 0.1026 | 9.6 | 15.5 |
| 2026-10-13 *† | 35 | 0.0571 | 0.9318 | 0.7727 | 0.0473 | 9.1 | 14.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 82 | 0.7561 | 0.6226 | 0.5754 | 56.0 |
| < 30 min | 198 | 0.2121 | 0.6478 | 0.5994 | 10.7 |
| 30–120 min | 753 | 0.1607 | 0.6615 | 0.6244 | 11.9 |
| 2–12 h | 1959 | 0.1332 | 0.6769 | 0.6601 | 12.4 |
| > 12 h * | 60 | 0.0167 | 0.4576 | 0.5085 | 7.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 837 | 0.064 | 0.061 |
| 0.1-0.2 | 941 | 0.145 | 0.139 |
| 0.2-0.3 | 729 | 0.247 | 0.221 |
| 0.3-0.4 | 392 | 0.343 | 0.237 |
| 0.4-0.5 | 117 | 0.438 | 0.308 |
| 0.5-0.6 | 32 | 0.537 | 0.375 |
| 0.6-0.7 * | 2 | 0.638 | 0.500 |
| 0.8-0.9 * | 2 | 0.851 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-10 | RNA | KTM | 0.87 | 58.7 | 195 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| OD 606 | 2026-10-11 | MXD | KUL | 0.61 | 48.8 | 19 min |
| VJ 877 | 2026-10-12 | VJC | SGN | 0.59 | 21.6 | 40 min |
| TG 639 | 2026-10-10 | THA | BKK | 0.57 | 18.7 | 43 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |
| LX 139 | 2026-10-12 | SWR | ZRH | 0.59 | 16.7 | 11 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3052 | 0.6719 | 0.1298 | 0.4186 | 13.2 | 2026-10-04T23:41:41+00:00 | 2026-10-12T09:56:18+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3052}
