# Live evaluation — predictions vs actuals

Generated 2026-08-31T22:49:19+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3088**.

Dates 2026-08-25..2026-09-01; observed P(delay > 15) = 0.2662; median lead time between last score and departure = 108.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6658 | 0.188 | 0.5609 | 15.757 |
| baseline_airline_hour | 0.6102 | 0.1892 | 0.5649 | 17.43 |
| naive_rate | 0.5 | 0.1953 | 0.5794 | 15.444 |

Coverage: **3088 of 3126** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3088 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0556 | [+0.0336, +0.0771] | **yes** |
| brier | -0.0012 | [-0.0062, +0.0037] | no — CI straddles 0 |
| logloss | -0.0040 | [-0.0158, +0.0077] | no — CI straddles 0 |
| mae | -1.67 | [-1.9474, -1.3911] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-25 † | 396 | 0.2348 | 0.5536 | 0.5532 | 0.1840 | 14.8 | 17.4 |
| 2026-08-26 | 438 | 0.3196 | 0.7291 | 0.6087 | 0.1844 | 16.4 | 18.3 |
| 2026-08-27 | 432 | 0.4306 | 0.5638 | 0.6145 | 0.2611 | 20.7 | 18.3 |
| 2026-08-28 | 449 | 0.1893 | 0.6133 | 0.6065 | 0.1714 | 15.1 | 16.7 |
| 2026-08-29 | 444 | 0.2297 | 0.7014 | 0.6879 | 0.1579 | 14.1 | 17.1 |
| 2026-08-30 | 451 | 0.2705 | 0.6491 | 0.6333 | 0.1863 | 14.9 | 17.6 |
| 2026-08-31 | 442 | 0.1991 | 0.6230 | 0.5766 | 0.1751 | 14.8 | 16.9 |
| 2026-09-01 *† | 36 | 0.1667 | 0.6472 | 0.4500 | 0.1552 | 11.2 | 13.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 255 | 0.7686 | 0.6007 | 0.5866 | 36.4 |
| < 30 min | 519 | 0.2119 | 0.6645 | 0.5993 | 13.4 |
| 30–120 min | 959 | 0.2336 | 0.6707 | 0.5692 | 13.1 |
| 2–12 h | 1331 | 0.2164 | 0.6760 | 0.6370 | 14.7 |
| > 12 h * | 24 | 0.1667 | 0.6875 | 0.6438 | 14.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 219 | 0.071 | 0.128 |
| 0.1-0.2 | 643 | 0.151 | 0.159 |
| 0.2-0.3 | 630 | 0.250 | 0.208 |
| 0.3-0.4 | 584 | 0.348 | 0.257 |
| 0.4-0.5 | 478 | 0.445 | 0.322 |
| 0.5-0.6 | 268 | 0.544 | 0.418 |
| 0.6-0.7 | 191 | 0.645 | 0.508 |
| 0.7-0.8 | 62 | 0.735 | 0.581 |
| 0.8-0.9 * | 13 | 0.837 | 0.923 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |
| LX 139 | 2026-08-29 | SWR | ZRH | 0.85 | 31.3 | 39 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 75 calls published at P ≥ 70%**, 48 were actually more than 15 minutes late (64%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-08-26 | JNA | CJU | 0.03 | -0.5 | 24 min |
| TW 640 | 2026-08-27 | TWB | PUS | 0.04 | -1.5 | 26 min |
| OZ 746 | 2026-08-26 | AAR | ICN | 0.04 | -0.6 | 24 min |
| VJ 985 | 2026-08-27 | VJC | PQC | 0.86 | 41.7 | 10 min |
| TG 601 | 2026-08-27 | THA | BKK | 0.79 | 46.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 2e00760@2026-08-16T16:13:29+00:00 | 281 | 0.5163 | 0.1769 | 0.5417 | 13.1 | 2026-08-24T19:51:51+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 2807 | 0.6740 | 0.1891 | 0.5628 | 16.0 | 2026-08-25T09:38:36+00:00 | 2026-08-31T14:33:09+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 281, '4a4212f@2026-08-25T09:35:34+00:00': 2807}
