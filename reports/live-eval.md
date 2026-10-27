# Live evaluation — predictions vs actuals

Generated 2026-10-27T22:10:55+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2966**.

Dates 2026-10-21..2026-10-28; observed P(delay > 15) = 0.1898; median lead time between last score and departure = 144.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.664 | 0.1458 | 0.4605 | 13.939 |
| baseline_airline_hour | 0.6325 | 0.1577 | 0.4955 | 17.945 |
| naive_rate | 0.5 | 0.1538 | 0.486 | 14.017 |

Coverage: **2966 of 3003** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2966 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0315 | [+0.0108, +0.0522] | **yes** |
| brier | -0.0119 | [-0.0153, -0.0087] | **yes** |
| logloss | -0.0350 | [-0.0472, -0.0236] | **yes** |
| mae | -4.01 | [-4.3289, -3.6916] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-21 † | 396 | 0.1616 | 0.7113 | 0.7634 | 0.1272 | 10.6 | 14.3 |
| 2026-10-22 | 420 | 0.2810 | 0.6632 | 0.6445 | 0.1913 | 19.0 | 21.1 |
| 2026-10-23 | 396 | 0.1919 | 0.6007 | 0.5620 | 0.1556 | 14.8 | 18.4 |
| 2026-10-24 | 429 | 0.2191 | 0.6541 | 0.6057 | 0.1625 | 17.3 | 20.7 |
| 2026-10-25 | 439 | 0.1868 | 0.6740 | 0.6543 | 0.1432 | 15.4 | 19.2 |
| 2026-10-26 | 430 | 0.1419 | 0.6094 | 0.6095 | 0.1206 | 11.3 | 16.8 |
| 2026-10-27 | 419 | 0.1527 | 0.6685 | 0.6124 | 0.1243 | 9.6 | 15.5 |
| 2026-10-28 *† | 37 | 0.1081 | 0.7083 | 0.6288 | 0.0967 | 6.8 | 10.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 99 | 0.6869 | 0.6328 | 0.5413 | 57.8 |
| < 30 min | 299 | 0.1873 | 0.7974 | 0.7428 | 13.4 |
| 30–120 min | 966 | 0.1998 | 0.6567 | 0.6017 | 13.8 |
| 2–12 h | 1566 | 0.1545 | 0.6223 | 0.6077 | 11.5 |
| > 12 h * | 36 | 0.1111 | 0.6875 | 0.6328 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 633 | 0.068 | 0.073 |
| 0.1-0.2 | 989 | 0.148 | 0.160 |
| 0.2-0.3 | 765 | 0.247 | 0.213 |
| 0.3-0.4 | 398 | 0.340 | 0.291 |
| 0.4-0.5 | 120 | 0.440 | 0.400 |
| 0.5-0.6 | 41 | 0.545 | 0.512 |
| 0.6-0.7 * | 12 | 0.650 | 0.583 |
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
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| CA 118 | 2026-10-27 | CCA | PEK | 0.03 | -2.9 | 19 min |
| CA 428 | 2026-10-27 | CCA | CTU | 0.04 | -2.7 | 32 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2966 | 0.6640 | 0.1458 | 0.4605 | 13.9 | 2026-10-19T20:47:45+00:00 | 2026-10-27T14:44:34+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2966}
