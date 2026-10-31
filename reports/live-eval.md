# Live evaluation — predictions vs actuals

Generated 2026-10-31T21:30:40+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2977**.

Dates 2026-10-25..2026-11-01; observed P(delay > 15) = 0.1454; median lead time between last score and departure = 177.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.667 | 0.1183 | 0.3933 | 11.439 |
| baseline_airline_hour | 0.6561 | 0.1383 | 0.4523 | 16.865 |
| naive_rate | 0.5 | 0.1243 | 0.4147 | 11.53 |

Coverage: **2977 of 3013** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2977 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0109 | [-0.0148, +0.0366] | no — CI straddles 0 |
| brier | -0.0200 | [-0.0238, -0.0159] | **yes** |
| logloss | -0.0590 | [-0.0725, -0.0455] | **yes** |
| mae | -5.43 | [-5.7648, -5.0887] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-25 † | 403 | 0.1985 | 0.6605 | 0.6483 | 0.1512 | 16.0 | 20.0 |
| 2026-10-26 | 430 | 0.1419 | 0.6094 | 0.6251 | 0.1206 | 11.3 | 16.6 |
| 2026-10-27 | 419 | 0.1527 | 0.6685 | 0.6110 | 0.1243 | 9.6 | 15.5 |
| 2026-10-28 | 420 | 0.1119 | 0.6963 | 0.6810 | 0.0947 | 10.8 | 17.9 |
| 2026-10-29 | 414 | 0.1498 | 0.5928 | 0.6339 | 0.1273 | 11.7 | 17.2 |
| 2026-10-30 | 424 | 0.1651 | 0.7570 | 0.7105 | 0.1204 | 11.6 | 16.2 |
| 2026-10-31 | 433 | 0.1085 | 0.7025 | 0.6863 | 0.0958 | 9.7 | 15.2 |
| 2026-11-01 *† | 34 | 0.0588 | 0.1250 | 0.1484 | 0.0657 | 7.1 | 11.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 82 | 0.6341 | 0.5724 | 0.5240 | 57.1 |
| < 30 min | 253 | 0.0830 | 0.7239 | 0.6948 | 9.9 |
| 30–120 min | 788 | 0.1434 | 0.6797 | 0.6602 | 10.1 |
| 2–12 h | 1790 | 0.1346 | 0.6562 | 0.6583 | 10.3 |
| > 12 h * | 64 | 0.0938 | 0.5661 | 0.4009 | 8.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 855 | 0.066 | 0.070 |
| 0.1-0.2 | 1202 | 0.148 | 0.130 |
| 0.2-0.3 | 670 | 0.241 | 0.196 |
| 0.3-0.4 | 187 | 0.339 | 0.294 |
| 0.4-0.5 | 43 | 0.437 | 0.442 |
| 0.5-0.6 * | 13 | 0.539 | 0.692 |
| 0.6-0.7 * | 6 | 0.658 | 0.333 |
| 0.7-0.8 * | 1 | 0.793 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-31 | RNA | KTM | 0.79 | 41.3 | 55 min |
| VJ 877 | 2026-10-25 | VJC | SGN | 0.68 | 26.8 | 85 min |
| LX 139 | 2026-10-30 | SWR | ZRH | 0.67 | 27.1 | 39 min |
| VJ 877 | 2026-10-26 | VJC | SGN | 0.59 | 23.0 | 78 min |
| LX 139 | 2026-10-31 | SWR | ZRH | 0.57 | 21.6 | 42 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-29 | KAL | ICN | 0.02 | -3.7 | 41 min |
| QR 817 | 2026-10-29 | QTR | DOH | 0.03 | 3.0 | 19 min |
| CA 118 | 2026-10-27 | CCA | PEK | 0.03 | -2.9 | 19 min |
| VJ 985 | 2026-10-27 | VJC | PQC | 0.70 | 28.9 | 13 min |
| VJ 985 | 2026-10-31 | VJC | PQC | 0.65 | 26.4 | -3 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 853 | 0.7264 | 0.1087 | 0.3661 | 10.7 | 2026-10-29T19:04:17+00:00 | 2026-10-31T16:27:51+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 2124 | 0.6493 | 0.1221 | 0.4042 | 11.7 | 2026-10-24T12:09:06+00:00 | 2026-10-29T13:25:39+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 853, '4a4212f@2026-08-25T09:35:34+00:00': 2124}
