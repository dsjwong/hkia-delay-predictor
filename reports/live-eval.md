# Live evaluation — predictions vs actuals

Generated 2026-11-03T23:18:16+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2905**.

Dates 2026-10-28..2026-11-04; observed P(delay > 15) = 0.1356; median lead time between last score and departure = 196.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6611 | 0.1112 | 0.3761 | 10.737 |
| baseline_airline_hour | 0.651 | 0.1342 | 0.4405 | 16.335 |
| naive_rate | 0.5 | 0.1172 | 0.3969 | 10.936 |

Coverage: **2905 of 2942** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2905 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0101 | [-0.0157, +0.0359] | no — CI straddles 0 |
| brier | -0.0230 | [-0.0268, -0.0190] | **yes** |
| logloss | -0.0644 | [-0.0758, -0.0525] | **yes** |
| mae | -5.60 | [-5.9133, -5.2513] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-28 † | 383 | 0.1149 | 0.7000 | 0.6737 | 0.0962 | 11.2 | 18.5 |
| 2026-10-29 | 414 | 0.1498 | 0.5928 | 0.6337 | 0.1273 | 11.7 | 17.1 |
| 2026-10-30 | 424 | 0.1651 | 0.7570 | 0.7107 | 0.1204 | 11.6 | 16.1 |
| 2026-10-31 | 433 | 0.1085 | 0.7025 | 0.6898 | 0.0958 | 9.7 | 15.0 |
| 2026-11-01 | 418 | 0.1172 | 0.6891 | 0.6486 | 0.0984 | 9.9 | 15.7 |
| 2026-11-02 | 406 | 0.1478 | 0.6486 | 0.6369 | 0.1172 | 10.6 | 15.9 |
| 2026-11-03 | 400 | 0.1450 | 0.5864 | 0.5885 | 0.1219 | 10.8 | 16.7 |
| 2026-11-04 *† | 27 | 0.1481 | 0.6304 | 0.4565 | 0.1224 | 6.8 | 9.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 64 | 0.5938 | 0.5951 | 0.5481 | 51.3 |
| < 30 min | 231 | 0.1212 | 0.6237 | 0.6462 | 8.8 |
| 30–120 min | 686 | 0.1210 | 0.7049 | 0.6940 | 9.3 |
| 2–12 h | 1778 | 0.1305 | 0.6561 | 0.6551 | 10.3 |
| > 12 h | 146 | 0.0890 | 0.5590 | 0.4954 | 8.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 882 | 0.067 | 0.069 |
| 0.1-0.2 | 1274 | 0.148 | 0.130 |
| 0.2-0.3 | 571 | 0.239 | 0.172 |
| 0.3-0.4 | 139 | 0.340 | 0.309 |
| 0.4-0.5 * | 24 | 0.438 | 0.625 |
| 0.5-0.6 * | 9 | 0.556 | 0.778 |
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
| KE 2012 | 2026-10-29 | KAL | ICN | 0.02 | -3.7 | 41 min |
| EK 381 | 2026-11-02 | UAE | DXB | 0.03 | -0.4 | 26 min |
| QR 817 | 2026-10-29 | QTR | DOH | 0.03 | 3.0 | 19 min |
| VJ 985 | 2026-10-31 | VJC | PQC | 0.65 | 26.4 | -3 min |
| VJ 985 | 2026-10-29 | VJC | PQC | 0.64 | 25.4 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 1244 | 0.7183 | 0.1064 | 0.3611 | 10.5 | 2026-10-29T19:04:17+00:00 | 2026-11-01T09:29:58+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 835 | 0.6400 | 0.1098 | 0.3729 | 11.2 | 2026-10-27T19:44:32+00:00 | 2026-10-29T13:25:39+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 | 826 | 0.6193 | 0.1196 | 0.4018 | 10.6 | 2026-11-01T16:14:42+00:00 | 2026-11-03T11:27:32+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 1244, '4a4212f@2026-08-25T09:35:34+00:00': 835, 'f6ae66c@2026-11-01T10:28:21+00:00': 826}
