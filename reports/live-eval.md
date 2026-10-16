# Live evaluation — predictions vs actuals

Generated 2026-10-16T21:04:44+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3014**.

Dates 2026-10-10..2026-10-17; observed P(delay > 15) = 0.138; median lead time between last score and departure = 160.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.696 | 0.1157 | 0.381 | 10.871 |
| baseline_airline_hour | 0.6748 | 0.1333 | 0.4351 | 15.76 |
| naive_rate | 0.5 | 0.119 | 0.4014 | 10.553 |

Coverage: **3014 of 3053** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3014 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0212 | [+0.0005, +0.0429] | **yes** |
| brier | -0.0176 | [-0.0208, -0.0147] | **yes** |
| logloss | -0.0541 | [-0.0632, -0.0456] | **yes** |
| mae | -4.89 | [-5.1887, -4.5782] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-10 † | 397 | 0.2418 | 0.6668 | 0.6465 | 0.1738 | 15.3 | 18.9 |
| 2026-10-11 | 437 | 0.1236 | 0.6972 | 0.6659 | 0.1094 | 9.8 | 15.1 |
| 2026-10-12 | 434 | 0.1267 | 0.6957 | 0.6393 | 0.1026 | 9.6 | 15.5 |
| 2026-10-13 | 423 | 0.1371 | 0.7361 | 0.7383 | 0.1091 | 10.3 | 15.5 |
| 2026-10-14 | 420 | 0.1071 | 0.7107 | 0.7070 | 0.1055 | 10.2 | 15.1 |
| 2026-10-15 | 421 | 0.1116 | 0.7419 | 0.7044 | 0.0940 | 9.1 | 15.1 |
| 2026-10-16 | 448 | 0.1250 | 0.6116 | 0.6268 | 0.1205 | 12.3 | 15.9 |
| 2026-10-17 *† | 34 | 0.1471 | 0.8414 | 0.7517 | 0.0967 | 6.8 | 9.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 67 | 0.6716 | 0.5737 | 0.6439 | 45.2 |
| < 30 min | 255 | 0.1843 | 0.6994 | 0.6484 | 11.1 |
| 30–120 min | 889 | 0.1440 | 0.7068 | 0.6618 | 10.2 |
| 2–12 h | 1753 | 0.1112 | 0.6954 | 0.6792 | 10.0 |
| > 12 h * | 50 | 0.0200 | 0.4694 | 0.6531 | 6.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 868 | 0.063 | 0.043 |
| 0.1-0.2 | 979 | 0.145 | 0.115 |
| 0.2-0.3 | 666 | 0.247 | 0.206 |
| 0.3-0.4 | 336 | 0.342 | 0.226 |
| 0.4-0.5 | 117 | 0.441 | 0.308 |
| 0.5-0.6 | 37 | 0.540 | 0.297 |
| 0.6-0.7 * | 9 | 0.642 | 0.444 |
| 0.7-0.8 * | 1 | 0.731 | 1.000 |
| 0.8-0.9 * | 1 | 0.873 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-10 | RNA | KTM | 0.87 | 58.7 | 195 min |
| VJ 985 | 2026-10-13 | VJC | PQC | 0.73 | 30.9 | 33 min |
| NH 812 | 2026-10-14 | ANA | NRT | 0.70 | 24.0 | 35 min |
| CX 520 | 2026-10-14 | CPA | NRT | 0.62 | 25.8 | 45 min |
| CX 520 | 2026-10-16 | CPA | NRT | 0.61 | 28.0 | 38 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| KE 2002 | 2026-10-10 | KAL | ICN | 0.04 | 1.0 | 76 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3014 | 0.6960 | 0.1157 | 0.3810 | 10.9 | 2026-10-09T13:57:55+00:00 | 2026-10-16T14:31:48+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3014}
