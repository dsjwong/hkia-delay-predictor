# Live evaluation — predictions vs actuals

Generated 2026-11-28T01:26:17+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2891**.

Dates 2026-11-21..2026-11-28; observed P(delay > 15) = 0.1671; median lead time between last score and departure = 225.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6472 | 0.1372 | 0.44 | 12.184 |
| baseline_airline_hour | 0.6212 | 0.1471 | 0.4692 | 14.915 |
| naive_rate | 0.5 | 0.1392 | 0.4512 | 11.003 |

Coverage: **2891 of 3005** departures in the window (96.2%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2891 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0260 | [+0.0003, +0.0516] | **yes** |
| brier | -0.0099 | [-0.0130, -0.0066] | **yes** |
| logloss | -0.0292 | [-0.0378, -0.0197] | **yes** |
| mae | -2.73 | [-2.9896, -2.4727] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-21 † | 316 | 0.1614 | 0.6321 | 0.6162 | 0.1515 | 14.1 | 16.9 |
| 2026-11-22 | 427 | 0.1358 | 0.6490 | 0.5757 | 0.1155 | 10.5 | 14.7 |
| 2026-11-23 | 425 | 0.1412 | 0.6263 | 0.6116 | 0.1223 | 11.1 | 15.6 |
| 2026-11-24 | 404 | 0.1634 | 0.6589 | 0.5917 | 0.1365 | 12.9 | 15.2 |
| 2026-11-25 | 411 | 0.1411 | 0.7359 | 0.6809 | 0.1116 | 9.6 | 13.4 |
| 2026-11-26 | 410 | 0.2220 | 0.5964 | 0.6257 | 0.1740 | 15.8 | 15.6 |
| 2026-11-27 | 432 | 0.2060 | 0.6630 | 0.6596 | 0.1534 | 12.5 | 14.5 |
| 2026-11-28 *† | 66 | 0.1515 | 0.5875 | 0.5536 | 0.1329 | 7.5 | 8.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 46 | 0.7609 | 0.5766 | 0.6883 | 52.4 |
| < 30 min | 183 | 0.1639 | 0.6801 | 0.6117 | 11.3 |
| 30–120 min | 611 | 0.1751 | 0.6640 | 0.6168 | 11.2 |
| 2–12 h | 1970 | 0.1528 | 0.6350 | 0.6197 | 11.8 |
| > 12 h * | 81 | 0.1235 | 0.8056 | 0.6662 | 7.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 539 | 0.068 | 0.078 |
| 0.1-0.2 | 943 | 0.151 | 0.137 |
| 0.2-0.3 | 825 | 0.246 | 0.182 |
| 0.3-0.4 | 382 | 0.342 | 0.236 |
| 0.4-0.5 | 126 | 0.434 | 0.310 |
| 0.5-0.6 | 46 | 0.538 | 0.370 |
| 0.6-0.7 * | 22 | 0.631 | 0.455 |
| 0.7-0.8 * | 5 | 0.734 | 1.000 |
| 0.8-0.9 * | 2 | 0.828 | 0.500 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-11-26 | VJC | PQC | 0.80 | 44.7 | 101 min |
| QF 128 | 2026-11-26 | QFA | SYD | 0.75 | 32.4 | 26 min |
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| K6 681 | 2026-11-27 | KHV | KTI | 0.74 | 32.4 | 27 min |
| VJ 877 | 2026-11-26 | VJC | SGN | 0.73 | 42.6 | 19 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 8 calls published at P ≥ 70%**, 6 were actually more than 15 minutes late (75%).

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
| e2c2178@2026-11-22T11:25:36+00:00 | 2108 | 0.6508 | 0.1410 | 0.4487 | 12.4 | 2026-11-22T17:57:19+00:00 | 2026-11-27T16:52:07+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 783 | 0.6525 | 0.1267 | 0.4167 | 11.7 | 2026-11-20T21:37:30+00:00 | 2026-11-22T10:28:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'e2c2178@2026-11-22T11:25:36+00:00': 2108, 'f6ae66c@2026-11-01T10:28:21+00:00': 783}
