# Live evaluation — predictions vs actuals

Generated 2026-10-07T23:03:50+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3143**.

Dates 2026-10-01..2026-10-08; observed P(delay > 15) = 0.1836; median lead time between last score and departure = 180.9 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6618 | 0.146 | 0.4583 | 13.812 |
| baseline_airline_hour | 0.6424 | 0.1542 | 0.4826 | 17.48 |
| naive_rate | 0.5 | 0.1499 | 0.4768 | 13.241 |

Coverage: **3143 of 3186** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3143 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0194 | [-0.0021, +0.0406] | no — CI straddles 0 |
| brier | -0.0082 | [-0.0114, -0.0051] | **yes** |
| logloss | -0.0243 | [-0.0331, -0.0159] | **yes** |
| mae | -3.67 | [-3.9235, -3.4211] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-01 † | 411 | 0.1776 | 0.6742 | 0.6689 | 0.1410 | 10.2 | 14.5 |
| 2026-10-02 | 454 | 0.2819 | 0.6236 | 0.6199 | 0.1973 | 13.6 | 15.9 |
| 2026-10-03 | 437 | 0.1831 | 0.6382 | 0.5936 | 0.1584 | 15.6 | 18.6 |
| 2026-10-04 | 448 | 0.1786 | 0.7096 | 0.6825 | 0.1381 | 13.6 | 17.2 |
| 2026-10-05 | 451 | 0.1086 | 0.6805 | 0.6774 | 0.1019 | 11.1 | 16.6 |
| 2026-10-06 | 449 | 0.1782 | 0.6253 | 0.6585 | 0.1469 | 18.0 | 20.8 |
| 2026-10-07 | 454 | 0.1784 | 0.6703 | 0.6263 | 0.1402 | 14.8 | 19.0 |
| 2026-10-08 *† | 39 | 0.1538 | 0.7273 | 0.6843 | 0.1196 | 8.2 | 10.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 108 | 0.7593 | 0.5940 | 0.4873 | 53.4 |
| < 30 min | 236 | 0.2288 | 0.7228 | 0.6792 | 11.5 |
| 30–120 min | 819 | 0.1563 | 0.6815 | 0.6161 | 11.3 |
| 2–12 h | 1921 | 0.1598 | 0.6373 | 0.6389 | 13.1 |
| > 12 h * | 59 | 0.1017 | 0.7374 | 0.6855 | 8.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 601 | 0.064 | 0.055 |
| 0.1-0.2 | 962 | 0.148 | 0.158 |
| 0.2-0.3 | 738 | 0.247 | 0.211 |
| 0.3-0.4 | 478 | 0.347 | 0.230 |
| 0.4-0.5 | 244 | 0.438 | 0.299 |
| 0.5-0.6 | 82 | 0.545 | 0.341 |
| 0.6-0.7 * | 28 | 0.639 | 0.571 |
| 0.7-0.8 * | 7 | 0.748 | 0.857 |
| 0.8-0.9 * | 3 | 0.833 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-03 | RNA | KTM | 0.85 | 63.2 | 598 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| VJ 985 | 2026-10-01 | VJC | PQC | 0.79 | 34.6 | 27 min |
| CX 302 | 2026-10-04 | CPA | PVG | 0.77 | 32.0 | 79 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 10 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (90%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| NH 814 | 2026-10-01 | ANA | HND | 0.04 | -3.6 | 25 min |
| OD 606 | 2026-10-03 | MXD | KUL | 0.77 | 60.0 | 7 min |
| LX 139 | 2026-10-01 | SWR | ZRH | 0.69 | 22.6 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3143 | 0.6618 | 0.1460 | 0.4583 | 13.8 | 2026-09-30T01:44:00+00:00 | 2026-10-07T16:46:35+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3143}
