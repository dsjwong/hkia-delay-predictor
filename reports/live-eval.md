# Live evaluation — predictions vs actuals

Generated 2026-09-17T21:20:14+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2811**.

Dates 2026-09-11..2026-09-18; observed P(delay > 15) = 0.1405; median lead time between last score and departure = 128.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.7056 | 0.1152 | 0.38 | 11.447 |
| baseline_airline_hour | 0.6721 | 0.1364 | 0.4424 | 16.613 |
| naive_rate | 0.5 | 0.1208 | 0.4059 | 11.247 |

Coverage: **2811 of 2847** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2811 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0335 | [+0.0098, +0.0568] | **yes** |
| brier | -0.0212 | [-0.0245, -0.0176] | **yes** |
| logloss | -0.0624 | [-0.0720, -0.0523] | **yes** |
| mae | -5.17 | [-5.4867, -4.8158] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-11 † | 380 | 0.1553 | 0.7019 | 0.6849 | 0.1222 | 9.7 | 14.4 |
| 2026-09-12 | 406 | 0.1429 | 0.7051 | 0.7068 | 0.1160 | 10.8 | 15.7 |
| 2026-09-13 | 413 | 0.1961 | 0.7214 | 0.7004 | 0.1430 | 14.5 | 18.1 |
| 2026-09-14 | 402 | 0.1617 | 0.6549 | 0.6332 | 0.1327 | 14.9 | 19.4 |
| 2026-09-15 | 386 | 0.0855 | 0.6674 | 0.6061 | 0.0914 | 9.9 | 16.2 |
| 2026-09-16 | 389 | 0.1260 | 0.7551 | 0.6831 | 0.1005 | 9.6 | 15.9 |
| 2026-09-17 | 399 | 0.1203 | 0.7270 | 0.6686 | 0.1020 | 11.0 | 17.1 |
| 2026-09-18 *† | 36 | 0.0556 | 0.1618 | 0.4926 | 0.0834 | 5.9 | 8.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 104 | 0.6731 | 0.6536 | 0.6538 | 51.1 |
| < 30 min | 296 | 0.1655 | 0.6715 | 0.5701 | 9.8 |
| 30–120 min | 998 | 0.1303 | 0.6978 | 0.6492 | 10.4 |
| 2–12 h | 1401 | 0.1042 | 0.7321 | 0.7211 | 9.6 |
| > 12 h * | 12 | 0.0000 | — | — | 4.9 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 756 | 0.063 | 0.042 |
| 0.1-0.2 | 989 | 0.148 | 0.113 |
| 0.2-0.3 | 655 | 0.246 | 0.205 |
| 0.3-0.4 | 279 | 0.342 | 0.251 |
| 0.4-0.5 | 92 | 0.436 | 0.272 |
| 0.5-0.6 * | 29 | 0.540 | 0.517 |
| 0.6-0.7 * | 7 | 0.639 | 0.857 |
| 0.7-0.8 * | 3 | 0.715 | 0.000 |
| 0.8-0.9 * | 1 | 0.821 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LX 139 | 2026-09-13 | SWR | ZRH | 0.82 | 31.8 | 34 min |
| CX 725 | 2026-09-14 | CPA | KUL | 0.68 | 27.4 | 290 min |
| VJ 877 | 2026-09-13 | VJC | SGN | 0.66 | 27.6 | 39 min |
| CX 852 | 2026-09-14 | CPA | SEA | 0.65 | 23.7 | 101 min |
| LX 139 | 2026-09-11 | SWR | ZRH | 0.63 | 23.9 | 61 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (25%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-09-18 | JNA | CJU | 0.03 | -1.2 | 20 min |
| EK 381 | 2026-09-16 | UAE | DXB | 0.03 | -1.1 | 18 min |
| EK 385 | 2026-09-17 | UAE | BKK | 0.04 | 0.0 | 20 min |
| OD 606 | 2026-09-13 | MXD | KUL | 0.73 | 50.7 | -1 min |
| VJ 985 | 2026-09-15 | VJC | PQC | 0.71 | 30.3 | -6 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2811 | 0.7056 | 0.1152 | 0.3800 | 11.4 | 2026-09-10T19:53:25+00:00 | 2026-09-17T17:49:24+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2811}
