# Live evaluation — predictions vs actuals

Generated 2026-08-20T07:35:39+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **1402**.

Dates 2026-08-17..2026-08-20; observed P(delay > 15) = 0.2375; median lead time between last score and departure = 25.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6635 | 0.1681 | 0.5148 | 14.571 |
| baseline_airline_hour | 0.6466 | 0.1734 | 0.5271 | 17.4 |
| naive_rate | 0.5 | 0.1811 | 0.5482 | 15.003 |

Coverage: **1402 of 1562** departures in the window (89.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 1402 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0169 | [-0.0127, +0.0487] | no — CI straddles 0 |
| brier | -0.0053 | [-0.0107, +0.0002] | no — CI straddles 0 |
| logloss | -0.0123 | [-0.0262, +0.0023] | no — CI straddles 0 |
| mae | -2.83 | [-3.2792, -2.3981] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-17 † | 293 | 0.2287 | 0.5923 | 0.5372 | 0.1726 | 16.2 | 20.3 |
| 2026-08-18 | 440 | 0.2386 | 0.7012 | 0.6549 | 0.1635 | 14.2 | 17.3 |
| 2026-08-19 | 439 | 0.1845 | 0.5825 | 0.6825 | 0.1530 | 11.9 | 15.2 |
| 2026-08-20 † | 230 | 0.3478 | 0.7085 | 0.7267 | 0.1998 | 18.4 | 18.1 |

`†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 286 | 0.6678 | 0.6151 | 0.5747 | 29.9 |
| < 30 min | 705 | 0.1560 | 0.6679 | 0.6833 | 11.1 |
| 30–120 min | 399 | 0.0802 | 0.6618 | 0.7140 | 10.0 |
| 2–12 h * | 12 | 0.0000 | — | — | 4.7 |
| > 12 h * | 0 | — | — | — | — |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 204 | 0.071 | 0.098 |
| 0.1-0.2 | 458 | 0.149 | 0.188 |
| 0.2-0.3 | 344 | 0.246 | 0.230 |
| 0.3-0.4 | 237 | 0.343 | 0.295 |
| 0.4-0.5 | 93 | 0.440 | 0.387 |
| 0.5-0.6 | 40 | 0.539 | 0.600 |
| 0.6-0.7 * | 12 | 0.649 | 0.750 |
| 0.7-0.8 * | 8 | 0.748 | 0.375 |
| 0.8-0.9 * | 6 | 0.843 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-18 | RNA | KTM | 0.88 | 59.3 | 235 min |
| VJ 985 | 2026-08-18 | VJC | PQC | 0.87 | 39.9 | 28 min |
| LX 139 | 2026-08-18 | SWR | ZRH | 0.84 | 30.7 | 37 min |
| LX 139 | 2026-08-17 | SWR | ZRH | 0.84 | 32.8 | 24 min |
| CX 506 | 2026-08-20 | CPA | KIX | 0.81 | 42.0 | 105 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 14 calls published at P ≥ 70%**, 9 were actually more than 15 minutes late (64%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 616 | 2026-08-18 | HKE | ICN | 0.03 | -4.1 | 147 min |
| MH 073 | 2026-08-19 | MAS | KUL | 0.05 | 3.7 | 36 min |
| EK 385 | 2026-08-17 | UAE | BKK | 0.06 | 2.8 | 159 min |
| OD 606 | 2026-08-18 | MXD | KUL | 0.79 | 65.1 | 0 min |
| CX 239 | 2026-08-20 | CPA | LHR | 0.77 | 32.5 | -4 min |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 1402}
