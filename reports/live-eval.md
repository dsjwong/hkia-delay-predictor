# Live evaluation — predictions vs actuals

Generated 2026-09-27T21:19:25+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2999**.

Dates 2026-09-21..2026-09-28; observed P(delay > 15) = 0.1791; median lead time between last score and departure = 136.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6838 | 0.1376 | 0.4393 | 12.387 |
| baseline_airline_hour | 0.6535 | 0.1504 | 0.4742 | 16.52 |
| naive_rate | 0.5 | 0.147 | 0.47 | 12.404 |

Coverage: **2999 of 3040** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2999 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0303 | [+0.0082, +0.0517] | **yes** |
| brier | -0.0128 | [-0.0161, -0.0096] | **yes** |
| logloss | -0.0349 | [-0.0446, -0.0256] | **yes** |
| mae | -4.13 | [-4.4514, -3.8409] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-21 † | 372 | 0.1183 | 0.6452 | 0.6268 | 0.1073 | 10.1 | 16.1 |
| 2026-09-22 | 410 | 0.1756 | 0.7213 | 0.6813 | 0.1305 | 11.7 | 16.7 |
| 2026-09-23 | 424 | 0.1392 | 0.6118 | 0.6791 | 0.1197 | 10.3 | 14.9 |
| 2026-09-24 | 429 | 0.1702 | 0.6566 | 0.6505 | 0.1362 | 12.3 | 16.8 |
| 2026-09-25 | 447 | 0.1790 | 0.7152 | 0.6696 | 0.1362 | 12.5 | 15.9 |
| 2026-09-26 | 436 | 0.2271 | 0.6941 | 0.6609 | 0.1595 | 13.6 | 17.2 |
| 2026-09-27 | 441 | 0.2336 | 0.6558 | 0.6288 | 0.1685 | 15.8 | 18.3 |
| 2026-09-28 *† | 40 | 0.1750 | 0.7381 | 0.6710 | 0.1313 | 11.4 | 13.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 118 | 0.7712 | 0.6142 | 0.5706 | 56.5 |
| < 30 min | 297 | 0.1515 | 0.6679 | 0.6574 | 11.6 |
| 30–120 min | 995 | 0.1930 | 0.7112 | 0.6423 | 10.8 |
| 2–12 h | 1566 | 0.1335 | 0.6598 | 0.6313 | 10.3 |
| > 12 h * | 23 | 0.0000 | — | — | 6.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 687 | 0.066 | 0.077 |
| 0.1-0.2 | 966 | 0.149 | 0.128 |
| 0.2-0.3 | 708 | 0.245 | 0.213 |
| 0.3-0.4 | 390 | 0.345 | 0.269 |
| 0.4-0.5 | 165 | 0.439 | 0.327 |
| 0.5-0.6 | 56 | 0.542 | 0.518 |
| 0.6-0.7 * | 21 | 0.646 | 0.810 |
| 0.7-0.8 * | 3 | 0.737 | 0.333 |
| 0.8-0.9 * | 3 | 0.836 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-27 | SWR | ZRH | 0.85 | 31.7 | 38 min |
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| VJ 985 | 2026-09-26 | VJC | PQC | 0.82 | 38.0 | 78 min |
| VJ 877 | 2026-09-27 | VJC | SGN | 0.76 | 34.7 | 37 min |
| CX 520 | 2026-09-25 | CPA | NRT | 0.69 | 28.4 | 40 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 6 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (67%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| CA 420 | 2026-09-23 | CCA | CKG | 0.04 | -3.5 | 18 min |
| CA 764 | 2026-09-21 | CCA | PKX | 0.04 | -6.4 | 45 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| OD 606 | 2026-09-26 | MXD | KUL | 0.70 | 60.1 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2999 | 0.6838 | 0.1376 | 0.4393 | 12.4 | 2026-09-20T19:10:03+00:00 | 2026-09-27T15:42:49+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2999}
