# Live evaluation — predictions vs actuals

Generated 2026-08-22T18:48:12+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2557**.

Dates 2026-08-17..2026-08-23; observed P(delay > 15) = 0.2808; median lead time between last score and departure = 27.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6435 | 0.1941 | 0.5735 | 16.447 |
| baseline_airline_hour | 0.6446 | 0.1906 | 0.5664 | 17.981 |
| naive_rate | 0.5 | 0.202 | 0.5937 | 16.598 |

Coverage: **2557 of 2717** departures in the window (94.1%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2557 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | -0.0011 | [-0.0225, +0.0192] | no — CI straddles 0 |
| brier | +0.0035 | [-0.0009, +0.0078] | no — CI straddles 0 |
| logloss | +0.0071 | [-0.0041, +0.0176] | no — CI straddles 0 |
| mae | -1.53 | [-1.8403, -1.2015] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-17 † | 293 | 0.2287 | 0.5923 | 0.5372 | 0.1726 | 16.2 | 20.3 |
| 2026-08-18 | 440 | 0.2386 | 0.7012 | 0.6549 | 0.1635 | 14.2 | 17.3 |
| 2026-08-19 | 439 | 0.1845 | 0.5825 | 0.6825 | 0.1530 | 11.9 | 15.2 |
| 2026-08-20 | 440 | 0.3250 | 0.6489 | 0.6859 | 0.2145 | 19.3 | 18.9 |
| 2026-08-21 | 461 | 0.3059 | 0.6261 | 0.6224 | 0.2057 | 17.9 | 18.4 |
| 2026-08-22 | 452 | 0.3916 | 0.5610 | 0.6623 | 0.2501 | 19.5 | 18.9 |
| 2026-08-23 *† | 32 | 0.1250 | 0.4196 | 0.5580 | 0.1365 | 8.8 | 10.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 545 | 0.6606 | 0.5863 | 0.5847 | 29.7 |
| < 30 min | 1236 | 0.2031 | 0.6601 | 0.6697 | 13.6 |
| 30–120 min | 742 | 0.1375 | 0.6321 | 0.6720 | 11.8 |
| 2–12 h * | 34 | 0.1471 | 0.6276 | 0.7034 | 9.0 |
| > 12 h * | 0 | — | — | — | — |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 241 | 0.073 | 0.100 |
| 0.1-0.2 | 612 | 0.151 | 0.211 |
| 0.2-0.3 | 644 | 0.250 | 0.259 |
| 0.3-0.4 | 483 | 0.348 | 0.313 |
| 0.4-0.5 | 300 | 0.445 | 0.413 |
| 0.5-0.6 | 170 | 0.542 | 0.406 |
| 0.6-0.7 | 74 | 0.641 | 0.446 |
| 0.7-0.8 * | 18 | 0.728 | 0.389 |
| 0.8-0.9 * | 15 | 0.840 | 0.933 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| RA 410 | 2026-08-18 | RNA | KTM | 0.88 | 59.3 | 235 min |
| VJ 985 | 2026-08-18 | VJC | PQC | 0.87 | 39.9 | 28 min |
| VJ 985 | 2026-08-20 | VJC | PQC | 0.86 | 43.7 | 24 min |
| VJ 985 | 2026-08-22 | VJC | PQC | 0.85 | 48.7 | 19 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 33 calls published at P ≥ 70%**, 21 were actually more than 15 minutes late (64%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 616 | 2026-08-18 | HKE | ICN | 0.03 | -4.1 | 147 min |
| TW 640 | 2026-08-21 | TWB | PUS | 0.04 | -2.1 | 77 min |
| MH 073 | 2026-08-19 | MAS | KUL | 0.05 | 3.7 | 36 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |
| OD 606 | 2026-08-18 | MXD | KUL | 0.79 | 65.1 | 0 min |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 2557}
