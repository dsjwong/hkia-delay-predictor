# Live evaluation — predictions vs actuals

Generated 2026-08-23T18:47:17+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3012**.

Dates 2026-08-17..2026-08-24; observed P(delay > 15) = 0.2699; median lead time between last score and departure = 29.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6441 | 0.1892 | 0.5623 | 15.814 |
| baseline_airline_hour | 0.6418 | 0.1869 | 0.558 | 17.62 |
| naive_rate | 0.5 | 0.1971 | 0.5832 | 16.019 |

Coverage: **3012 of 3172** departures in the window (95.0%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3012 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0023 | [-0.0176, +0.0226] | no — CI straddles 0 |
| brier | +0.0023 | [-0.0015, +0.0060] | no — CI straddles 0 |
| logloss | +0.0043 | [-0.0054, +0.0140] | no — CI straddles 0 |
| mae | -1.81 | [-2.1012, -1.5227] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-17 † | 293 | 0.2287 | 0.5923 | 0.5372 | 0.1726 | 16.2 | 20.3 |
| 2026-08-18 | 440 | 0.2386 | 0.7012 | 0.6549 | 0.1635 | 14.2 | 17.3 |
| 2026-08-19 | 439 | 0.1845 | 0.5825 | 0.6825 | 0.1530 | 11.9 | 15.2 |
| 2026-08-20 | 440 | 0.3250 | 0.6489 | 0.6859 | 0.2145 | 19.3 | 18.9 |
| 2026-08-21 | 461 | 0.3059 | 0.6261 | 0.6224 | 0.2057 | 17.9 | 18.4 |
| 2026-08-22 | 451 | 0.3902 | 0.5617 | 0.6620 | 0.2495 | 19.4 | 18.9 |
| 2026-08-23 | 451 | 0.2129 | 0.6000 | 0.6187 | 0.1660 | 12.7 | 15.9 |
| 2026-08-24 *† | 37 | 0.1081 | 0.8712 | 0.6818 | 0.0920 | 5.4 | 8.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 598 | 0.6605 | 0.5850 | 0.5829 | 29.5 |
| < 30 min | 1366 | 0.2035 | 0.6475 | 0.6565 | 13.6 |
| 30–120 min | 921 | 0.1401 | 0.6193 | 0.6594 | 11.3 |
| 2–12 h | 125 | 0.0880 | 0.5789 | 0.7145 | 7.7 |
| > 12 h * | 2 | 0.0000 | — | — | 7.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 279 | 0.073 | 0.097 |
| 0.1-0.2 | 764 | 0.154 | 0.202 |
| 0.2-0.3 | 805 | 0.250 | 0.252 |
| 0.3-0.4 | 557 | 0.347 | 0.300 |
| 0.4-0.5 | 321 | 0.445 | 0.421 |
| 0.5-0.6 | 174 | 0.542 | 0.408 |
| 0.6-0.7 | 77 | 0.640 | 0.442 |
| 0.7-0.8 * | 19 | 0.730 | 0.368 |
| 0.8-0.9 * | 16 | 0.838 | 0.938 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| RA 410 | 2026-08-18 | RNA | KTM | 0.88 | 59.3 | 235 min |
| VJ 985 | 2026-08-18 | VJC | PQC | 0.87 | 39.9 | 28 min |
| VJ 985 | 2026-08-20 | VJC | PQC | 0.86 | 43.7 | 24 min |
| VJ 985 | 2026-08-22 | VJC | PQC | 0.85 | 48.7 | 19 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 35 calls published at P ≥ 70%**, 22 were actually more than 15 minutes late (63%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 616 | 2026-08-18 | HKE | ICN | 0.03 | -4.1 | 147 min |
| TW 640 | 2026-08-21 | TWB | PUS | 0.04 | -2.1 | 77 min |
| MH 073 | 2026-08-19 | MAS | KUL | 0.05 | 3.7 | 36 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |
| OD 606 | 2026-08-18 | MXD | KUL | 0.79 | 65.1 | 0 min |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 3012}
