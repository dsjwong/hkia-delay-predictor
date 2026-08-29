# Live evaluation — predictions vs actuals

Generated 2026-08-29T01:45:33+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3032**.

Dates 2026-08-22..2026-08-29; observed P(delay > 15) = 0.2794; median lead time between last score and departure = 61.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6483 | 0.1941 | 0.5776 | 16.056 |
| baseline_airline_hour | 0.6098 | 0.1948 | 0.5776 | 17.63 |
| naive_rate | 0.5 | 0.2013 | 0.5923 | 15.953 |

Coverage: **3032 of 3152** departures in the window (96.2%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3032 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0385 | [+0.0167, +0.0606] | **yes** |
| brier | -0.0007 | [-0.0056, +0.0043] | no — CI straddles 0 |
| logloss | +0.0000 | [-0.0122, +0.0123] | no — CI straddles 0 |
| mae | -1.57 | [-1.8726, -1.2779] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-22 † | 331 | 0.4441 | 0.5860 | 0.6478 | 0.2606 | 21.4 | 21.2 |
| 2026-08-23 | 452 | 0.2146 | 0.6040 | 0.6199 | 0.1661 | 13.5 | 16.7 |
| 2026-08-24 | 452 | 0.1947 | 0.5243 | 0.5938 | 0.1621 | 12.8 | 16.2 |
| 2026-08-25 | 434 | 0.2258 | 0.5556 | 0.5614 | 0.1795 | 14.6 | 17.2 |
| 2026-08-26 | 438 | 0.3196 | 0.7291 | 0.6087 | 0.1844 | 16.4 | 18.3 |
| 2026-08-27 | 432 | 0.4306 | 0.5638 | 0.6145 | 0.2611 | 20.7 | 18.3 |
| 2026-08-28 | 449 | 0.1893 | 0.6133 | 0.6065 | 0.1714 | 15.1 | 16.7 |
| 2026-08-29 *† | 44 | 0.1364 | 0.7105 | 0.4627 | 0.1219 | 11.9 | 15.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 371 | 0.7332 | 0.5815 | 0.5801 | 31.2 |
| < 30 min | 803 | 0.2391 | 0.6171 | 0.5873 | 14.0 |
| 30–120 min | 1032 | 0.1957 | 0.6780 | 0.5926 | 12.1 |
| 2–12 h | 808 | 0.2191 | 0.6813 | 0.6328 | 16.1 |
| > 12 h * | 18 | 0.2222 | 0.7143 | 0.7232 | 17.1 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 243 | 0.071 | 0.156 |
| 0.1-0.2 | 682 | 0.154 | 0.185 |
| 0.2-0.3 | 743 | 0.249 | 0.237 |
| 0.3-0.4 | 491 | 0.346 | 0.271 |
| 0.4-0.5 | 355 | 0.448 | 0.341 |
| 0.5-0.6 | 249 | 0.545 | 0.442 |
| 0.6-0.7 | 193 | 0.644 | 0.487 |
| 0.7-0.8 | 59 | 0.734 | 0.576 |
| 0.8-0.9 * | 17 | 0.836 | 0.882 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 76 calls published at P ≥ 70%**, 49 were actually more than 15 minutes late (64%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-08-26 | JNA | CJU | 0.03 | -0.5 | 24 min |
| CA 412 | 2026-08-24 | CCA | TFU | 0.03 | -7.0 | 26 min |
| TW 640 | 2026-08-27 | TWB | PUS | 0.04 | -1.5 | 26 min |
| VJ 985 | 2026-08-27 | VJC | PQC | 0.86 | 41.7 | 10 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 2e00760@2026-08-16T16:13:29+00:00 | 1554 | 0.6014 | 0.1862 | 0.5629 | 14.9 | 2026-08-21T23:45:34+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 1478 | 0.6823 | 0.2023 | 0.5931 | 17.3 | 2026-08-25T09:38:36+00:00 | 2026-08-28T13:01:33+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 1554, '4a4212f@2026-08-25T09:35:34+00:00': 1478}
