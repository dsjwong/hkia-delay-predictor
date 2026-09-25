# Live evaluation — predictions vs actuals

Generated 2026-09-25T21:33:27+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2968**.

Dates 2026-09-19..2026-09-26; observed P(delay > 15) = 0.1543; median lead time between last score and departure = 131.9 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6626 | 0.1254 | 0.4116 | 11.574 |
| baseline_airline_hour | 0.6495 | 0.1423 | 0.4564 | 16.358 |
| naive_rate | 0.5 | 0.1305 | 0.4301 | 11.591 |

Coverage: **2968 of 3010** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2968 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0131 | [-0.0092, +0.0369] | no — CI straddles 0 |
| brier | -0.0169 | [-0.0204, -0.0134] | **yes** |
| logloss | -0.0448 | [-0.0552, -0.0341] | **yes** |
| mae | -4.78 | [-5.0815, -4.4738] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-19 † | 383 | 0.1567 | 0.6840 | 0.6287 | 0.1245 | 12.2 | 17.7 |
| 2026-09-20 | 423 | 0.1253 | 0.6765 | 0.6537 | 0.1082 | 11.8 | 17.2 |
| 2026-09-21 | 412 | 0.1311 | 0.5944 | 0.5875 | 0.1182 | 10.4 | 15.8 |
| 2026-09-22 | 410 | 0.1756 | 0.7213 | 0.6813 | 0.1305 | 11.7 | 16.7 |
| 2026-09-23 | 424 | 0.1392 | 0.6118 | 0.6791 | 0.1197 | 10.3 | 14.9 |
| 2026-09-24 | 429 | 0.1702 | 0.6566 | 0.6505 | 0.1362 | 12.3 | 16.8 |
| 2026-09-25 | 447 | 0.1790 | 0.7152 | 0.6696 | 0.1362 | 12.5 | 15.9 |
| 2026-09-26 *† | 40 | 0.1750 | 0.4004 | 0.6147 | 0.1622 | 9.9 | 13.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 116 | 0.7500 | 0.5822 | 0.5299 | 52.8 |
| < 30 min | 327 | 0.1621 | 0.6817 | 0.6477 | 11.4 |
| 30–120 min | 1016 | 0.1427 | 0.6603 | 0.6056 | 9.7 |
| 2–12 h | 1492 | 0.1160 | 0.6410 | 0.6373 | 9.7 |
| > 12 h * | 17 | 0.0000 | — | — | 5.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 782 | 0.064 | 0.082 |
| 0.1-0.2 | 1053 | 0.149 | 0.119 |
| 0.2-0.3 | 682 | 0.243 | 0.198 |
| 0.3-0.4 | 304 | 0.342 | 0.230 |
| 0.4-0.5 | 98 | 0.437 | 0.378 |
| 0.5-0.6 | 32 | 0.546 | 0.531 |
| 0.6-0.7 * | 14 | 0.637 | 0.571 |
| 0.7-0.8 * | 2 | 0.764 | 0.500 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-09-24 | VJC | PQC | 0.83 | 33.4 | 26 min |
| RA 410 | 2026-09-19 | RNA | KTM | 0.78 | 52.8 | 55 min |
| CX 520 | 2026-09-25 | CPA | NRT | 0.69 | 28.4 | 40 min |
| VJ 877 | 2026-09-25 | VJC | SGN | 0.68 | 31.3 | 46 min |
| CX 506 | 2026-09-25 | CPA | KIX | 0.66 | 30.1 | 138 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 3 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (67%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| UO 604 | 2026-09-21 | HKE | PUS | 0.03 | -6.9 | 26 min |
| NH 814 | 2026-09-20 | ANA | HND | 0.04 | -4.3 | 149 min |
| LX 139 | 2026-09-24 | SWR | ZRH | 0.75 | 24.2 | 15 min |
| VJ 985 | 2026-09-19 | VJC | PQC | 0.70 | 34.0 | 0 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2968 | 0.6626 | 0.1254 | 0.4116 | 11.6 | 2026-09-18T15:21:47+00:00 | 2026-09-25T18:00:46+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2968}
