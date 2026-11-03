# Live evaluation — predictions vs actuals

Generated 2026-11-03T00:56:07+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2885**.

Dates 2026-10-27..2026-11-03; observed P(delay > 15) = 0.1373; median lead time between last score and departure = 190.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6747 | 0.1117 | 0.3761 | 10.616 |
| baseline_airline_hour | 0.6573 | 0.1347 | 0.4413 | 16.244 |
| naive_rate | 0.5 | 0.1184 | 0.4 | 10.818 |

Coverage: **2885 of 2971** departures in the window (97.1%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2885 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0174 | [-0.0085, +0.0442] | no — CI straddles 0 |
| brier | -0.0230 | [-0.0271, -0.0190] | **yes** |
| logloss | -0.0652 | [-0.0773, -0.0536] | **yes** |
| mae | -5.63 | [-5.9707, -5.2936] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-27 † | 333 | 0.1652 | 0.6876 | 0.6005 | 0.1310 | 10.1 | 16.5 |
| 2026-10-28 | 420 | 0.1119 | 0.6963 | 0.6790 | 0.0947 | 10.8 | 17.8 |
| 2026-10-29 | 414 | 0.1498 | 0.5928 | 0.6337 | 0.1273 | 11.7 | 17.1 |
| 2026-10-30 | 424 | 0.1651 | 0.7570 | 0.7107 | 0.1204 | 11.6 | 16.1 |
| 2026-10-31 | 433 | 0.1085 | 0.7025 | 0.6898 | 0.0958 | 9.7 | 15.0 |
| 2026-11-01 | 418 | 0.1172 | 0.6891 | 0.6486 | 0.0984 | 9.9 | 15.7 |
| 2026-11-02 | 406 | 0.1478 | 0.6486 | 0.6369 | 0.1172 | 10.6 | 15.9 |
| 2026-11-03 *† | 37 | 0.1622 | 0.5914 | 0.6156 | 0.1287 | 9.3 | 12.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 60 | 0.5833 | 0.5954 | 0.5760 | 51.2 |
| < 30 min | 240 | 0.1000 | 0.6197 | 0.5906 | 8.5 |
| 30–120 min | 710 | 0.1268 | 0.7169 | 0.6802 | 9.0 |
| 2–12 h | 1795 | 0.1337 | 0.6679 | 0.6645 | 10.2 |
| > 12 h * | 80 | 0.0875 | 0.6135 | 0.5382 | 9.8 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 866 | 0.067 | 0.067 |
| 0.1-0.2 | 1272 | 0.148 | 0.124 |
| 0.2-0.3 | 560 | 0.238 | 0.195 |
| 0.3-0.4 | 147 | 0.340 | 0.313 |
| 0.4-0.5 * | 26 | 0.440 | 0.577 |
| 0.5-0.6 * | 7 | 0.553 | 0.857 |
| 0.6-0.7 * | 6 | 0.663 | 0.500 |
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
| KE 2012 | 2026-10-29 | KAL | ICN | 0.02 | -3.7 | 41 min |
| EK 381 | 2026-11-02 | UAE | DXB | 0.03 | -0.4 | 26 min |
| QR 817 | 2026-10-29 | QTR | DOH | 0.03 | 3.0 | 19 min |
| VJ 985 | 2026-10-27 | VJC | PQC | 0.70 | 28.9 | 13 min |
| VJ 985 | 2026-10-31 | VJC | PQC | 0.65 | 26.4 | -3 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 1244 | 0.7183 | 0.1064 | 0.3611 | 10.5 | 2026-10-29T19:04:17+00:00 | 2026-11-01T09:29:58+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 1205 | 0.6569 | 0.1147 | 0.3836 | 10.8 | 2026-10-26T13:42:00+00:00 | 2026-10-29T13:25:39+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 436 | 0.6458 | 0.1181 | 0.3981 | 10.5 | 2026-11-01T16:14:42+00:00 | 2026-11-02T12:56:56+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 1244, '4a4212f@2026-08-25T09:35:34+00:00': 1205, 'f6ae66c@2026-11-01T10:28:21+00:00': 436}
