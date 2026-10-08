# Live evaluation — predictions vs actuals

Generated 2026-10-08T23:19:30+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3131**.

Dates 2026-10-02..2026-10-09; observed P(delay > 15) = 0.1795; median lead time between last score and departure = 184.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6633 | 0.1439 | 0.4529 | 14.168 |
| baseline_airline_hour | 0.6419 | 0.1528 | 0.4787 | 17.894 |
| naive_rate | 0.5 | 0.1473 | 0.4706 | 13.287 |

Coverage: **3131 of 3173** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3131 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0214 | [-0.0008, +0.0431] | no — CI straddles 0 |
| brier | -0.0089 | [-0.0123, -0.0056] | **yes** |
| logloss | -0.0258 | [-0.0351, -0.0167] | **yes** |
| mae | -3.73 | [-4.0016, -3.4651] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-02 † | 412 | 0.2937 | 0.6014 | 0.5921 | 0.2056 | 14.1 | 16.5 |
| 2026-10-03 | 437 | 0.1831 | 0.6382 | 0.5936 | 0.1584 | 15.6 | 18.6 |
| 2026-10-04 | 448 | 0.1786 | 0.7096 | 0.6825 | 0.1381 | 13.6 | 17.2 |
| 2026-10-05 | 451 | 0.1086 | 0.6805 | 0.6774 | 0.1019 | 11.1 | 16.6 |
| 2026-10-06 | 449 | 0.1782 | 0.6253 | 0.6585 | 0.1469 | 18.0 | 20.8 |
| 2026-10-07 | 454 | 0.1784 | 0.6703 | 0.6263 | 0.1402 | 14.8 | 19.0 |
| 2026-10-08 | 444 | 0.1532 | 0.6788 | 0.6782 | 0.1266 | 12.5 | 16.8 |
| 2026-10-09 *† | 36 | 0.0833 | 0.6364 | 0.6414 | 0.0853 | 8.6 | 11.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 109 | 0.7706 | 0.5564 | 0.4590 | 56.4 |
| < 30 min | 229 | 0.2140 | 0.7105 | 0.6634 | 11.3 |
| 30–120 min | 772 | 0.1593 | 0.6747 | 0.6066 | 11.9 |
| 2–12 h | 1956 | 0.1539 | 0.6431 | 0.6450 | 13.3 |
| > 12 h * | 65 | 0.0769 | 0.7917 | 0.7183 | 8.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 621 | 0.064 | 0.056 |
| 0.1-0.2 | 934 | 0.149 | 0.146 |
| 0.2-0.3 | 780 | 0.247 | 0.221 |
| 0.3-0.4 | 460 | 0.347 | 0.239 |
| 0.4-0.5 | 219 | 0.438 | 0.274 |
| 0.5-0.6 | 83 | 0.543 | 0.313 |
| 0.6-0.7 * | 25 | 0.637 | 0.600 |
| 0.7-0.8 * | 6 | 0.741 | 0.833 |
| 0.8-0.9 * | 3 | 0.833 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-03 | RNA | KTM | 0.85 | 63.2 | 598 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| CX 302 | 2026-10-04 | CPA | PVG | 0.77 | 32.0 | 79 min |
| CX 161 | 2026-10-04 | CPA | SYD | 0.74 | 31.5 | 35 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 8 were actually more than 15 minutes late (89%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| OD 606 | 2026-10-03 | MXD | KUL | 0.77 | 60.0 | 7 min |
| CX 520 | 2026-10-02 | CPA | NRT | 0.69 | 25.8 | 12 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3131 | 0.6633 | 0.1439 | 0.4529 | 14.2 | 2026-10-01T09:09:47+00:00 | 2026-10-08T15:02:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3131}
