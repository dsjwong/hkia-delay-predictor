# Live evaluation — predictions vs actuals

Generated 2026-10-20T21:35:27+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3046**.

Dates 2026-10-14..2026-10-21; observed P(delay > 15) = 0.1326; median lead time between last score and departure = 131.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6822 | 0.1161 | 0.3835 | 11.708 |
| baseline_airline_hour | 0.68 | 0.1315 | 0.4345 | 16.169 |
| naive_rate | 0.5 | 0.115 | 0.3914 | 10.969 |

Coverage: **3046 of 3083** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3046 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0022 | [-0.0197, +0.0238] | no — CI straddles 0 |
| brier | -0.0154 | [-0.0187, -0.0123] | **yes** |
| logloss | -0.0510 | [-0.0648, -0.0393] | **yes** |
| mae | -4.46 | [-4.7495, -4.1657] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-14 † | 383 | 0.1123 | 0.6931 | 0.6873 | 0.1114 | 10.7 | 15.5 |
| 2026-10-15 | 421 | 0.1116 | 0.7419 | 0.7044 | 0.0940 | 9.1 | 15.1 |
| 2026-10-16 | 448 | 0.1250 | 0.6116 | 0.6268 | 0.1205 | 12.3 | 15.9 |
| 2026-10-17 | 441 | 0.1678 | 0.7029 | 0.6981 | 0.1335 | 14.0 | 17.7 |
| 2026-10-18 | 439 | 0.1458 | 0.7372 | 0.7121 | 0.1197 | 12.6 | 16.7 |
| 2026-10-19 | 447 | 0.1365 | 0.6465 | 0.6142 | 0.1164 | 11.7 | 17.0 |
| 2026-10-20 | 431 | 0.1346 | 0.6420 | 0.7145 | 0.1215 | 11.9 | 15.6 |
| 2026-10-21 *† | 36 | 0.0278 | 0.6857 | 0.5429 | 0.0415 | 5.8 | 11.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 90 | 0.6444 | 0.5954 | 0.6366 | 46.5 |
| < 30 min | 328 | 0.1463 | 0.7071 | 0.6219 | 12.6 |
| 30–120 min | 1048 | 0.1307 | 0.6878 | 0.6685 | 10.4 |
| 2–12 h | 1558 | 0.1027 | 0.6830 | 0.7150 | 10.5 |
| > 12 h * | 22 | 0.0455 | 0.9048 | 0.9286 | 7.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 774 | 0.064 | 0.040 |
| 0.1-0.2 | 976 | 0.146 | 0.112 |
| 0.2-0.3 | 678 | 0.246 | 0.170 |
| 0.3-0.4 | 402 | 0.341 | 0.224 |
| 0.4-0.5 | 151 | 0.444 | 0.238 |
| 0.5-0.6 | 50 | 0.539 | 0.280 |
| 0.6-0.7 * | 11 | 0.637 | 0.545 |
| 0.7-0.8 * | 3 | 0.724 | 0.667 |
| 0.8-0.9 * | 1 | 0.870 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |
| NH 812 | 2026-10-14 | ANA | NRT | 0.70 | 24.0 | 35 min |
| LX 139 | 2026-10-17 | SWR | ZRH | 0.68 | 21.5 | 32 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| KE 2006 | 2026-10-18 | KAL | ICN | 0.04 | -0.2 | 145 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3046 | 0.6822 | 0.1161 | 0.3835 | 11.7 | 2026-10-13T16:34:19+00:00 | 2026-10-20T15:14:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3046}
