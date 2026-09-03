# Live evaluation — predictions vs actuals

Generated 2026-09-03T21:00:53+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2983**.

Dates 2026-08-28..2026-09-04; observed P(delay > 15) = 0.2015; median lead time between last score and departure = 154.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6288 | 0.1662 | 0.509 | 13.915 |
| baseline_airline_hour | 0.6168 | 0.1626 | 0.5033 | 16.655 |
| naive_rate | 0.5 | 0.1609 | 0.5024 | 12.918 |

Coverage: **2983 of 3024** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2983 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0120 | [-0.0106, +0.0354] | no — CI straddles 0 |
| brier | +0.0036 | [-0.0002, +0.0072] | no — CI straddles 0 |
| logloss | +0.0057 | [-0.0042, +0.0152] | no — CI straddles 0 |
| mae | -2.74 | [-3.0384, -2.4615] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-28 † | 408 | 0.1838 | 0.6375 | 0.6289 | 0.1695 | 15.2 | 16.9 |
| 2026-08-29 | 444 | 0.2297 | 0.7014 | 0.6879 | 0.1579 | 14.1 | 17.1 |
| 2026-08-30 | 451 | 0.2705 | 0.6491 | 0.6333 | 0.1863 | 14.9 | 17.6 |
| 2026-08-31 | 442 | 0.1991 | 0.6230 | 0.5766 | 0.1751 | 14.8 | 16.9 |
| 2026-09-01 | 403 | 0.1737 | 0.5722 | 0.6105 | 0.1938 | 15.2 | 15.6 |
| 2026-09-02 | 405 | 0.1802 | 0.6607 | 0.6256 | 0.1432 | 12.3 | 16.6 |
| 2026-09-03 | 393 | 0.1578 | 0.6067 | 0.5606 | 0.1317 | 10.8 | 16.0 |
| 2026-09-04 *† | 37 | 0.2432 | 0.5853 | 0.5754 | 0.1965 | 11.7 | 13.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 107 | 0.7664 | 0.6863 | 0.5520 | 47.5 |
| < 30 min | 294 | 0.1735 | 0.6714 | 0.6464 | 12.1 |
| 30–120 min | 878 | 0.2073 | 0.6036 | 0.5698 | 12.3 |
| 2–12 h | 1679 | 0.1686 | 0.6208 | 0.6268 | 12.9 |
| > 12 h * | 25 | 0.1200 | 0.8182 | 0.7576 | 12.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 369 | 0.067 | 0.092 |
| 0.1-0.2 | 733 | 0.150 | 0.146 |
| 0.2-0.3 | 728 | 0.249 | 0.184 |
| 0.3-0.4 | 518 | 0.348 | 0.266 |
| 0.4-0.5 | 412 | 0.445 | 0.282 |
| 0.5-0.6 | 147 | 0.537 | 0.286 |
| 0.6-0.7 | 58 | 0.641 | 0.362 |
| 0.7-0.8 * | 14 | 0.736 | 0.357 |
| 0.8-0.9 * | 4 | 0.847 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |
| LX 139 | 2026-08-29 | SWR | ZRH | 0.85 | 31.3 | 39 min |
| RA 410 | 2026-09-01 | RNA | KTM | 0.81 | 45.1 | 182 min |
| CX 548 | 2026-09-01 | CPA | HND | 0.76 | 33.8 | 43 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 18 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 704 | 2026-09-03 | HKE | BKK | 0.02 | -2.8 | 21 min |
| NH 814 | 2026-09-03 | ANA | HND | 0.03 | -4.8 | 21 min |
| KE 2006 | 2026-09-02 | KAL | ICN | 0.04 | -0.5 | 23 min |
| LX 139 | 2026-08-31 | SWR | ZRH | 0.78 | 29.8 | 15 min |
| CX 520 | 2026-09-01 | CPA | NRT | 0.76 | 40.9 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2983 | 0.6288 | 0.1662 | 0.5090 | 13.9 | 2026-08-27T05:30:18+00:00 | 2026-09-03T17:55:35+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2983}
