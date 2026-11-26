# Live evaluation — predictions vs actuals

Generated 2026-11-26T01:46:25+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2849**.

Dates 2026-11-19..2026-11-26; observed P(delay > 15) = 0.1657; median lead time between last score and departure = 221.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6317 | 0.1397 | 0.4476 | 12.063 |
| baseline_airline_hour | 0.5806 | 0.1506 | 0.4787 | 14.967 |
| naive_rate | 0.5 | 0.1382 | 0.449 | 10.868 |

Coverage: **2849 of 2964** departures in the window (96.1%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2849 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0511 | [+0.0226, +0.0783] | **yes** |
| brier | -0.0109 | [-0.0139, -0.0077] | **yes** |
| logloss | -0.0311 | [-0.0394, -0.0222] | **yes** |
| mae | -2.90 | [-3.1642, -2.6610] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-19 † | 291 | 0.1753 | 0.5697 | 0.5029 | 0.1499 | 13.7 | 16.0 |
| 2026-11-20 | 424 | 0.2476 | 0.5754 | 0.5410 | 0.1892 | 14.3 | 15.3 |
| 2026-11-21 | 430 | 0.1605 | 0.5796 | 0.5807 | 0.1561 | 13.0 | 15.2 |
| 2026-11-22 | 427 | 0.1358 | 0.6490 | 0.5757 | 0.1155 | 10.5 | 14.7 |
| 2026-11-23 | 425 | 0.1412 | 0.6263 | 0.6116 | 0.1223 | 11.1 | 15.6 |
| 2026-11-24 | 404 | 0.1634 | 0.6589 | 0.5917 | 0.1365 | 12.9 | 15.2 |
| 2026-11-25 | 411 | 0.1411 | 0.7359 | 0.6809 | 0.1116 | 9.6 | 13.4 |
| 2026-11-26 *† | 37 | 0.1351 | 0.4250 | 0.3781 | 0.1314 | 8.3 | 10.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 46 | 0.6957 | 0.7344 | 0.6730 | 49.7 |
| < 30 min | 160 | 0.1750 | 0.6364 | 0.5664 | 12.1 |
| 30–120 min | 577 | 0.1872 | 0.6096 | 0.5454 | 12.1 |
| 2–12 h | 1978 | 0.1476 | 0.6294 | 0.5844 | 11.3 |
| > 12 h * | 88 | 0.1364 | 0.7664 | 0.6190 | 8.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 439 | 0.068 | 0.077 |
| 0.1-0.2 | 891 | 0.152 | 0.139 |
| 0.2-0.3 | 822 | 0.247 | 0.165 |
| 0.3-0.4 | 455 | 0.343 | 0.218 |
| 0.4-0.5 | 176 | 0.436 | 0.295 |
| 0.5-0.6 | 50 | 0.540 | 0.380 |
| 0.6-0.7 * | 12 | 0.626 | 0.500 |
| 0.7-0.8 * | 2 | 0.741 | 1.000 |
| 0.8-0.9 * | 1 | 0.855 | 0.000 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |
| VJ 877 | 2026-11-21 | VJC | SGN | 0.67 | 35.5 | 90 min |
| VJ 877 | 2026-11-24 | VJC | SGN | 0.62 | 29.0 | 45 min |
| VN 593 | 2026-11-20 | HVN | HAN | 0.62 | 24.7 | 49 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 794 | 2026-11-23 | CCA | HGH | 0.04 | 3.9 | 27 min |
| GA 873 | 2026-11-25 | GIA | CGK | 0.04 | 3.7 | 18 min |
| CA 412 | 2026-11-24 | CCA | TFU | 0.04 | 2.6 | 23 min |
| RA 410 | 2026-11-21 | RNA | KTM | 0.91 | 54.4 | 12 min |
| RA 410 | 2026-11-25 | RNA | KTM | 0.85 | 50.9 | -7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| e2c2178@2026-11-22T11:25:36+00:00 | 1237 | 0.6547 | 0.1260 | 0.4114 | 11.3 | 2026-11-22T17:57:19+00:00 | 2026-11-25T14:43:10+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 1612 | 0.6139 | 0.1503 | 0.4754 | 12.6 | 2026-11-18T18:15:36+00:00 | 2026-11-22T10:28:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'e2c2178@2026-11-22T11:25:36+00:00': 1237, 'f6ae66c@2026-11-01T10:28:21+00:00': 1612}
