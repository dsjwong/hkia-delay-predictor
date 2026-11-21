# Live evaluation — predictions vs actuals

Generated 2026-11-21T23:11:52+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2895**.

Dates 2026-11-15..2026-11-22; observed P(delay > 15) = 0.1824; median lead time between last score and departure = 224.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6155 | 0.1495 | 0.4738 | 13.214 |
| baseline_airline_hour | 0.5669 | 0.1605 | 0.5018 | 16.6 |
| naive_rate | 0.5 | 0.1491 | 0.475 | 12.464 |

Coverage: **2895 of 2933** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2895 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0486 | [+0.0223, +0.0744] | **yes** |
| brier | -0.0110 | [-0.0143, -0.0079] | **yes** |
| logloss | -0.0280 | [-0.0368, -0.0194] | **yes** |
| mae | -3.39 | [-3.6538, -3.1232] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-15 † | 380 | 0.1816 | 0.6373 | 0.5806 | 0.1487 | 13.5 | 17.1 |
| 2026-11-16 | 412 | 0.1505 | 0.6417 | 0.5768 | 0.1226 | 12.9 | 17.6 |
| 2026-11-17 | 398 | 0.1734 | 0.5931 | 0.5729 | 0.1400 | 13.8 | 18.8 |
| 2026-11-18 | 409 | 0.2152 | 0.6962 | 0.6021 | 0.1520 | 12.7 | 16.2 |
| 2026-11-19 | 406 | 0.1478 | 0.5617 | 0.5381 | 0.1366 | 12.7 | 15.8 |
| 2026-11-20 | 424 | 0.2476 | 0.5754 | 0.5408 | 0.1892 | 14.3 | 15.8 |
| 2026-11-21 | 430 | 0.1605 | 0.5796 | 0.5694 | 0.1561 | 13.0 | 15.8 |
| 2026-11-22 *† | 36 | 0.1667 | 0.6500 | 0.5111 | 0.1389 | 7.7 | 9.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 67 | 0.7015 | 0.5777 | 0.5112 | 61.0 |
| < 30 min | 183 | 0.1585 | 0.6794 | 0.5675 | 14.4 |
| 30–120 min | 571 | 0.1874 | 0.6032 | 0.5655 | 13.6 |
| 2–12 h | 1984 | 0.1689 | 0.6193 | 0.5607 | 11.5 |
| > 12 h * | 90 | 0.1111 | 0.6138 | 0.6350 | 9.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 336 | 0.073 | 0.104 |
| 0.1-0.2 | 938 | 0.152 | 0.154 |
| 0.2-0.3 | 844 | 0.246 | 0.160 |
| 0.3-0.4 | 510 | 0.345 | 0.229 |
| 0.4-0.5 | 193 | 0.437 | 0.295 |
| 0.5-0.6 | 52 | 0.544 | 0.558 |
| 0.6-0.7 * | 17 | 0.630 | 0.471 |
| 0.7-0.8 * | 3 | 0.740 | 0.667 |
| 0.8-0.9 * | 1 | 0.854 | 1.000 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-17 | RNA | KTM | 0.85 | 47.8 | 188 min |
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |
| QF 128 | 2026-11-15 | QFA | SYD | 0.67 | 23.7 | 66 min |
| VJ 877 | 2026-11-21 | VJC | SGN | 0.67 | 35.5 | 90 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 5 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (60%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CZ 356 | 2026-11-17 | CSN | PKX | 0.04 | -5.7 | 23 min |
| CA 110 | 2026-11-17 | CCA | PEK | 0.05 | -3.1 | 87 min |
| KE 2002 | 2026-11-19 | KAL | ICN | 0.06 | 4.7 | 20 min |
| RA 410 | 2026-11-21 | RNA | KTM | 0.91 | 54.4 | 12 min |
| LX 139 | 2026-11-15 | SWR | ZRH | 0.74 | 31.0 | 8 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2895 | 0.6155 | 0.1495 | 0.4738 | 13.2 | 2026-11-14T12:21:40+00:00 | 2026-11-21T17:41:43+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2895}
