# Live evaluation — predictions vs actuals

Generated 2026-08-29T20:54:06+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3100**.

Dates 2026-08-23..2026-08-30; observed P(delay > 15) = 0.2587; median lead time between last score and departure = 79.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6578 | 0.1838 | 0.5541 | 15.316 |
| baseline_airline_hour | 0.6087 | 0.1863 | 0.5584 | 17.239 |
| naive_rate | 0.5 | 0.1918 | 0.5717 | 15.207 |

Coverage: **3100 of 3140** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3100 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0491 | [+0.0261, +0.0736] | **yes** |
| brier | -0.0025 | [-0.0077, +0.0024] | no — CI straddles 0 |
| logloss | -0.0043 | [-0.0169, +0.0077] | no — CI straddles 0 |
| mae | -1.92 | [-2.2391, -1.6287] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-23 † | 412 | 0.2184 | 0.6158 | 0.6331 | 0.1661 | 13.7 | 17.0 |
| 2026-08-24 | 452 | 0.1947 | 0.5243 | 0.5938 | 0.1621 | 12.8 | 16.2 |
| 2026-08-25 | 434 | 0.2258 | 0.5556 | 0.5614 | 0.1795 | 14.6 | 17.2 |
| 2026-08-26 | 438 | 0.3196 | 0.7291 | 0.6087 | 0.1844 | 16.4 | 18.3 |
| 2026-08-27 | 432 | 0.4306 | 0.5638 | 0.6145 | 0.2611 | 20.7 | 18.3 |
| 2026-08-28 | 449 | 0.1893 | 0.6133 | 0.6065 | 0.1714 | 15.1 | 16.7 |
| 2026-08-29 | 444 | 0.2297 | 0.7014 | 0.6879 | 0.1579 | 14.1 | 17.1 |
| 2026-08-30 *† | 39 | 0.3333 | 0.6361 | 0.5991 | 0.2451 | 14.2 | 15.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 309 | 0.7346 | 0.5833 | 0.5671 | 32.3 |
| < 30 min | 678 | 0.2109 | 0.6253 | 0.5869 | 13.5 |
| 30–120 min | 1062 | 0.1977 | 0.6620 | 0.5662 | 11.9 |
| 2–12 h | 1025 | 0.2127 | 0.6900 | 0.6523 | 15.0 |
| > 12 h * | 26 | 0.1538 | 0.7159 | 0.6761 | 13.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 281 | 0.071 | 0.146 |
| 0.1-0.2 | 746 | 0.152 | 0.172 |
| 0.2-0.3 | 734 | 0.249 | 0.206 |
| 0.3-0.4 | 496 | 0.346 | 0.240 |
| 0.4-0.5 | 350 | 0.445 | 0.349 |
| 0.5-0.6 | 235 | 0.545 | 0.430 |
| 0.6-0.7 | 186 | 0.644 | 0.500 |
| 0.7-0.8 | 57 | 0.736 | 0.579 |
| 0.8-0.9 * | 15 | 0.837 | 0.933 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 72 calls published at P ≥ 70%**, 47 were actually more than 15 minutes late (65%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-08-26 | JNA | CJU | 0.03 | -0.5 | 24 min |
| CA 412 | 2026-08-24 | CCA | TFU | 0.03 | -7.0 | 26 min |
| TW 640 | 2026-08-27 | TWB | PUS | 0.04 | -1.5 | 26 min |
| VJ 985 | 2026-08-27 | VJC | PQC | 0.86 | 41.7 | 10 min |
| TG 601 | 2026-08-27 | THA | BKK | 0.79 | 46.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 2e00760@2026-08-16T16:13:29+00:00 | 1183 | 0.5585 | 0.1660 | 0.5193 | 13.2 | 2026-08-22T19:14:58+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 1917 | 0.6827 | 0.1947 | 0.5756 | 16.6 | 2026-08-25T09:38:36+00:00 | 2026-08-29T15:41:39+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 1183, '4a4212f@2026-08-25T09:35:34+00:00': 1917}
