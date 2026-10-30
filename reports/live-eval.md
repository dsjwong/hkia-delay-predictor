# Live evaluation — predictions vs actuals

Generated 2026-10-30T22:16:29+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2975**.

Dates 2026-10-24..2026-10-31; observed P(delay > 15) = 0.1603; median lead time between last score and departure = 170.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6722 | 0.1272 | 0.4152 | 12.515 |
| baseline_airline_hour | 0.6465 | 0.1449 | 0.4673 | 17.631 |
| naive_rate | 0.5 | 0.1346 | 0.4402 | 12.701 |

Coverage: **2975 of 3014** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2975 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0257 | [+0.0003, +0.0505] | **yes** |
| brier | -0.0177 | [-0.0215, -0.0138] | **yes** |
| logloss | -0.0521 | [-0.0657, -0.0389] | **yes** |
| mae | -5.12 | [-5.4622, -4.7626] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-24 † | 391 | 0.2251 | 0.6485 | 0.5933 | 0.1668 | 18.1 | 21.5 |
| 2026-10-25 | 439 | 0.1868 | 0.6740 | 0.6673 | 0.1432 | 15.4 | 19.2 |
| 2026-10-26 | 430 | 0.1419 | 0.6094 | 0.6251 | 0.1206 | 11.3 | 16.6 |
| 2026-10-27 | 419 | 0.1527 | 0.6685 | 0.6110 | 0.1243 | 9.6 | 15.5 |
| 2026-10-28 | 420 | 0.1119 | 0.6963 | 0.6810 | 0.0947 | 10.8 | 17.9 |
| 2026-10-29 | 414 | 0.1498 | 0.5928 | 0.6339 | 0.1273 | 11.7 | 17.2 |
| 2026-10-30 | 424 | 0.1651 | 0.7570 | 0.7105 | 0.1204 | 11.6 | 16.2 |
| 2026-10-31 *† | 38 | 0.0789 | 0.5667 | 0.7286 | 0.0775 | 6.0 | 10.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 79 | 0.6962 | 0.5659 | 0.5193 | 72.6 |
| < 30 min | 256 | 0.1211 | 0.7913 | 0.7404 | 11.2 |
| 30–120 min | 829 | 0.1532 | 0.6892 | 0.6559 | 10.9 |
| 2–12 h | 1755 | 0.1476 | 0.6532 | 0.6336 | 10.9 |
| > 12 h * | 56 | 0.0893 | 0.6275 | 0.3941 | 8.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 808 | 0.066 | 0.073 |
| 0.1-0.2 | 1191 | 0.148 | 0.139 |
| 0.2-0.3 | 662 | 0.242 | 0.218 |
| 0.3-0.4 | 224 | 0.339 | 0.299 |
| 0.4-0.5 | 61 | 0.439 | 0.443 |
| 0.5-0.6 * | 20 | 0.538 | 0.550 |
| 0.6-0.7 * | 7 | 0.663 | 0.429 |
| 0.7-0.8 * | 1 | 0.790 | 1.000 |
| 0.8-0.9 * | 1 | 0.871 | 0.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-10-24 | VJC | PQC | 0.79 | 43.9 | 22 min |
| VJ 877 | 2026-10-25 | VJC | SGN | 0.68 | 26.8 | 85 min |
| LX 139 | 2026-10-30 | SWR | ZRH | 0.67 | 27.1 | 39 min |
| JX 236 | 2026-10-24 | SJX | TPE | 0.67 | 35.2 | 43 min |
| VJ 877 | 2026-10-26 | VJC | SGN | 0.59 | 23.0 | 78 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 2 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (50%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-29 | KAL | ICN | 0.02 | -3.7 | 41 min |
| QR 817 | 2026-10-29 | QTR | DOH | 0.03 | 3.0 | 19 min |
| CA 118 | 2026-10-27 | CCA | PEK | 0.03 | -2.9 | 19 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| VJ 985 | 2026-10-27 | VJC | PQC | 0.70 | 28.9 | 13 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 42715b6@2026-10-29T14:57:07+00:00 | 424 | 0.7529 | 0.1224 | 0.3981 | 11.6 | 2026-10-29T19:04:17+00:00 | 2026-10-30T16:05:35+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 2551 | 0.6594 | 0.1280 | 0.4180 | 12.7 | 2026-10-23T20:45:36+00:00 | 2026-10-29T13:25:39+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 424, '4a4212f@2026-08-25T09:35:34+00:00': 2551}
