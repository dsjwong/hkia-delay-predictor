# Live evaluation — predictions vs actuals

Generated 2026-09-12T20:32:08+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2796**.

Dates 2026-09-06..2026-09-13; observed P(delay > 15) = 0.1316; median lead time between last score and departure = 122.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6909 | 0.1136 | 0.3759 | 10.898 |
| baseline_airline_hour | 0.6749 | 0.1324 | 0.4336 | 16.059 |
| naive_rate | 0.5 | 0.1143 | 0.3894 | 10.046 |

Coverage: **2796 of 2832** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2796 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0160 | [-0.0134, +0.0424] | no — CI straddles 0 |
| brier | -0.0188 | [-0.0227, -0.0147] | **yes** |
| logloss | -0.0577 | [-0.0687, -0.0459] | **yes** |
| mae | -5.16 | [-5.5186, -4.8091] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-06 † | 374 | 0.1791 | 0.6248 | 0.6054 | 0.1742 | 14.9 | 15.4 |
| 2026-09-07 | 400 | 0.0975 | 0.7261 | 0.7205 | 0.0904 | 9.9 | 16.5 |
| 2026-09-08 | 384 | 0.0885 | 0.6350 | 0.6201 | 0.0833 | 9.6 | 17.0 |
| 2026-09-09 | 384 | 0.1016 | 0.7097 | 0.7427 | 0.0860 | 10.6 | 17.8 |
| 2026-09-10 | 397 | 0.1537 | 0.6538 | 0.6665 | 0.1244 | 10.7 | 15.9 |
| 2026-09-11 | 416 | 0.1587 | 0.7125 | 0.6779 | 0.1227 | 10.0 | 14.4 |
| 2026-09-12 | 406 | 0.1429 | 0.7051 | 0.7068 | 0.1160 | 10.8 | 15.7 |
| 2026-09-13 *† | 35 | 0.1143 | 0.5968 | 0.7661 | 0.1073 | 12.1 | 14.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 97 | 0.6392 | 0.5438 | 0.5127 | 41.7 |
| < 30 min | 302 | 0.1325 | 0.7222 | 0.6356 | 8.9 |
| 30–120 min | 1023 | 0.1046 | 0.6859 | 0.6661 | 9.4 |
| 2–12 h | 1362 | 0.1167 | 0.7200 | 0.7224 | 10.3 |
| > 12 h * | 12 | 0.0000 | — | — | 6.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 883 | 0.063 | 0.049 |
| 0.1-0.2 | 983 | 0.146 | 0.119 |
| 0.2-0.3 | 554 | 0.241 | 0.195 |
| 0.3-0.4 | 202 | 0.340 | 0.248 |
| 0.4-0.5 | 83 | 0.444 | 0.265 |
| 0.5-0.6 | 52 | 0.546 | 0.308 |
| 0.6-0.7 * | 29 | 0.644 | 0.276 |
| 0.7-0.8 * | 10 | 0.724 | 0.400 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| HX 608 | 2026-09-06 | CRK | NRT | 0.75 | 31.4 | 24 min |
| HX 618 | 2026-09-06 | CRK | KIX | 0.74 | 35.0 | 25 min |
| NH 812 | 2026-09-06 | ANA | NRT | 0.72 | 30.4 | 23 min |
| CX 504 | 2026-09-06 | CPA | NRT | 0.72 | 36.3 | 64 min |
| CX 342 | 2026-09-06 | CPA | SHA | 0.68 | 34.2 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 10 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (40%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 700 | 2026-09-10 | HKE | BKK | 0.01 | -4.3 | 26 min |
| UO 670 | 2026-09-10 | HKE | NGO | 0.02 | -5.8 | 48 min |
| CX 334 | 2026-09-08 | CPA | PEK | 0.04 | -3.3 | 32 min |
| DL 088 | 2026-09-06 | DAL | LAX | 0.74 | 38.0 | 10 min |
| OD 606 | 2026-09-06 | MXD | KUL | 0.73 | 69.3 | 0 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2796 | 0.6909 | 0.1136 | 0.3759 | 10.9 | 2026-09-05T22:27:12+00:00 | 2026-09-12T17:57:54+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2796}
