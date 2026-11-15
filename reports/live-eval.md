# Live evaluation — predictions vs actuals

Generated 2026-11-15T22:47:26+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2836**.

Dates 2026-11-09..2026-11-16; observed P(delay > 15) = 0.146; median lead time between last score and departure = 203.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.653 | 0.1238 | 0.4065 | 11.524 |
| baseline_airline_hour | 0.6145 | 0.1409 | 0.4549 | 15.911 |
| naive_rate | 0.5 | 0.1247 | 0.4157 | 10.794 |

Coverage: **2836 of 2876** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2836 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0385 | [+0.0081, +0.0687] | **yes** |
| brier | -0.0171 | [-0.0206, -0.0134] | **yes** |
| logloss | -0.0484 | [-0.0584, -0.0383] | **yes** |
| mae | -4.39 | [-4.6843, -4.1010] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-09 † | 364 | 0.1346 | 0.7243 | 0.6575 | 0.1082 | 10.2 | 16.1 |
| 2026-11-10 | 391 | 0.1714 | 0.7526 | 0.6521 | 0.1272 | 11.7 | 16.1 |
| 2026-11-11 | 396 | 0.1010 | 0.6205 | 0.6142 | 0.0955 | 10.2 | 16.1 |
| 2026-11-12 | 396 | 0.1212 | 0.6581 | 0.6283 | 0.1036 | 8.7 | 14.7 |
| 2026-11-13 | 416 | 0.1298 | 0.6018 | 0.6843 | 0.1168 | 10.2 | 14.7 |
| 2026-11-14 | 416 | 0.1659 | 0.6539 | 0.5838 | 0.1521 | 15.9 | 17.4 |
| 2026-11-15 | 418 | 0.1890 | 0.6041 | 0.5398 | 0.1556 | 13.5 | 16.9 |
| 2026-11-16 *† | 39 | 0.2051 | 0.5242 | 0.5202 | 0.1607 | 10.1 | 10.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 63 | 0.6032 | 0.6316 | 0.5363 | 42.0 |
| < 30 min | 195 | 0.1538 | 0.7085 | 0.6068 | 12.0 |
| 30–120 min | 678 | 0.1475 | 0.6697 | 0.6610 | 10.2 |
| 2–12 h | 1776 | 0.1306 | 0.6342 | 0.5933 | 11.0 |
| > 12 h | 124 | 0.1129 | 0.7406 | 0.5516 | 9.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 655 | 0.070 | 0.063 |
| 0.1-0.2 | 1017 | 0.149 | 0.135 |
| 0.2-0.3 | 669 | 0.243 | 0.145 |
| 0.3-0.4 | 322 | 0.344 | 0.270 |
| 0.4-0.5 | 117 | 0.441 | 0.214 |
| 0.5-0.6 | 36 | 0.544 | 0.472 |
| 0.6-0.7 * | 15 | 0.626 | 0.467 |
| 0.7-0.8 * | 4 | 0.751 | 0.500 |
| 0.9-1.0 * | 1 | 0.912 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-14 | RNA | KTM | 0.91 | 55.8 | 83 min |
| LX 139 | 2026-11-14 | SWR | ZRH | 0.79 | 32.6 | 30 min |
| VJ 985 | 2026-11-14 | VJC | PQC | 0.74 | 34.4 | 219 min |
| QF 128 | 2026-11-15 | QFA | SYD | 0.67 | 23.7 | 66 min |
| VJ 877 | 2026-11-15 | VJC | SGN | 0.64 | 38.4 | 83 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 5 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (60%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-11-12 | HKE | HND | 0.03 | -4.9 | 33 min |
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| UO 132 | 2026-11-10 | HKE | KHH | 0.05 | -1.1 | 36 min |
| LX 139 | 2026-11-15 | SWR | ZRH | 0.74 | 31.0 | 8 min |
| QF 128 | 2026-11-14 | QFA | SYD | 0.73 | 30.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2836 | 0.6530 | 0.1238 | 0.4065 | 11.5 | 2026-11-08T19:49:35+00:00 | 2026-11-15T16:41:51+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2836}
