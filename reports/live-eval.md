# Live evaluation — predictions vs actuals

Generated 2026-09-11T20:56:47+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2800**.

Dates 2026-09-05..2026-09-12; observed P(delay > 15) = 0.1286; median lead time between last score and departure = 121.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6865 | 0.1131 | 0.3744 | 10.861 |
| baseline_airline_hour | 0.6649 | 0.1316 | 0.4322 | 16.097 |
| naive_rate | 0.5 | 0.112 | 0.3837 | 9.944 |

Coverage: **2800 of 2841** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2800 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0216 | [-0.0061, +0.0502] | no — CI straddles 0 |
| brier | -0.0185 | [-0.0225, -0.0143] | **yes** |
| logloss | -0.0578 | [-0.0692, -0.0457] | **yes** |
| mae | -5.24 | [-5.5779, -4.8594] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-05 † | 369 | 0.1220 | 0.6850 | 0.6215 | 0.1144 | 10.7 | 16.5 |
| 2026-09-06 | 410 | 0.1732 | 0.6271 | 0.6146 | 0.1686 | 14.4 | 15.0 |
| 2026-09-07 | 400 | 0.0975 | 0.7261 | 0.7205 | 0.0904 | 9.9 | 16.5 |
| 2026-09-08 | 384 | 0.0885 | 0.6350 | 0.6201 | 0.0833 | 9.6 | 17.0 |
| 2026-09-09 | 384 | 0.1016 | 0.7097 | 0.7427 | 0.0860 | 10.6 | 17.8 |
| 2026-09-10 | 397 | 0.1537 | 0.6538 | 0.6665 | 0.1244 | 10.7 | 15.9 |
| 2026-09-11 | 416 | 0.1587 | 0.7125 | 0.6779 | 0.1227 | 10.0 | 14.4 |
| 2026-09-12 *† | 40 | 0.1250 | 0.8114 | 0.8857 | 0.0931 | 11.5 | 13.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 89 | 0.6517 | 0.5565 | 0.5072 | 42.7 |
| < 30 min | 310 | 0.1226 | 0.6583 | 0.6085 | 9.1 |
| 30–120 min | 1046 | 0.1099 | 0.6886 | 0.6435 | 9.4 |
| 2–12 h | 1343 | 0.1109 | 0.7114 | 0.7209 | 10.4 |
| > 12 h * | 12 | 0.0000 | — | — | 6.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 879 | 0.063 | 0.043 |
| 0.1-0.2 | 970 | 0.146 | 0.125 |
| 0.2-0.3 | 549 | 0.242 | 0.186 |
| 0.3-0.4 | 214 | 0.341 | 0.229 |
| 0.4-0.5 | 95 | 0.445 | 0.242 |
| 0.5-0.6 | 54 | 0.550 | 0.278 |
| 0.6-0.7 | 30 | 0.646 | 0.267 |
| 0.7-0.8 * | 9 | 0.726 | 0.444 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| HX 608 | 2026-09-06 | CRK | NRT | 0.75 | 31.4 | 24 min |
| HX 618 | 2026-09-06 | CRK | KIX | 0.74 | 35.0 | 25 min |
| NH 812 | 2026-09-06 | ANA | NRT | 0.72 | 30.4 | 23 min |
| CX 504 | 2026-09-06 | CPA | NRT | 0.72 | 36.3 | 64 min |
| CX 342 | 2026-09-06 | CPA | SHA | 0.68 | 34.2 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (44%).

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
| 4a4212f@2026-08-25T09:35:34+00:00 | 2800 | 0.6865 | 0.1131 | 0.3744 | 10.9 | 2026-09-04T19:43:29+00:00 | 2026-09-11T17:24:36+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2800}
