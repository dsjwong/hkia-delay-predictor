# Live evaluation — predictions vs actuals

Generated 2026-10-28T22:32:24+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2951**.

Dates 2026-10-22..2026-10-29; observed P(delay > 15) = 0.1806; median lead time between last score and departure = 151.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6693 | 0.14 | 0.4464 | 13.773 |
| baseline_airline_hour | 0.6201 | 0.1558 | 0.4922 | 18.325 |
| naive_rate | 0.5 | 0.148 | 0.4723 | 13.892 |

Coverage: **2951 of 2990** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2951 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0492 | [+0.0272, +0.0717] | **yes** |
| brier | -0.0158 | [-0.0191, -0.0125] | **yes** |
| logloss | -0.0458 | [-0.0582, -0.0347] | **yes** |
| mae | -4.55 | [-4.8810, -4.2286] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-22 † | 382 | 0.2827 | 0.6554 | 0.6314 | 0.1922 | 19.7 | 22.0 |
| 2026-10-23 | 396 | 0.1919 | 0.6007 | 0.5620 | 0.1556 | 14.8 | 18.4 |
| 2026-10-24 | 429 | 0.2191 | 0.6541 | 0.6057 | 0.1625 | 17.3 | 20.7 |
| 2026-10-25 | 439 | 0.1868 | 0.6740 | 0.6543 | 0.1432 | 15.4 | 19.2 |
| 2026-10-26 | 430 | 0.1419 | 0.6094 | 0.6095 | 0.1206 | 11.3 | 16.8 |
| 2026-10-27 | 419 | 0.1527 | 0.6685 | 0.6124 | 0.1243 | 9.6 | 15.5 |
| 2026-10-28 | 419 | 0.1098 | 0.7070 | 0.6791 | 0.0928 | 9.4 | 16.5 |
| 2026-10-29 *† | 37 | 0.0541 | 0.0143 | 0.0000 | 0.0704 | 6.7 | 13.1 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 93 | 0.6989 | 0.6137 | 0.4959 | 60.7 |
| < 30 min | 280 | 0.1714 | 0.8049 | 0.7357 | 13.3 |
| 30–120 min | 924 | 0.1786 | 0.6708 | 0.5923 | 13.4 |
| 2–12 h | 1613 | 0.1562 | 0.6292 | 0.6010 | 11.5 |
| > 12 h * | 41 | 0.0732 | 0.5702 | 0.4605 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 682 | 0.068 | 0.070 |
| 0.1-0.2 | 1057 | 0.148 | 0.151 |
| 0.2-0.3 | 724 | 0.245 | 0.220 |
| 0.3-0.4 | 337 | 0.339 | 0.294 |
| 0.4-0.5 | 99 | 0.440 | 0.394 |
| 0.5-0.6 | 34 | 0.545 | 0.559 |
| 0.6-0.7 * | 10 | 0.655 | 0.500 |
| 0.7-0.8 * | 6 | 0.735 | 0.500 |
| 0.8-0.9 * | 2 | 0.854 | 0.500 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-10-22 | VJC | PQC | 0.84 | 42.4 | 33 min |
| VJ 985 | 2026-10-24 | VJC | PQC | 0.79 | 43.9 | 22 min |
| VJ 877 | 2026-10-23 | VJC | SGN | 0.72 | 34.3 | 34 min |
| JX 236 | 2026-10-22 | SJX | TPE | 0.71 | 41.6 | 51 min |
| VJ 877 | 2026-10-25 | VJC | SGN | 0.68 | 26.8 | 85 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 8 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-29 | KAL | ICN | 0.02 | -3.7 | 41 min |
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| CA 118 | 2026-10-27 | CCA | PEK | 0.03 | -2.9 | 19 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2951 | 0.6693 | 0.1400 | 0.4464 | 13.8 | 2026-10-21T05:30:13+00:00 | 2026-10-28T15:35:30+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2951}
