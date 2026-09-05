# Live evaluation — predictions vs actuals

Generated 2026-09-05T20:18:44+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2913**.

Dates 2026-08-30..2026-09-06; observed P(delay > 15) = 0.1809; median lead time between last score and departure = 130.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6502 | 0.1521 | 0.4735 | 12.757 |
| baseline_airline_hour | 0.6164 | 0.1552 | 0.4859 | 16.353 |
| naive_rate | 0.5 | 0.1482 | 0.4728 | 11.878 |

Coverage: **2913 of 2953** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2913 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0338 | [+0.0094, +0.0594] | **yes** |
| brier | -0.0031 | [-0.0071, +0.0005] | no — CI straddles 0 |
| logloss | -0.0124 | [-0.0226, -0.0030] | **yes** |
| mae | -3.60 | [-3.9058, -3.3135] | **yes** |

The model is separably better on: auc, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-30 † | 411 | 0.2676 | 0.6621 | 0.6513 | 0.1829 | 15.0 | 17.9 |
| 2026-08-31 | 442 | 0.1991 | 0.6230 | 0.5766 | 0.1751 | 14.8 | 16.9 |
| 2026-09-01 | 403 | 0.1737 | 0.5722 | 0.6105 | 0.1938 | 15.2 | 15.6 |
| 2026-09-02 | 405 | 0.1802 | 0.6607 | 0.6256 | 0.1432 | 12.3 | 16.6 |
| 2026-09-03 | 393 | 0.1578 | 0.6067 | 0.5606 | 0.1317 | 10.8 | 16.0 |
| 2026-09-04 | 418 | 0.1770 | 0.7245 | 0.6272 | 0.1309 | 10.7 | 15.6 |
| 2026-09-05 | 410 | 0.1195 | 0.6704 | 0.6390 | 0.1133 | 10.8 | 16.3 |
| 2026-09-06 *† | 31 | 0.0323 | 0.8333 | 0.7000 | 0.0461 | 6.9 | 10.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 102 | 0.7549 | 0.7636 | 0.6257 | 44.7 |
| < 30 min | 339 | 0.1475 | 0.6531 | 0.6224 | 10.3 |
| 30–120 min | 1003 | 0.1805 | 0.6570 | 0.6088 | 11.1 |
| 2–12 h | 1461 | 0.1499 | 0.6330 | 0.6274 | 12.3 |
| > 12 h * | 8 | 0.0000 | — | — | 5.9 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 484 | 0.065 | 0.072 |
| 0.1-0.2 | 806 | 0.149 | 0.133 |
| 0.2-0.3 | 692 | 0.248 | 0.184 |
| 0.3-0.4 | 451 | 0.347 | 0.268 |
| 0.4-0.5 | 310 | 0.447 | 0.281 |
| 0.5-0.6 | 108 | 0.540 | 0.278 |
| 0.6-0.7 | 48 | 0.644 | 0.312 |
| 0.7-0.8 * | 13 | 0.737 | 0.308 |
| 0.8-0.9 * | 1 | 0.806 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-09-01 | RNA | KTM | 0.81 | 45.1 | 182 min |
| CX 548 | 2026-09-01 | CPA | HND | 0.76 | 33.8 | 43 min |
| LX 139 | 2026-08-30 | SWR | ZRH | 0.73 | 28.7 | 36 min |
| CX 797 | 2026-08-30 | CPA | CGK | 0.72 | 31.1 | 192 min |
| VJ 877 | 2026-08-30 | VJC | SGN | 0.72 | 34.6 | 19 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 14 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (36%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 704 | 2026-09-03 | HKE | BKK | 0.02 | -2.8 | 21 min |
| NH 814 | 2026-09-03 | ANA | HND | 0.03 | -4.8 | 21 min |
| KE 2012 | 2026-09-05 | KAL | ICN | 0.03 | -2.5 | 161 min |
| LX 139 | 2026-08-31 | SWR | ZRH | 0.78 | 29.8 | 15 min |
| CX 520 | 2026-09-01 | CPA | NRT | 0.76 | 40.9 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2913 | 0.6502 | 0.1521 | 0.4735 | 12.8 | 2026-08-29T21:30:30+00:00 | 2026-09-05T16:22:13+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2913}
