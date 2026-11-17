# Live evaluation — predictions vs actuals

Generated 2026-11-17T01:52:35+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2763**.

Dates 2026-11-10..2026-11-17; observed P(delay > 15) = 0.1484; median lead time between last score and departure = 206.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6486 | 0.126 | 0.4135 | 11.984 |
| baseline_airline_hour | 0.6093 | 0.1424 | 0.459 | 16.31 |
| naive_rate | 0.5 | 0.1264 | 0.4199 | 11.26 |

Coverage: **2763 of 2878** departures in the window (96.0%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2763 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0393 | [+0.0087, +0.0701] | **yes** |
| brier | -0.0164 | [-0.0199, -0.0129] | **yes** |
| logloss | -0.0455 | [-0.0552, -0.0353] | **yes** |
| mae | -4.33 | [-4.6083, -4.0248] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-10 † | 276 | 0.1884 | 0.7751 | 0.6969 | 0.1340 | 12.3 | 17.3 |
| 2026-11-11 | 396 | 0.1010 | 0.6205 | 0.6142 | 0.0955 | 10.2 | 16.1 |
| 2026-11-12 | 396 | 0.1212 | 0.6581 | 0.6283 | 0.1036 | 8.7 | 14.7 |
| 2026-11-13 | 416 | 0.1298 | 0.6018 | 0.6843 | 0.1168 | 10.2 | 14.7 |
| 2026-11-14 | 416 | 0.1659 | 0.6539 | 0.5838 | 0.1521 | 15.9 | 17.4 |
| 2026-11-15 | 418 | 0.1890 | 0.6041 | 0.5398 | 0.1556 | 13.5 | 16.9 |
| 2026-11-16 | 412 | 0.1505 | 0.6417 | 0.5768 | 0.1226 | 12.9 | 17.6 |
| 2026-11-17 *† | 33 | 0.1818 | 0.6451 | 0.6852 | 0.1500 | 11.9 | 14.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 70 | 0.6143 | 0.5866 | 0.4681 | 52.0 |
| < 30 min | 195 | 0.1590 | 0.6959 | 0.5395 | 13.0 |
| 30–120 min | 630 | 0.1460 | 0.6611 | 0.6529 | 10.3 |
| 2–12 h | 1779 | 0.1321 | 0.6437 | 0.5999 | 11.0 |
| > 12 h * | 89 | 0.1011 | 0.6347 | 0.5882 | 9.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 528 | 0.071 | 0.066 |
| 0.1-0.2 | 991 | 0.150 | 0.126 |
| 0.2-0.3 | 724 | 0.243 | 0.141 |
| 0.3-0.4 | 341 | 0.343 | 0.276 |
| 0.4-0.5 | 123 | 0.441 | 0.211 |
| 0.5-0.6 | 36 | 0.542 | 0.500 |
| 0.6-0.7 * | 15 | 0.626 | 0.467 |
| 0.7-0.8 * | 4 | 0.751 | 0.500 |
| 0.9-1.0 * | 1 | 0.912 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-14 | RNA | KTM | 0.91 | 55.8 | 83 min |
| LX 139 | 2026-11-14 | SWR | ZRH | 0.79 | 32.6 | 30 min |
| VJ 985 | 2026-11-14 | VJC | PQC | 0.74 | 34.4 | 219 min |
| QF 128 | 2026-11-15 | QFA | SYD | 0.67 | 23.7 | 66 min |
| VJ 877 | 2026-11-15 | VJC | SGN | 0.64 | 38.4 | 83 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 5 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (60%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-11-12 | HKE | HND | 0.03 | -4.9 | 33 min |
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| UO 132 | 2026-11-10 | HKE | KHH | 0.05 | -1.1 | 36 min |
| LX 139 | 2026-11-15 | SWR | ZRH | 0.74 | 31.0 | 8 min |
| QF 128 | 2026-11-14 | QFA | SYD | 0.73 | 30.4 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2763 | 0.6486 | 0.1260 | 0.4135 | 12.0 | 2026-11-08T23:16:00+00:00 | 2026-11-16T08:08:24+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2763}
