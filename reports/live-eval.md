# Live evaluation — predictions vs actuals

Generated 2026-09-22T21:16:46+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2878**.

Dates 2026-09-16..2026-09-23; observed P(delay > 15) = 0.1341; median lead time between last score and departure = 126.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.689 | 0.1108 | 0.3715 | 10.761 |
| baseline_airline_hour | 0.6566 | 0.1351 | 0.4397 | 16.37 |
| naive_rate | 0.5 | 0.1161 | 0.3941 | 10.853 |

Coverage: **2878 of 2914** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2878 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0324 | [+0.0094, +0.0551] | **yes** |
| brier | -0.0243 | [-0.0276, -0.0208] | **yes** |
| logloss | -0.0682 | [-0.0780, -0.0581] | **yes** |
| mae | -5.61 | [-5.9330, -5.2843] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-16 † | 354 | 0.1271 | 0.7709 | 0.6949 | 0.1001 | 9.8 | 16.4 |
| 2026-09-17 | 399 | 0.1203 | 0.7270 | 0.6686 | 0.1020 | 11.0 | 17.1 |
| 2026-09-18 | 418 | 0.1148 | 0.6810 | 0.6624 | 0.1007 | 8.8 | 14.6 |
| 2026-09-19 | 424 | 0.1486 | 0.6913 | 0.6467 | 0.1193 | 11.9 | 17.1 |
| 2026-09-20 | 423 | 0.1253 | 0.6765 | 0.6537 | 0.1082 | 11.8 | 17.2 |
| 2026-09-21 | 412 | 0.1311 | 0.5944 | 0.5875 | 0.1182 | 10.4 | 15.8 |
| 2026-09-22 | 410 | 0.1756 | 0.7213 | 0.6813 | 0.1305 | 11.7 | 16.7 |
| 2026-09-23 *† | 38 | 0.0789 | 0.8190 | 0.6667 | 0.0585 | 8.5 | 11.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 107 | 0.7009 | 0.5579 | 0.5590 | 49.1 |
| < 30 min | 319 | 0.1379 | 0.7421 | 0.6402 | 9.1 |
| 30–120 min | 1030 | 0.1136 | 0.6659 | 0.6213 | 9.3 |
| 2–12 h | 1404 | 0.1068 | 0.6744 | 0.6557 | 9.4 |
| > 12 h * | 18 | 0.0000 | — | — | 5.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 873 | 0.063 | 0.060 |
| 0.1-0.2 | 1063 | 0.148 | 0.109 |
| 0.2-0.3 | 634 | 0.245 | 0.196 |
| 0.3-0.4 | 225 | 0.339 | 0.262 |
| 0.4-0.5 | 55 | 0.439 | 0.364 |
| 0.5-0.6 * | 21 | 0.546 | 0.571 |
| 0.6-0.7 * | 6 | 0.644 | 0.333 |
| 0.7-0.8 * | 1 | 0.777 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-09-19 | RNA | KTM | 0.78 | 52.8 | 55 min |
| VJ 985 | 2026-09-22 | VJC | PQC | 0.65 | 29.8 | 40 min |
| CX 520 | 2026-09-20 | CPA | NRT | 0.60 | 25.4 | 62 min |
| OD 606 | 2026-09-22 | MXD | KUL | 0.60 | 46.7 | 158 min |
| VJ 985 | 2026-09-17 | VJC | PQC | 0.59 | 26.1 | 20 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-09-18 | JNA | CJU | 0.03 | -1.2 | 20 min |
| UO 604 | 2026-09-21 | HKE | PUS | 0.03 | -6.9 | 26 min |
| NH 814 | 2026-09-20 | ANA | HND | 0.04 | -4.3 | 149 min |
| VJ 985 | 2026-09-19 | VJC | PQC | 0.70 | 34.0 | 0 min |
| NH 812 | 2026-09-21 | ANA | NRT | 0.66 | 30.1 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2878 | 0.6890 | 0.1108 | 0.3715 | 10.8 | 2026-09-15T10:37:49+00:00 | 2026-09-22T17:06:51+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2878}
