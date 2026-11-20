# Live evaluation — predictions vs actuals

Generated 2026-11-20T00:35:55+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2848**.

Dates 2026-11-13..2026-11-20; observed P(delay > 15) = 0.1699; median lead time between last score and departure = 228.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6134 | 0.1415 | 0.4549 | 13.165 |
| baseline_airline_hour | 0.5789 | 0.1533 | 0.4852 | 16.801 |
| naive_rate | 0.5 | 0.1411 | 0.4558 | 12.37 |

Coverage: **2848 of 2915** departures in the window (97.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2848 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0345 | [+0.0071, +0.0638] | **yes** |
| brier | -0.0118 | [-0.0152, -0.0084] | **yes** |
| logloss | -0.0303 | [-0.0400, -0.0205] | **yes** |
| mae | -3.64 | [-3.9138, -3.3360] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-13 † | 349 | 0.1461 | 0.5731 | 0.6710 | 0.1297 | 10.1 | 14.9 |
| 2026-11-14 | 416 | 0.1659 | 0.6539 | 0.5838 | 0.1521 | 15.9 | 17.4 |
| 2026-11-15 | 418 | 0.1890 | 0.6041 | 0.5398 | 0.1556 | 13.5 | 16.9 |
| 2026-11-16 | 412 | 0.1505 | 0.6417 | 0.5768 | 0.1226 | 12.9 | 17.6 |
| 2026-11-17 | 398 | 0.1734 | 0.5931 | 0.5729 | 0.1400 | 13.8 | 18.8 |
| 2026-11-18 | 409 | 0.2152 | 0.6962 | 0.6021 | 0.1520 | 12.7 | 16.2 |
| 2026-11-19 | 406 | 0.1478 | 0.5617 | 0.5381 | 0.1366 | 12.7 | 15.8 |
| 2026-11-20 *† | 40 | 0.1500 | 0.4412 | 0.6961 | 0.1378 | 13.9 | 15.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 69 | 0.6522 | 0.5491 | 0.4639 | 56.1 |
| < 30 min | 187 | 0.1765 | 0.7212 | 0.5801 | 16.7 |
| 30–120 min | 565 | 0.1735 | 0.6377 | 0.6306 | 13.2 |
| 2–12 h | 1923 | 0.1539 | 0.6001 | 0.5580 | 11.5 |
| > 12 h | 104 | 0.1154 | 0.5824 | 0.5983 | 9.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 413 | 0.074 | 0.102 |
| 0.1-0.2 | 988 | 0.151 | 0.151 |
| 0.2-0.3 | 792 | 0.243 | 0.139 |
| 0.3-0.4 | 438 | 0.346 | 0.244 |
| 0.4-0.5 | 152 | 0.441 | 0.270 |
| 0.5-0.6 | 42 | 0.543 | 0.524 |
| 0.6-0.7 * | 16 | 0.625 | 0.500 |
| 0.7-0.8 * | 5 | 0.749 | 0.600 |
| 0.8-0.9 * | 1 | 0.854 | 1.000 |
| 0.9-1.0 * | 1 | 0.912 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-14 | RNA | KTM | 0.91 | 55.8 | 83 min |
| RA 410 | 2026-11-17 | RNA | KTM | 0.85 | 47.8 | 188 min |
| LX 139 | 2026-11-14 | SWR | ZRH | 0.79 | 32.6 | 30 min |
| VJ 985 | 2026-11-14 | VJC | PQC | 0.74 | 34.4 | 219 min |
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 7 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (71%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CZ 356 | 2026-11-17 | CSN | PKX | 0.04 | -5.7 | 23 min |
| CA 110 | 2026-11-17 | CCA | PEK | 0.05 | -3.1 | 87 min |
| KE 2002 | 2026-11-19 | KAL | ICN | 0.06 | 4.7 | 20 min |
| LX 139 | 2026-11-15 | SWR | ZRH | 0.74 | 31.0 | 8 min |
| QF 128 | 2026-11-14 | QFA | SYD | 0.73 | 30.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2848 | 0.6134 | 0.1415 | 0.4549 | 13.2 | 2026-11-12T17:12:32+00:00 | 2026-11-19T17:28:55+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2848}
