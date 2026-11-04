# Live evaluation — predictions vs actuals

Generated 2026-11-04T23:38:50+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2882**.

Dates 2026-10-28..2026-11-05; observed P(delay > 15) = 0.1381; median lead time between last score and departure = 201.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.651 | 0.1134 | 0.3832 | 10.705 |
| baseline_airline_hour | 0.6364 | 0.1362 | 0.4455 | 16.17 |
| naive_rate | 0.5 | 0.119 | 0.4015 | 10.851 |

Coverage: **2882 of 3344** departures in the window (86.2%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2882 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0146 | [-0.0119, +0.0400] | no — CI straddles 0 |
| brier | -0.0228 | [-0.0265, -0.0191] | **yes** |
| logloss | -0.0623 | [-0.0736, -0.0514] | **yes** |
| mae | -5.46 | [-5.7984, -5.1303] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-28 *† | 1 | 1.0000 | — | — | 0.8772 | 585.8 | 575.6 |
| 2026-10-29 | 371 | 0.1644 | 0.5882 | 0.6135 | 0.1375 | 12.3 | 17.7 |
| 2026-10-30 | 424 | 0.1651 | 0.7570 | 0.7107 | 0.1204 | 11.6 | 16.1 |
| 2026-10-31 | 433 | 0.1085 | 0.7025 | 0.6898 | 0.0958 | 9.7 | 15.0 |
| 2026-11-01 | 418 | 0.1172 | 0.6891 | 0.6486 | 0.0984 | 9.9 | 15.7 |
| 2026-11-02 | 406 | 0.1478 | 0.6486 | 0.6369 | 0.1172 | 10.6 | 15.9 |
| 2026-11-03 | 400 | 0.1450 | 0.5864 | 0.5885 | 0.1219 | 10.8 | 16.7 |
| 2026-11-04 | 395 | 0.1114 | 0.6438 | 0.6115 | 0.0980 | 8.9 | 15.4 |
| 2026-11-05 *† | 34 | 0.2353 | 0.5529 | 0.3029 | 0.1843 | 9.2 | 10.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 65 | 0.5846 | 0.5322 | 0.5292 | 51.5 |
| < 30 min | 241 | 0.1328 | 0.6172 | 0.6702 | 9.4 |
| 30–120 min | 673 | 0.1278 | 0.6960 | 0.6835 | 9.4 |
| 2–12 h | 1736 | 0.1302 | 0.6533 | 0.6378 | 10.1 |
| > 12 h | 167 | 0.0958 | 0.5677 | 0.4874 | 8.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 825 | 0.068 | 0.080 |
| 0.1-0.2 | 1254 | 0.148 | 0.124 |
| 0.2-0.3 | 609 | 0.238 | 0.169 |
| 0.3-0.4 | 154 | 0.338 | 0.299 |
| 0.4-0.5 * | 23 | 0.438 | 0.609 |
| 0.5-0.6 * | 11 | 0.554 | 0.818 |
| 0.6-0.7 * | 5 | 0.656 | 0.600 |
| 0.7-0.8 * | 1 | 0.793 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-31 | RNA | KTM | 0.79 | 41.3 | 55 min |
| LX 139 | 2026-11-02 | SWR | ZRH | 0.68 | 27.3 | 40 min |
| LX 139 | 2026-10-30 | SWR | ZRH | 0.67 | 27.1 | 39 min |
| LX 139 | 2026-11-01 | SWR | ZRH | 0.64 | 27.3 | 40 min |
| OD 606 | 2026-11-02 | MXD | KUL | 0.60 | 39.1 | 92 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| EK 381 | 2026-11-02 | UAE | DXB | 0.03 | -0.4 | 26 min |
| QR 817 | 2026-10-29 | QTR | DOH | 0.03 | 3.0 | 19 min |
| QR 817 | 2026-11-02 | QTR | DOH | 0.03 | 4.3 | 37 min |
| VJ 985 | 2026-10-31 | VJC | PQC | 0.65 | 26.4 | -3 min |
| VJ 985 | 2026-10-29 | VJC | PQC | 0.64 | 25.4 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 1244 | 0.7183 | 0.1064 | 0.3611 | 10.5 | 2026-10-29T19:04:17+00:00 | 2026-11-01T09:29:58+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 410 | 0.5808 | 0.1317 | 0.4348 | 13.1 | 2026-10-27T19:44:32+00:00 | 2026-10-29T13:25:39+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 1228 | 0.6207 | 0.1144 | 0.3883 | 10.1 | 2026-11-01T16:14:42+00:00 | 2026-11-04T11:42:04+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 1244, '4a4212f@2026-08-25T09:35:34+00:00': 410, 'f6ae66c@2026-11-01T10:28:21+00:00': 1228}
