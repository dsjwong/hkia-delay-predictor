# Live evaluation — predictions vs actuals

Generated 2026-10-11T21:55:44+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3119**.

Dates 2026-10-05..2026-10-12; observed P(delay > 15) = 0.1555; median lead time between last score and departure = 197.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6674 | 0.1285 | 0.4153 | 13.259 |
| baseline_airline_hour | 0.6586 | 0.1422 | 0.4545 | 17.616 |
| naive_rate | 0.5 | 0.1313 | 0.4321 | 12.181 |

Coverage: **3119 of 3161** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3119 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0088 | [-0.0125, +0.0290] | no — CI straddles 0 |
| brier | -0.0137 | [-0.0169, -0.0105] | **yes** |
| logloss | -0.0392 | [-0.0481, -0.0301] | **yes** |
| mae | -4.36 | [-4.6319, -4.0794] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-05 † | 409 | 0.1100 | 0.6776 | 0.6728 | 0.1012 | 11.0 | 17.2 |
| 2026-10-06 | 449 | 0.1782 | 0.6253 | 0.6585 | 0.1469 | 18.0 | 20.8 |
| 2026-10-07 | 454 | 0.1784 | 0.6703 | 0.6263 | 0.1402 | 14.8 | 19.0 |
| 2026-10-08 | 444 | 0.1532 | 0.6788 | 0.6782 | 0.1266 | 12.5 | 16.8 |
| 2026-10-09 | 449 | 0.1180 | 0.6776 | 0.6584 | 0.1111 | 12.3 | 16.8 |
| 2026-10-10 | 436 | 0.2271 | 0.6730 | 0.6612 | 0.1657 | 14.6 | 18.2 |
| 2026-10-11 | 437 | 0.1236 | 0.6972 | 0.6659 | 0.1094 | 9.8 | 15.1 |
| 2026-10-12 *† | 41 | 0.1220 | 0.7278 | 0.7556 | 0.0917 | 7.9 | 10.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 79 | 0.7342 | 0.6585 | 0.5583 | 51.2 |
| < 30 min | 212 | 0.1981 | 0.6381 | 0.6018 | 10.8 |
| 30–120 min | 744 | 0.1586 | 0.6420 | 0.6116 | 11.9 |
| 2–12 h | 2014 | 0.1301 | 0.6777 | 0.6759 | 12.7 |
| > 12 h * | 70 | 0.0714 | 0.7708 | 0.6769 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 797 | 0.064 | 0.053 |
| 0.1-0.2 | 965 | 0.146 | 0.139 |
| 0.2-0.3 | 788 | 0.248 | 0.207 |
| 0.3-0.4 | 413 | 0.344 | 0.237 |
| 0.4-0.5 | 119 | 0.438 | 0.277 |
| 0.5-0.6 | 33 | 0.534 | 0.364 |
| 0.6-0.7 * | 2 | 0.638 | 0.500 |
| 0.8-0.9 * | 2 | 0.851 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-10 | RNA | KTM | 0.87 | 58.7 | 195 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| OD 606 | 2026-10-11 | MXD | KUL | 0.61 | 48.8 | 19 min |
| TG 639 | 2026-10-10 | THA | BKK | 0.57 | 18.7 | 43 min |
| OD 606 | 2026-10-09 | MXD | KUL | 0.56 | 52.7 | 49 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 2 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |
| VJ 985 | 2026-10-06 | VJC | PQC | 0.58 | 31.0 | -6 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3119 | 0.6674 | 0.1285 | 0.4153 | 13.3 | 2026-10-04T17:54:55+00:00 | 2026-10-11T14:15:21+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3119}
