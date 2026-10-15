# Live evaluation — predictions vs actuals

Generated 2026-10-15T21:20:55+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3021**.

Dates 2026-10-09..2026-10-16; observed P(delay > 15) = 0.1367; median lead time between last score and departure = 171.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.7026 | 0.1142 | 0.3763 | 10.876 |
| baseline_airline_hour | 0.6799 | 0.1327 | 0.4331 | 15.897 |
| naive_rate | 0.5 | 0.118 | 0.3989 | 10.512 |

Coverage: **3021 of 3057** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3021 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0227 | [+0.0014, +0.0436] | **yes** |
| brier | -0.0185 | [-0.0216, -0.0154] | **yes** |
| logloss | -0.0568 | [-0.0659, -0.0476] | **yes** |
| mae | -5.02 | [-5.3171, -4.7232] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-09 † | 413 | 0.1211 | 0.6737 | 0.6533 | 0.1134 | 12.6 | 17.2 |
| 2026-10-10 | 436 | 0.2271 | 0.6730 | 0.6612 | 0.1657 | 14.6 | 18.2 |
| 2026-10-11 | 437 | 0.1236 | 0.6972 | 0.6659 | 0.1094 | 9.8 | 15.1 |
| 2026-10-12 | 434 | 0.1267 | 0.6957 | 0.6393 | 0.1026 | 9.6 | 15.5 |
| 2026-10-13 | 423 | 0.1371 | 0.7361 | 0.7383 | 0.1091 | 10.3 | 15.5 |
| 2026-10-14 | 420 | 0.1071 | 0.7107 | 0.7070 | 0.1055 | 10.2 | 15.1 |
| 2026-10-15 | 421 | 0.1116 | 0.7419 | 0.7044 | 0.0940 | 9.1 | 15.1 |
| 2026-10-16 *† | 37 | 0.1351 | 0.6656 | 0.8594 | 0.0955 | 8.7 | 11.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 65 | 0.6923 | 0.6167 | 0.6444 | 39.5 |
| < 30 min | 242 | 0.2066 | 0.7269 | 0.6613 | 11.7 |
| 30–120 min | 812 | 0.1502 | 0.7093 | 0.6737 | 10.4 |
| 2–12 h | 1851 | 0.1053 | 0.6939 | 0.6728 | 10.1 |
| > 12 h * | 51 | 0.0196 | 0.5000 | 0.6600 | 6.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 879 | 0.064 | 0.038 |
| 0.1-0.2 | 959 | 0.144 | 0.120 |
| 0.2-0.3 | 670 | 0.248 | 0.196 |
| 0.3-0.4 | 352 | 0.342 | 0.224 |
| 0.4-0.5 | 120 | 0.438 | 0.317 |
| 0.5-0.6 | 31 | 0.539 | 0.387 |
| 0.6-0.7 * | 8 | 0.646 | 0.375 |
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
| OD 606 | 2026-10-11 | MXD | KUL | 0.61 | 48.8 | 19 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2002 | 2026-10-10 | KAL | ICN | 0.04 | 1.0 | 76 min |
| UO 600 | 2026-10-10 | HKE | FUK | 0.04 | -5.2 | 23 min |
| UO 130 | 2026-10-11 | HKE | KHH | 0.04 | 1.4 | 19 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3021 | 0.7026 | 0.1142 | 0.3763 | 10.9 | 2026-10-07T21:41:26+00:00 | 2026-10-15T15:39:53+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3021}
