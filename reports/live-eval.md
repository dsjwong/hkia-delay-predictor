# Live evaluation — predictions vs actuals

Generated 2026-08-30T21:02:59+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3099**.

Dates 2026-08-24..2026-08-31; observed P(delay > 15) = 0.2678; median lead time between last score and departure = 92.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6596 | 0.1875 | 0.5627 | 15.637 |
| baseline_airline_hour | 0.6087 | 0.1897 | 0.5661 | 17.461 |
| naive_rate | 0.5 | 0.1961 | 0.5811 | 15.561 |

Coverage: **3099 of 3143** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3099 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0509 | [+0.0291, +0.0731] | **yes** |
| brier | -0.0022 | [-0.0068, +0.0030] | no — CI straddles 0 |
| logloss | -0.0034 | [-0.0150, +0.0092] | no — CI straddles 0 |
| mae | -1.82 | [-2.1207, -1.5191] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-24 † | 408 | 0.2108 | 0.5070 | 0.5693 | 0.1736 | 13.6 | 17.1 |
| 2026-08-25 | 434 | 0.2258 | 0.5556 | 0.5614 | 0.1795 | 14.6 | 17.2 |
| 2026-08-26 | 438 | 0.3196 | 0.7291 | 0.6087 | 0.1844 | 16.4 | 18.3 |
| 2026-08-27 | 432 | 0.4306 | 0.5638 | 0.6145 | 0.2611 | 20.7 | 18.3 |
| 2026-08-28 | 449 | 0.1893 | 0.6133 | 0.6065 | 0.1714 | 15.1 | 16.7 |
| 2026-08-29 | 444 | 0.2297 | 0.7014 | 0.6879 | 0.1579 | 14.1 | 17.1 |
| 2026-08-30 | 451 | 0.2705 | 0.6491 | 0.6333 | 0.1863 | 14.9 | 17.6 |
| 2026-08-31 *† | 43 | 0.2558 | 0.6974 | 0.6179 | 0.1785 | 16.9 | 16.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 281 | 0.7616 | 0.5924 | 0.5844 | 35.1 |
| < 30 min | 608 | 0.2105 | 0.6487 | 0.6071 | 13.3 |
| 30–120 min | 1023 | 0.2190 | 0.6716 | 0.5581 | 12.2 |
| 2–12 h | 1163 | 0.2236 | 0.6701 | 0.6386 | 15.2 |
| > 12 h * | 24 | 0.1667 | 0.6875 | 0.6438 | 14.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 279 | 0.071 | 0.161 |
| 0.1-0.2 | 712 | 0.150 | 0.164 |
| 0.2-0.3 | 676 | 0.249 | 0.216 |
| 0.3-0.4 | 536 | 0.347 | 0.256 |
| 0.4-0.5 | 391 | 0.445 | 0.348 |
| 0.5-0.6 | 242 | 0.546 | 0.430 |
| 0.6-0.7 | 189 | 0.644 | 0.508 |
| 0.7-0.8 | 60 | 0.734 | 0.600 |
| 0.8-0.9 * | 14 | 0.839 | 0.929 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 74 calls published at P ≥ 70%**, 49 were actually more than 15 minutes late (66%).

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
| 2e00760@2026-08-16T16:13:29+00:00 | 727 | 0.5149 | 0.1727 | 0.5412 | 13.3 | 2026-08-23T16:48:40+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 2372 | 0.6804 | 0.1920 | 0.5693 | 16.3 | 2026-08-25T09:38:36+00:00 | 2026-08-30T17:50:06+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 727, '4a4212f@2026-08-25T09:35:34+00:00': 2372}
