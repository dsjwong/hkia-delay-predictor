# Live evaluation — predictions vs actuals

Generated 2026-09-02T21:01:36+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3022**.

Dates 2026-08-27..2026-09-03; observed P(delay > 15) = 0.2333; median lead time between last score and departure = 163.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6568 | 0.1818 | 0.5428 | 15.115 |
| baseline_airline_hour | 0.6285 | 0.1739 | 0.5282 | 16.848 |
| naive_rate | 0.5 | 0.1789 | 0.5432 | 14.017 |

Coverage: **3022 of 3062** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3022 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0283 | [+0.0048, +0.0515] | **yes** |
| brier | +0.0079 | [+0.0028, +0.0125] | no — CI straddles 0 |
| logloss | +0.0146 | [+0.0029, +0.0261] | no — CI straddles 0 |
| mae | -1.73 | [-2.0196, -1.4339] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-27 † | 392 | 0.4107 | 0.5908 | 0.6456 | 0.2564 | 20.3 | 17.7 |
| 2026-08-28 | 449 | 0.1893 | 0.6133 | 0.6065 | 0.1714 | 15.1 | 16.7 |
| 2026-08-29 | 444 | 0.2297 | 0.7014 | 0.6879 | 0.1579 | 14.1 | 17.1 |
| 2026-08-30 | 451 | 0.2705 | 0.6491 | 0.6333 | 0.1863 | 14.9 | 17.6 |
| 2026-08-31 | 442 | 0.1991 | 0.6230 | 0.5766 | 0.1751 | 14.8 | 16.9 |
| 2026-09-01 | 403 | 0.1737 | 0.5722 | 0.6105 | 0.1938 | 15.2 | 15.6 |
| 2026-09-02 | 405 | 0.1802 | 0.6607 | 0.6256 | 0.1432 | 12.3 | 16.6 |
| 2026-09-03 *† | 36 | 0.1111 | 0.5547 | 0.4688 | 0.1161 | 9.0 | 12.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 105 | 0.7524 | 0.6020 | 0.5898 | 46.9 |
| < 30 min | 296 | 0.1892 | 0.7154 | 0.6596 | 13.1 |
| 30–120 min | 863 | 0.2514 | 0.6575 | 0.5964 | 13.2 |
| 2–12 h | 1732 | 0.2015 | 0.6548 | 0.6328 | 14.5 |
| > 12 h * | 26 | 0.1538 | 0.7159 | 0.6761 | 13.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 251 | 0.069 | 0.084 |
| 0.1-0.2 | 639 | 0.152 | 0.142 |
| 0.2-0.3 | 638 | 0.250 | 0.183 |
| 0.3-0.4 | 527 | 0.349 | 0.275 |
| 0.4-0.5 | 468 | 0.446 | 0.284 |
| 0.5-0.6 | 252 | 0.544 | 0.345 |
| 0.6-0.7 | 192 | 0.645 | 0.432 |
| 0.7-0.8 | 47 | 0.734 | 0.447 |
| 0.8-0.9 * | 8 | 0.838 | 0.875 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |
| LX 139 | 2026-08-29 | SWR | ZRH | 0.85 | 31.3 | 39 min |
| OD 606 | 2026-08-27 | MXD | KUL | 0.84 | 73.2 | 30 min |
| VJ 877 | 2026-08-27 | VJC | SGN | 0.81 | 44.6 | 23 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 55 calls published at P ≥ 70%**, 28 were actually more than 15 minutes late (51%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2006 | 2026-09-02 | KAL | ICN | 0.04 | -0.5 | 23 min |
| UO 746 | 2026-08-30 | HKE | PEN | 0.05 | -1.2 | 21 min |
| TW 644 | 2026-09-01 | TWB | ICN | 0.06 | 0.7 | 22 min |
| VJ 985 | 2026-08-27 | VJC | PQC | 0.86 | 41.7 | 10 min |
| TG 601 | 2026-08-27 | THA | BKK | 0.79 | 46.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3022 | 0.6568 | 0.1818 | 0.5428 | 15.1 | 2026-08-26T20:19:28+00:00 | 2026-09-02T17:31:01+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3022}
