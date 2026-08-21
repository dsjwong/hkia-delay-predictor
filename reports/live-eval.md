# Live evaluation — predictions vs actuals

Generated 2026-08-21T18:54:52+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2107**.

Dates 2026-08-17..2026-08-22; observed P(delay > 15) = 0.2587; median lead time between last score and departure = 26.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6559 | 0.1825 | 0.5473 | 15.843 |
| baseline_airline_hour | 0.6406 | 0.1823 | 0.5484 | 17.821 |
| naive_rate | 0.5 | 0.1918 | 0.5717 | 15.989 |

Coverage: **2107 of 2267** departures in the window (92.9%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2107 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0153 | [-0.0098, +0.0392] | no — CI straddles 0 |
| brier | +0.0002 | [-0.0047, +0.0052] | no — CI straddles 0 |
| logloss | -0.0011 | [-0.0138, +0.0116] | no — CI straddles 0 |
| mae | -1.98 | [-2.3172, -1.6227] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-17 † | 293 | 0.2287 | 0.5923 | 0.5372 | 0.1726 | 16.2 | 20.3 |
| 2026-08-18 | 440 | 0.2386 | 0.7012 | 0.6549 | 0.1635 | 14.2 | 17.3 |
| 2026-08-19 | 439 | 0.1845 | 0.5825 | 0.6825 | 0.1530 | 11.9 | 15.2 |
| 2026-08-20 | 440 | 0.3250 | 0.6489 | 0.6859 | 0.2145 | 19.3 | 18.9 |
| 2026-08-21 | 461 | 0.3059 | 0.6261 | 0.6224 | 0.2057 | 17.9 | 18.4 |
| 2026-08-22 *† | 34 | 0.2353 | 0.6490 | 0.5913 | 0.1626 | 12.4 | 14.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 449 | 0.6548 | 0.5987 | 0.5642 | 28.4 |
| < 30 min | 1042 | 0.1804 | 0.6732 | 0.6732 | 13.3 |
| 30–120 min | 598 | 0.1037 | 0.6691 | 0.7093 | 11.1 |
| 2–12 h * | 18 | 0.0556 | 0.4118 | 0.3529 | 9.9 |
| > 12 h * | 0 | — | — | — | — |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 223 | 0.072 | 0.099 |
| 0.1-0.2 | 540 | 0.150 | 0.193 |
| 0.2-0.3 | 502 | 0.249 | 0.227 |
| 0.3-0.4 | 402 | 0.348 | 0.279 |
| 0.4-0.5 | 231 | 0.443 | 0.429 |
| 0.5-0.6 | 125 | 0.543 | 0.400 |
| 0.6-0.7 | 58 | 0.640 | 0.483 |
| 0.7-0.8 * | 15 | 0.733 | 0.333 |
| 0.8-0.9 * | 11 | 0.838 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-18 | RNA | KTM | 0.88 | 59.3 | 235 min |
| VJ 985 | 2026-08-18 | VJC | PQC | 0.87 | 39.9 | 28 min |
| VJ 985 | 2026-08-20 | VJC | PQC | 0.86 | 43.7 | 24 min |
| VJ 877 | 2026-08-21 | VJC | SGN | 0.85 | 53.5 | 23 min |
| LX 139 | 2026-08-18 | SWR | ZRH | 0.84 | 30.7 | 37 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 26 calls published at P ≥ 70%**, 16 were actually more than 15 minutes late (62%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 616 | 2026-08-18 | HKE | ICN | 0.03 | -4.1 | 147 min |
| TW 640 | 2026-08-21 | TWB | PUS | 0.04 | -2.1 | 77 min |
| MH 073 | 2026-08-19 | MAS | KUL | 0.05 | 3.7 | 36 min |
| OD 606 | 2026-08-18 | MXD | KUL | 0.79 | 65.1 | 0 min |
| CX 239 | 2026-08-20 | CPA | LHR | 0.77 | 32.5 | -4 min |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 2107}
