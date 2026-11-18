# Live evaluation — predictions vs actuals

Generated 2026-11-18T00:56:44+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2806**.

Dates 2026-11-11..2026-11-18; observed P(delay > 15) = 0.1518; median lead time between last score and departure = 216.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6186 | 0.13 | 0.4258 | 12.323 |
| baseline_airline_hour | 0.5843 | 0.1456 | 0.467 | 16.681 |
| naive_rate | 0.5 | 0.1288 | 0.4258 | 11.608 |

Coverage: **2806 of 2887** departures in the window (97.2%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2806 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0343 | [+0.0044, +0.0654] | **yes** |
| brier | -0.0156 | [-0.0192, -0.0121] | **yes** |
| logloss | -0.0412 | [-0.0515, -0.0314] | **yes** |
| mae | -4.36 | [-4.6645, -4.0712] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-11 † | 315 | 0.1175 | 0.5746 | 0.5688 | 0.1095 | 10.9 | 17.2 |
| 2026-11-12 | 396 | 0.1212 | 0.6581 | 0.6283 | 0.1036 | 8.7 | 14.7 |
| 2026-11-13 | 416 | 0.1298 | 0.6018 | 0.6843 | 0.1168 | 10.2 | 14.7 |
| 2026-11-14 | 416 | 0.1659 | 0.6539 | 0.5838 | 0.1521 | 15.9 | 17.4 |
| 2026-11-15 | 418 | 0.1890 | 0.6041 | 0.5398 | 0.1556 | 13.5 | 16.9 |
| 2026-11-16 | 412 | 0.1505 | 0.6417 | 0.5768 | 0.1226 | 12.9 | 17.6 |
| 2026-11-17 | 398 | 0.1734 | 0.5931 | 0.5729 | 0.1400 | 13.8 | 18.8 |
| 2026-11-18 *† | 35 | 0.2286 | 0.7361 | 0.4977 | 0.1744 | 10.8 | 12.9 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 65 | 0.6154 | 0.5350 | 0.4310 | 54.0 |
| < 30 min | 185 | 0.1568 | 0.7162 | 0.5174 | 16.8 |
| 30–120 min | 615 | 0.1496 | 0.6297 | 0.6493 | 11.2 |
| 2–12 h | 1831 | 0.1382 | 0.6078 | 0.5650 | 10.9 |
| > 12 h | 110 | 0.1091 | 0.6497 | 0.6186 | 10.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 536 | 0.072 | 0.084 |
| 0.1-0.2 | 1012 | 0.150 | 0.141 |
| 0.2-0.3 | 741 | 0.242 | 0.136 |
| 0.3-0.4 | 334 | 0.344 | 0.240 |
| 0.4-0.5 | 128 | 0.442 | 0.219 |
| 0.5-0.6 | 36 | 0.543 | 0.500 |
| 0.6-0.7 * | 13 | 0.626 | 0.538 |
| 0.7-0.8 * | 4 | 0.751 | 0.500 |
| 0.8-0.9 * | 1 | 0.854 | 1.000 |
| 0.9-1.0 * | 1 | 0.912 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-14 | RNA | KTM | 0.91 | 55.8 | 83 min |
| RA 410 | 2026-11-17 | RNA | KTM | 0.85 | 47.8 | 188 min |
| LX 139 | 2026-11-14 | SWR | ZRH | 0.79 | 32.6 | 30 min |
| VJ 985 | 2026-11-14 | VJC | PQC | 0.74 | 34.4 | 219 min |
| QF 128 | 2026-11-15 | QFA | SYD | 0.67 | 23.7 | 66 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 6 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (67%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-11-12 | HKE | HND | 0.03 | -4.9 | 33 min |
| CZ 356 | 2026-11-17 | CSN | PKX | 0.04 | -5.7 | 23 min |
| CA 110 | 2026-11-17 | CCA | PEK | 0.05 | -3.1 | 87 min |
| LX 139 | 2026-11-15 | SWR | ZRH | 0.74 | 31.0 | 8 min |
| QF 128 | 2026-11-14 | QFA | SYD | 0.73 | 30.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2806 | 0.6186 | 0.1300 | 0.4258 | 12.3 | 2026-11-10T19:00:09+00:00 | 2026-11-17T10:53:56+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2806}
