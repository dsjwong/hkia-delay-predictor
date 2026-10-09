# Live evaluation — predictions vs actuals

Generated 2026-10-09T22:36:21+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3129**.

Dates 2026-10-03..2026-10-10; observed P(delay > 15) = 0.1566; median lead time between last score and departure = 188.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6648 | 0.1315 | 0.4228 | 13.894 |
| baseline_airline_hour | 0.6513 | 0.1433 | 0.4571 | 17.912 |
| naive_rate | 0.5 | 0.1321 | 0.434 | 12.578 |

Coverage: **3129 of 3170** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3129 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0135 | [-0.0085, +0.0357] | no — CI straddles 0 |
| brier | -0.0118 | [-0.0151, -0.0086] | **yes** |
| logloss | -0.0343 | [-0.0429, -0.0255] | **yes** |
| mae | -4.02 | [-4.2955, -3.7561] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-03 † | 396 | 0.1919 | 0.6366 | 0.5846 | 0.1632 | 15.8 | 18.8 |
| 2026-10-04 | 448 | 0.1786 | 0.7096 | 0.6825 | 0.1381 | 13.6 | 17.2 |
| 2026-10-05 | 451 | 0.1086 | 0.6805 | 0.6774 | 0.1019 | 11.1 | 16.6 |
| 2026-10-06 | 449 | 0.1782 | 0.6253 | 0.6585 | 0.1469 | 18.0 | 20.8 |
| 2026-10-07 | 454 | 0.1784 | 0.6703 | 0.6263 | 0.1402 | 14.8 | 19.0 |
| 2026-10-08 | 444 | 0.1532 | 0.6788 | 0.6782 | 0.1266 | 12.5 | 16.8 |
| 2026-10-09 | 449 | 0.1180 | 0.6776 | 0.6584 | 0.1111 | 12.3 | 16.8 |
| 2026-10-10 *† | 38 | 0.0789 | 0.5762 | 0.5571 | 0.0855 | 7.3 | 11.1 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 97 | 0.7629 | 0.6296 | 0.5420 | 59.7 |
| < 30 min | 227 | 0.1586 | 0.6353 | 0.6105 | 11.0 |
| 30–120 min | 763 | 0.1520 | 0.6742 | 0.6033 | 11.6 |
| 2–12 h | 1977 | 0.1310 | 0.6483 | 0.6643 | 13.1 |
| > 12 h * | 65 | 0.0769 | 0.7883 | 0.7033 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 699 | 0.064 | 0.053 |
| 0.1-0.2 | 929 | 0.148 | 0.130 |
| 0.2-0.3 | 765 | 0.247 | 0.191 |
| 0.3-0.4 | 461 | 0.345 | 0.230 |
| 0.4-0.5 | 182 | 0.439 | 0.220 |
| 0.5-0.6 | 67 | 0.544 | 0.343 |
| 0.6-0.7 * | 18 | 0.634 | 0.556 |
| 0.7-0.8 * | 5 | 0.741 | 0.800 |
| 0.8-0.9 * | 3 | 0.833 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-03 | RNA | KTM | 0.85 | 63.2 | 598 min |
| RA 410 | 2026-10-06 | RNA | KTM | 0.83 | 55.3 | 91 min |
| VJ 985 | 2026-10-03 | VJC | PQC | 0.82 | 38.8 | 19 min |
| CX 302 | 2026-10-04 | CPA | PVG | 0.77 | 32.0 | 79 min |
| CX 161 | 2026-10-04 | CPA | SYD | 0.74 | 31.5 | 35 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 8 calls published at P ≥ 70%**, 7 were actually more than 15 minutes late (88%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 624 | 2026-10-07 | HKE | HND | 0.02 | -8.0 | 56 min |
| NH 814 | 2026-10-06 | ANA | HND | 0.02 | -3.3 | 24 min |
| CA 112 | 2026-10-08 | CCA | PEK | 0.03 | -0.2 | 27 min |
| OD 606 | 2026-10-03 | MXD | KUL | 0.77 | 60.0 | 7 min |
| CX 520 | 2026-10-04 | CPA | NRT | 0.68 | 27.6 | -2 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3129 | 0.6648 | 0.1315 | 0.4228 | 13.9 | 2026-10-02T22:47:14+00:00 | 2026-10-09T13:57:55+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3129}
