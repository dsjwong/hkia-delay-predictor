# Live evaluation — predictions vs actuals

Generated 2026-09-21T21:58:23+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2851**.

Dates 2026-09-15..2026-09-22; observed P(delay > 15) = 0.121; median lead time between last score and departure = 128.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6776 | 0.1052 | 0.3577 | 10.436 |
| baseline_airline_hour | 0.6462 | 0.1319 | 0.433 | 16.295 |
| naive_rate | 0.5 | 0.1064 | 0.3689 | 10.282 |

Coverage: **2851 of 2886** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2851 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0314 | [+0.0066, +0.0559] | **yes** |
| brier | -0.0267 | [-0.0301, -0.0231] | **yes** |
| logloss | -0.0753 | [-0.0856, -0.0646] | **yes** |
| mae | -5.86 | [-6.1801, -5.5236] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-15 † | 351 | 0.0826 | 0.6472 | 0.5993 | 0.0907 | 9.8 | 16.7 |
| 2026-09-16 | 389 | 0.1260 | 0.7551 | 0.6831 | 0.1005 | 9.6 | 15.9 |
| 2026-09-17 | 399 | 0.1203 | 0.7270 | 0.6686 | 0.1020 | 11.0 | 17.1 |
| 2026-09-18 | 418 | 0.1148 | 0.6810 | 0.6624 | 0.1007 | 8.8 | 14.6 |
| 2026-09-19 | 424 | 0.1486 | 0.6913 | 0.6467 | 0.1193 | 11.9 | 17.1 |
| 2026-09-20 | 423 | 0.1253 | 0.6765 | 0.6537 | 0.1082 | 11.8 | 17.2 |
| 2026-09-21 | 412 | 0.1311 | 0.5944 | 0.5875 | 0.1182 | 10.4 | 15.8 |
| 2026-09-22 *† | 35 | 0.0286 | 0.8824 | 0.5588 | 0.0332 | 5.7 | 11.1 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 98 | 0.6633 | 0.5497 | 0.5671 | 46.0 |
| < 30 min | 308 | 0.1234 | 0.7044 | 0.5723 | 8.8 |
| 30–120 min | 1018 | 0.1041 | 0.6632 | 0.6319 | 9.2 |
| 2–12 h | 1413 | 0.0962 | 0.6709 | 0.6545 | 9.3 |
| > 12 h * | 14 | 0.0000 | — | — | 4.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 860 | 0.062 | 0.053 |
| 0.1-0.2 | 1041 | 0.147 | 0.101 |
| 0.2-0.3 | 636 | 0.245 | 0.182 |
| 0.3-0.4 | 233 | 0.340 | 0.219 |
| 0.4-0.5 | 58 | 0.438 | 0.310 |
| 0.5-0.6 * | 16 | 0.546 | 0.438 |
| 0.6-0.7 * | 5 | 0.643 | 0.200 |
| 0.7-0.8 * | 2 | 0.742 | 0.500 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-09-19 | RNA | KTM | 0.78 | 52.8 | 55 min |
| CX 520 | 2026-09-20 | CPA | NRT | 0.60 | 25.4 | 62 min |
| VJ 985 | 2026-09-17 | VJC | PQC | 0.59 | 26.1 | 20 min |
| LX 139 | 2026-09-20 | SWR | ZRH | 0.58 | 19.8 | 20 min |
| OD 606 | 2026-09-18 | MXD | KUL | 0.55 | 44.8 | 43 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-09-18 | JNA | CJU | 0.03 | -1.2 | 20 min |
| EK 381 | 2026-09-16 | UAE | DXB | 0.03 | -1.1 | 18 min |
| UO 604 | 2026-09-21 | HKE | PUS | 0.03 | -6.9 | 26 min |
| VJ 985 | 2026-09-15 | VJC | PQC | 0.71 | 30.3 | -6 min |
| VJ 985 | 2026-09-19 | VJC | PQC | 0.70 | 34.0 | 0 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2851 | 0.6776 | 0.1052 | 0.3577 | 10.4 | 2026-09-14T18:48:10+00:00 | 2026-09-21T15:12:21+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2851}
