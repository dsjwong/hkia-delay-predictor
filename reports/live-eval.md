# Live evaluation — predictions vs actuals

Generated 2026-09-07T21:30:08+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2833**.

Dates 2026-09-01..2026-09-08; observed P(delay > 15) = 0.1532; median lead time between last score and departure = 122.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6589 | 0.1377 | 0.4359 | 11.969 |
| baseline_airline_hour | 0.6291 | 0.1438 | 0.4599 | 15.935 |
| naive_rate | 0.5 | 0.1297 | 0.4282 | 10.463 |

Coverage: **2833 of 2869** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2833 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0298 | [+0.0056, +0.0572] | **yes** |
| brier | -0.0061 | [-0.0100, -0.0022] | **yes** |
| logloss | -0.0240 | [-0.0346, -0.0141] | **yes** |
| mae | -3.97 | [-4.2966, -3.6433] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-01 † | 367 | 0.1744 | 0.5686 | 0.6295 | 0.1976 | 15.6 | 15.8 |
| 2026-09-02 | 405 | 0.1802 | 0.6607 | 0.6256 | 0.1432 | 12.3 | 16.6 |
| 2026-09-03 | 393 | 0.1578 | 0.6067 | 0.5606 | 0.1317 | 10.8 | 16.0 |
| 2026-09-04 | 418 | 0.1770 | 0.7245 | 0.6272 | 0.1309 | 10.7 | 15.6 |
| 2026-09-05 | 410 | 0.1195 | 0.6704 | 0.6390 | 0.1133 | 10.8 | 16.3 |
| 2026-09-06 | 410 | 0.1732 | 0.6271 | 0.6146 | 0.1686 | 14.4 | 15.0 |
| 2026-09-07 | 400 | 0.0975 | 0.7261 | 0.7205 | 0.0904 | 9.9 | 16.5 |
| 2026-09-08 *† | 30 | 0.0667 | 0.9821 | 0.7500 | 0.0471 | 7.2 | 12.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 87 | 0.6667 | 0.6831 | 0.5288 | 35.3 |
| < 30 min | 323 | 0.1548 | 0.6561 | 0.6062 | 10.2 |
| 30–120 min | 1039 | 0.1473 | 0.6626 | 0.6102 | 10.7 |
| 2–12 h | 1375 | 0.1258 | 0.6618 | 0.6687 | 11.9 |
| > 12 h * | 9 | 0.0000 | — | — | 5.7 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 606 | 0.064 | 0.053 |
| 0.1-0.2 | 862 | 0.147 | 0.128 |
| 0.2-0.3 | 676 | 0.246 | 0.173 |
| 0.3-0.4 | 318 | 0.342 | 0.277 |
| 0.4-0.5 | 192 | 0.450 | 0.240 |
| 0.5-0.6 | 101 | 0.546 | 0.218 |
| 0.6-0.7 | 61 | 0.645 | 0.213 |
| 0.7-0.8 * | 16 | 0.732 | 0.312 |
| 0.8-0.9 * | 1 | 0.806 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-09-01 | RNA | KTM | 0.81 | 45.1 | 182 min |
| CX 548 | 2026-09-01 | CPA | HND | 0.76 | 33.8 | 43 min |
| HX 608 | 2026-09-06 | CRK | NRT | 0.75 | 31.4 | 24 min |
| HX 618 | 2026-09-06 | CRK | KIX | 0.74 | 35.0 | 25 min |
| NH 812 | 2026-09-06 | ANA | NRT | 0.72 | 30.4 | 23 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 17 calls published at P ≥ 70%**, 6 were actually more than 15 minutes late (35%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 704 | 2026-09-03 | HKE | BKK | 0.02 | -2.8 | 21 min |
| NH 814 | 2026-09-03 | ANA | HND | 0.03 | -4.8 | 21 min |
| KE 2012 | 2026-09-05 | KAL | ICN | 0.03 | -2.5 | 161 min |
| CX 520 | 2026-09-01 | CPA | NRT | 0.76 | 40.9 | 7 min |
| DL 088 | 2026-09-06 | DAL | LAX | 0.74 | 38.0 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2833 | 0.6589 | 0.1377 | 0.4359 | 12.0 | 2026-08-31T20:27:22+00:00 | 2026-09-07T13:06:57+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2833}
