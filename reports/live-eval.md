# Live evaluation — predictions vs actuals

Generated 2026-10-10T21:40:58+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3127**.

Dates 2026-10-04..2026-10-11; observed P(delay > 15) = 0.1631; median lead time between last score and departure = 191.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6704 | 0.1328 | 0.4259 | 13.868 |
| baseline_airline_hour | 0.6599 | 0.1449 | 0.4601 | 17.957 |
| naive_rate | 0.5 | 0.1365 | 0.4448 | 12.793 |

Coverage: **3127 of 3166** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3127 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0105 | [-0.0102, +0.0310] | no — CI straddles 0 |
| brier | -0.0121 | [-0.0154, -0.0087] | **yes** |
| logloss | -0.0342 | [-0.0433, -0.0252] | **yes** |
| mae | -4.09 | [-4.3603, -3.8148] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-04 † | 409 | 0.1883 | 0.6995 | 0.6580 | 0.1448 | 14.3 | 17.9 |
| 2026-10-05 | 451 | 0.1086 | 0.6805 | 0.6774 | 0.1019 | 11.1 | 16.6 |
| 2026-10-06 | 449 | 0.1782 | 0.6253 | 0.6585 | 0.1469 | 18.0 | 20.8 |
| 2026-10-07 | 454 | 0.1784 | 0.6703 | 0.6263 | 0.1402 | 14.8 | 19.0 |
| 2026-10-08 | 444 | 0.1532 | 0.6788 | 0.6782 | 0.1266 | 12.5 | 16.8 |
| 2026-10-09 | 449 | 0.1180 | 0.6776 | 0.6584 | 0.1111 | 12.3 | 16.8 |
| 2026-10-10 | 436 | 0.2271 | 0.6730 | 0.6612 | 0.1657 | 14.6 | 18.2 |
| 2026-10-11 *† | 35 | 0.0857 | 0.8594 | 0.8073 | 0.0657 | 8.4 | 12.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 95 | 0.7895 | 0.6780 | 0.5823 | 53.4 |
| < 30 min | 214 | 0.1729 | 0.6064 | 0.5512 | 11.5 |
| 30–120 min | 743 | 0.1561 | 0.6604 | 0.6209 | 12.1 |
| 2–12 h | 2010 | 0.1378 | 0.6685 | 0.6762 | 13.1 |
| > 12 h * | 65 | 0.0769 | 0.7917 | 0.7017 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 753 | 0.064 | 0.058 |
| 0.1-0.2 | 967 | 0.147 | 0.135 |
| 0.2-0.3 | 763 | 0.248 | 0.212 |
| 0.3-0.4 | 425 | 0.344 | 0.247 |
| 0.4-0.5 | 151 | 0.437 | 0.245 |
| 0.5-0.6 | 51 | 0.542 | 0.392 |
| 0.6-0.7 * | 11 | 0.648 | 0.455 |
| 0.7-0.8 * | 4 | 0.734 | 1.000 |
| 0.8-0.9 * | 2 | 0.851 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-10 | RNA | KTM | 0.87 | 58.7 | 195 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| CX 302 | 2026-10-04 | CPA | PVG | 0.77 | 32.0 | 79 min |
| CX 161 | 2026-10-04 | CPA | SYD | 0.74 | 31.5 | 35 min |
| CX 113 | 2026-10-04 | CPA | AKL | 0.72 | 37.2 | 39 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 6 calls published at P ≥ 70%**, 6 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| CX 520 | 2026-10-04 | CPA | NRT | 0.68 | 27.6 | -2 min |
| VJ 985 | 2026-10-10 | VJC | PQC | 0.67 | 32.9 | 3 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3127 | 0.6704 | 0.1328 | 0.4259 | 13.9 | 2026-10-03T07:13:31+00:00 | 2026-10-10T14:53:49+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3127}
