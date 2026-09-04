# Live evaluation — predictions vs actuals

Generated 2026-09-04T20:44:50+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2955**.

Dates 2026-08-29..2026-09-05; observed P(delay > 15) = 0.1993; median lead time between last score and departure = 138.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6473 | 0.1601 | 0.4937 | 13.304 |
| baseline_airline_hour | 0.6225 | 0.1614 | 0.5 | 16.506 |
| naive_rate | 0.5 | 0.1596 | 0.4995 | 12.658 |

Coverage: **2955 of 2997** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2955 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0248 | [+0.0016, +0.0480] | **yes** |
| brier | -0.0013 | [-0.0049, +0.0024] | no — CI straddles 0 |
| logloss | -0.0063 | [-0.0159, +0.0034] | no — CI straddles 0 |
| mae | -3.20 | [-3.5051, -2.9174] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-29 † | 402 | 0.2388 | 0.7038 | 0.6922 | 0.1611 | 14.3 | 17.3 |
| 2026-08-30 | 451 | 0.2705 | 0.6491 | 0.6333 | 0.1863 | 14.9 | 17.6 |
| 2026-08-31 | 442 | 0.1991 | 0.6230 | 0.5766 | 0.1751 | 14.8 | 16.9 |
| 2026-09-01 | 403 | 0.1737 | 0.5722 | 0.6105 | 0.1938 | 15.2 | 15.6 |
| 2026-09-02 | 405 | 0.1802 | 0.6607 | 0.6256 | 0.1432 | 12.3 | 16.6 |
| 2026-09-03 | 393 | 0.1578 | 0.6067 | 0.5606 | 0.1317 | 10.8 | 16.0 |
| 2026-09-04 | 418 | 0.1770 | 0.7245 | 0.6272 | 0.1309 | 10.7 | 15.6 |
| 2026-09-05 *† | 41 | 0.0976 | 0.4459 | 0.7095 | 0.1033 | 11.2 | 14.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 112 | 0.7589 | 0.7316 | 0.6063 | 47.8 |
| < 30 min | 314 | 0.1624 | 0.6679 | 0.6456 | 10.9 |
| 30–120 min | 970 | 0.2072 | 0.6335 | 0.5884 | 12.0 |
| 2–12 h | 1543 | 0.1633 | 0.6403 | 0.6421 | 12.2 |
| > 12 h * | 16 | 0.0000 | — | — | 5.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 450 | 0.065 | 0.087 |
| 0.1-0.2 | 813 | 0.149 | 0.148 |
| 0.2-0.3 | 712 | 0.248 | 0.187 |
| 0.3-0.4 | 466 | 0.347 | 0.281 |
| 0.4-0.5 | 331 | 0.445 | 0.317 |
| 0.5-0.6 | 116 | 0.537 | 0.302 |
| 0.6-0.7 | 50 | 0.643 | 0.360 |
| 0.7-0.8 * | 14 | 0.736 | 0.357 |
| 0.8-0.9 * | 3 | 0.845 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-29 | SWR | ZRH | 0.85 | 31.3 | 39 min |
| RA 410 | 2026-09-01 | RNA | KTM | 0.81 | 45.1 | 182 min |
| CX 548 | 2026-09-01 | CPA | HND | 0.76 | 33.8 | 43 min |
| VJ 985 | 2026-08-29 | VJC | PQC | 0.73 | 38.2 | 21 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 17 calls published at P ≥ 70%**, 8 were actually more than 15 minutes late (47%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 704 | 2026-09-03 | HKE | BKK | 0.02 | -2.8 | 21 min |
| NH 814 | 2026-09-03 | ANA | HND | 0.03 | -4.8 | 21 min |
| KE 2012 | 2026-09-05 | KAL | ICN | 0.03 | -2.5 | 161 min |
| LX 139 | 2026-08-31 | SWR | ZRH | 0.78 | 29.8 | 15 min |
| CX 520 | 2026-09-01 | CPA | NRT | 0.76 | 40.9 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2955 | 0.6473 | 0.1601 | 0.4937 | 13.3 | 2026-08-28T01:12:48+00:00 | 2026-09-04T17:14:36+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2955}
