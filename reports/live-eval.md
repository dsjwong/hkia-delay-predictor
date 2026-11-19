# Live evaluation — predictions vs actuals

Generated 2026-11-19T00:20:05+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2823**.

Dates 2026-11-12..2026-11-19; observed P(delay > 15) = 0.1658; median lead time between last score and departure = 224.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6302 | 0.1368 | 0.4419 | 12.651 |
| baseline_airline_hour | 0.5894 | 0.1507 | 0.4788 | 16.686 |
| naive_rate | 0.5 | 0.1383 | 0.4491 | 12.205 |

Coverage: **2823 of 2885** departures in the window (97.9%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2823 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0408 | [+0.0114, +0.0689] | **yes** |
| brier | -0.0139 | [-0.0174, -0.0102] | **yes** |
| logloss | -0.0369 | [-0.0464, -0.0265] | **yes** |
| mae | -4.04 | [-4.3280, -3.7302] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-12 † | 334 | 0.1377 | 0.6460 | 0.5931 | 0.1150 | 9.0 | 15.4 |
| 2026-11-13 | 416 | 0.1298 | 0.6018 | 0.6843 | 0.1168 | 10.2 | 14.7 |
| 2026-11-14 | 416 | 0.1659 | 0.6539 | 0.5838 | 0.1521 | 15.9 | 17.4 |
| 2026-11-15 | 418 | 0.1890 | 0.6041 | 0.5398 | 0.1556 | 13.5 | 16.9 |
| 2026-11-16 | 412 | 0.1505 | 0.6417 | 0.5768 | 0.1226 | 12.9 | 17.6 |
| 2026-11-17 | 398 | 0.1734 | 0.5931 | 0.5729 | 0.1400 | 13.8 | 18.8 |
| 2026-11-18 | 409 | 0.2152 | 0.6962 | 0.6021 | 0.1520 | 12.7 | 16.2 |
| 2026-11-19 *† | 20 | 0.0500 | 0.2632 | 0.1053 | 0.1172 | 9.9 | 11.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 66 | 0.5909 | 0.5660 | 0.4416 | 54.9 |
| < 30 min | 186 | 0.1720 | 0.7421 | 0.5536 | 16.7 |
| 30–120 min | 580 | 0.1586 | 0.6634 | 0.6686 | 12.3 |
| 2–12 h | 1883 | 0.1551 | 0.6142 | 0.5660 | 11.0 |
| > 12 h | 108 | 0.1204 | 0.5927 | 0.5955 | 10.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 497 | 0.073 | 0.091 |
| 0.1-0.2 | 997 | 0.150 | 0.144 |
| 0.2-0.3 | 756 | 0.241 | 0.148 |
| 0.3-0.4 | 368 | 0.346 | 0.261 |
| 0.4-0.5 | 143 | 0.441 | 0.259 |
| 0.5-0.6 | 40 | 0.542 | 0.550 |
| 0.6-0.7 * | 16 | 0.625 | 0.500 |
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
| f6ae66c@2026-11-01T10:28:21+00:00 | 2823 | 0.6302 | 0.1368 | 0.4419 | 12.7 | 2026-11-11T11:31:51+00:00 | 2026-11-18T09:25:13+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2823}
