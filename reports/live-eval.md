# Live evaluation — predictions vs actuals

Generated 2026-11-22T23:35:34+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2901**.

Dates 2026-11-16..2026-11-23; observed P(delay > 15) = 0.1755; median lead time between last score and departure = 229.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6224 | 0.1443 | 0.4605 | 12.84 |
| baseline_airline_hour | 0.5713 | 0.1542 | 0.4871 | 15.893 |
| naive_rate | 0.5 | 0.1447 | 0.4644 | 12.152 |

Coverage: **2901 of 2945** departures in the window (98.5%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2901 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0511 | [+0.0233, +0.0778] | **yes** |
| brier | -0.0099 | [-0.0130, -0.0068] | **yes** |
| logloss | -0.0266 | [-0.0351, -0.0178] | **yes** |
| mae | -3.05 | [-3.2967, -2.8026] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-16 † | 368 | 0.1495 | 0.6543 | 0.5804 | 0.1219 | 13.3 | 17.8 |
| 2026-11-17 | 398 | 0.1734 | 0.5931 | 0.5742 | 0.1400 | 13.8 | 18.2 |
| 2026-11-18 | 409 | 0.2152 | 0.6962 | 0.6051 | 0.1520 | 12.7 | 15.7 |
| 2026-11-19 | 406 | 0.1478 | 0.5617 | 0.5470 | 0.1366 | 12.7 | 15.2 |
| 2026-11-20 | 424 | 0.2476 | 0.5754 | 0.5410 | 0.1892 | 14.3 | 15.3 |
| 2026-11-21 | 430 | 0.1605 | 0.5796 | 0.5807 | 0.1561 | 13.0 | 15.2 |
| 2026-11-22 | 427 | 0.1358 | 0.6490 | 0.5757 | 0.1155 | 10.5 | 14.7 |
| 2026-11-23 *† | 39 | 0.1282 | 0.8176 | 0.6765 | 0.0969 | 8.3 | 10.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 62 | 0.6774 | 0.6726 | 0.5512 | 57.8 |
| < 30 min | 174 | 0.1494 | 0.6983 | 0.5890 | 15.2 |
| 30–120 min | 561 | 0.1979 | 0.6193 | 0.5521 | 13.5 |
| 2–12 h | 1990 | 0.1578 | 0.6175 | 0.5663 | 11.3 |
| > 12 h | 114 | 0.1404 | 0.7089 | 0.6489 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 366 | 0.071 | 0.087 |
| 0.1-0.2 | 978 | 0.153 | 0.152 |
| 0.2-0.3 | 866 | 0.245 | 0.156 |
| 0.3-0.4 | 452 | 0.343 | 0.239 |
| 0.4-0.5 | 178 | 0.435 | 0.303 |
| 0.5-0.6 | 47 | 0.542 | 0.532 |
| 0.6-0.7 * | 10 | 0.630 | 0.300 |
| 0.7-0.8 * | 2 | 0.741 | 1.000 |
| 0.8-0.9 * | 1 | 0.854 | 1.000 |
| 0.9-1.0 * | 1 | 0.912 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-17 | RNA | KTM | 0.85 | 47.8 | 188 min |
| VJ 985 | 2026-11-21 | VJC | PQC | 0.74 | 33.0 | 135 min |
| VJ 985 | 2026-11-19 | VJC | PQC | 0.74 | 35.8 | 47 min |
| VJ 877 | 2026-11-21 | VJC | SGN | 0.67 | 35.5 | 90 min |
| OD 606 | 2026-11-18 | MXD | KUL | 0.63 | 41.4 | 264 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CZ 356 | 2026-11-17 | CSN | PKX | 0.04 | -5.7 | 23 min |
| CA 110 | 2026-11-17 | CCA | PEK | 0.05 | -3.1 | 87 min |
| EY 871 | 2026-11-22 | ETD | AUH | 0.05 | 8.4 | 49 min |
| RA 410 | 2026-11-21 | RNA | KTM | 0.91 | 54.4 | 12 min |
| JX 236 | 2026-11-21 | SJX | TPE | 0.66 | 23.1 | -1 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| e2c2178@2026-11-22T11:25:36+00:00 * | 10 | 0.8889 | 0.0815 | 0.2719 | 17.9 | 2026-11-22T17:57:19+00:00 | 2026-11-22T17:57:19+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 2891 | 0.6218 | 0.1445 | 0.4611 | 12.8 | 2026-11-15T21:24:35+00:00 | 2026-11-22T10:28:12+00:00 |

`*` = thin (< 100 flights — AUC standard error is large, treat as noise). Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'e2c2178@2026-11-22T11:25:36+00:00': 10, 'f6ae66c@2026-11-01T10:28:21+00:00': 2891}
