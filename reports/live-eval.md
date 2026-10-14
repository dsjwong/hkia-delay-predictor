# Live evaluation — predictions vs actuals

Generated 2026-10-14T21:39:19+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3001**.

Dates 2026-10-08..2026-10-14; observed P(delay > 15) = 0.142; median lead time between last score and departure = 184.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.693 | 0.1188 | 0.3888 | 11.402 |
| baseline_airline_hour | 0.6757 | 0.1353 | 0.4391 | 16.215 |
| naive_rate | 0.5 | 0.1218 | 0.4085 | 10.731 |

Coverage: **3001 of 3040** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3001 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0173 | [-0.0057, +0.0386] | no — CI straddles 0 |
| brier | -0.0165 | [-0.0197, -0.0133] | **yes** |
| logloss | -0.0503 | [-0.0593, -0.0414] | **yes** |
| mae | -4.81 | [-5.1108, -4.5358] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-08 † | 405 | 0.1531 | 0.6796 | 0.6752 | 0.1272 | 12.9 | 17.4 |
| 2026-10-09 | 449 | 0.1180 | 0.6776 | 0.6584 | 0.1111 | 12.3 | 16.8 |
| 2026-10-10 | 436 | 0.2271 | 0.6730 | 0.6612 | 0.1657 | 14.6 | 18.2 |
| 2026-10-11 | 437 | 0.1236 | 0.6972 | 0.6659 | 0.1094 | 9.8 | 15.1 |
| 2026-10-12 | 434 | 0.1267 | 0.6957 | 0.6393 | 0.1026 | 9.6 | 15.5 |
| 2026-10-13 | 423 | 0.1371 | 0.7361 | 0.7383 | 0.1091 | 10.3 | 15.5 |
| 2026-10-14 † | 417 | 0.1079 | 0.7085 | 0.7056 | 0.1062 | 10.3 | 15.0 |

`†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 69 | 0.6957 | 0.5992 | 0.6101 | 41.6 |
| < 30 min | 208 | 0.2163 | 0.6721 | 0.6079 | 10.9 |
| 30–120 min | 720 | 0.1556 | 0.7038 | 0.6727 | 11.2 |
| 2–12 h | 1942 | 0.1133 | 0.6867 | 0.6709 | 10.6 |
| > 12 h * | 62 | 0.0161 | 0.5902 | 0.6803 | 6.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 830 | 0.065 | 0.042 |
| 0.1-0.2 | 896 | 0.144 | 0.116 |
| 0.2-0.3 | 710 | 0.249 | 0.201 |
| 0.3-0.4 | 392 | 0.343 | 0.222 |
| 0.4-0.5 | 127 | 0.440 | 0.307 |
| 0.5-0.6 | 37 | 0.538 | 0.351 |
| 0.6-0.7 * | 7 | 0.639 | 0.429 |
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
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| EK 381 | 2026-10-09 | UAE | DXB | 0.04 | 0.4 | 36 min |
| KE 2002 | 2026-10-10 | KAL | ICN | 0.04 | 1.0 | 76 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |
| CX 506 | 2026-10-14 | CPA | KIX | 0.63 | 26.5 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3001 | 0.6930 | 0.1188 | 0.3888 | 11.4 | 2026-10-07T02:31:54+00:00 | 2026-10-14T10:46:58+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3001}
