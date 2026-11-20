# Live evaluation — predictions vs actuals

Generated 2026-11-20T23:58:50+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2869**.

Dates 2026-11-14..2026-11-21; observed P(delay > 15) = 0.1861; median lead time between last score and departure = 222.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.622 | 0.1506 | 0.4763 | 13.697 |
| baseline_airline_hour | 0.5612 | 0.1622 | 0.5058 | 16.941 |
| naive_rate | 0.5 | 0.1515 | 0.4806 | 12.855 |

Coverage: **2869 of 2922** departures in the window (98.2%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2869 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0608 | [+0.0354, +0.0861] | **yes** |
| brier | -0.0116 | [-0.0148, -0.0083] | **yes** |
| logloss | -0.0295 | [-0.0383, -0.0205] | **yes** |
| mae | -3.24 | [-3.5208, -2.9820] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-14 † | 363 | 0.1570 | 0.7069 | 0.6146 | 0.1485 | 16.4 | 18.2 |
| 2026-11-15 | 418 | 0.1890 | 0.6041 | 0.5398 | 0.1556 | 13.5 | 16.9 |
| 2026-11-16 | 412 | 0.1505 | 0.6417 | 0.5768 | 0.1226 | 12.9 | 17.6 |
| 2026-11-17 | 398 | 0.1734 | 0.5931 | 0.5729 | 0.1400 | 13.8 | 18.8 |
| 2026-11-18 | 409 | 0.2152 | 0.6962 | 0.6021 | 0.1520 | 12.7 | 16.2 |
| 2026-11-19 | 406 | 0.1478 | 0.5617 | 0.5381 | 0.1366 | 12.7 | 15.8 |
| 2026-11-20 | 424 | 0.2476 | 0.5754 | 0.5408 | 0.1892 | 14.3 | 15.8 |
| 2026-11-21 *† | 39 | 0.3590 | 0.5871 | 0.5743 | 0.2313 | 12.0 | 12.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 74 | 0.6622 | 0.5682 | 0.4604 | 55.7 |
| < 30 min | 201 | 0.1692 | 0.7307 | 0.5677 | 16.6 |
| 30–120 min | 601 | 0.1797 | 0.6094 | 0.5615 | 13.6 |
| 2–12 h | 1899 | 0.1743 | 0.6223 | 0.5586 | 12.0 |
| > 12 h * | 94 | 0.1277 | 0.6362 | 0.6382 | 10.1 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 332 | 0.073 | 0.105 |
| 0.1-0.2 | 907 | 0.153 | 0.157 |
| 0.2-0.3 | 826 | 0.245 | 0.154 |
| 0.3-0.4 | 515 | 0.346 | 0.241 |
| 0.4-0.5 | 209 | 0.439 | 0.301 |
| 0.5-0.6 | 55 | 0.546 | 0.527 |
| 0.6-0.7 * | 18 | 0.626 | 0.500 |
| 0.7-0.8 * | 5 | 0.749 | 0.600 |
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
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 7 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (71%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CZ 356 | 2026-11-17 | CSN | PKX | 0.04 | -5.7 | 23 min |
| CA 110 | 2026-11-17 | CCA | PEK | 0.05 | -3.1 | 87 min |
| KE 2002 | 2026-11-19 | KAL | ICN | 0.06 | 4.7 | 20 min |
| LX 139 | 2026-11-15 | SWR | ZRH | 0.74 | 31.0 | 8 min |
| QF 128 | 2026-11-14 | QFA | SYD | 0.73 | 30.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2869 | 0.6220 | 0.1506 | 0.4763 | 13.7 | 2026-11-13T18:37:40+00:00 | 2026-11-20T13:42:12+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2869}
