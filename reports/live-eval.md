# Live evaluation — predictions vs actuals

Generated 2026-11-01T21:59:38+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2958**.

Dates 2026-10-26..2026-11-02; observed P(delay > 15) = 0.1359; median lead time between last score and departure = 185.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6677 | 0.1118 | 0.3771 | 10.673 |
| baseline_airline_hour | 0.6549 | 0.1342 | 0.4437 | 16.238 |
| naive_rate | 0.5 | 0.1174 | 0.3975 | 10.861 |

Coverage: **2958 of 2997** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2958 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0128 | [-0.0136, +0.0378] | no — CI straddles 0 |
| brier | -0.0224 | [-0.0262, -0.0188] | **yes** |
| logloss | -0.0666 | [-0.0802, -0.0540] | **yes** |
| mae | -5.57 | [-5.8994, -5.2304] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-26 † | 391 | 0.1432 | 0.6287 | 0.6382 | 0.1201 | 11.5 | 16.8 |
| 2026-10-27 | 419 | 0.1527 | 0.6685 | 0.6093 | 0.1243 | 9.6 | 15.4 |
| 2026-10-28 | 420 | 0.1119 | 0.6963 | 0.6790 | 0.0947 | 10.8 | 17.8 |
| 2026-10-29 | 414 | 0.1498 | 0.5928 | 0.6337 | 0.1273 | 11.7 | 17.1 |
| 2026-10-30 | 424 | 0.1651 | 0.7570 | 0.7107 | 0.1204 | 11.6 | 16.1 |
| 2026-10-31 | 433 | 0.1085 | 0.7025 | 0.6898 | 0.0958 | 9.7 | 15.0 |
| 2026-11-01 | 418 | 0.1172 | 0.6891 | 0.6486 | 0.0984 | 9.9 | 15.7 |
| 2026-11-02 *† | 39 | 0.1795 | 0.6027 | 0.5893 | 0.1418 | 10.6 | 13.6 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 69 | 0.5942 | 0.5070 | 0.5057 | 49.8 |
| < 30 min | 245 | 0.0857 | 0.6029 | 0.5437 | 7.6 |
| 30–120 min | 747 | 0.1312 | 0.7057 | 0.6629 | 9.5 |
| 2–12 h | 1819 | 0.1292 | 0.6651 | 0.6721 | 10.1 |
| > 12 h * | 78 | 0.0897 | 0.6529 | 0.5181 | 9.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 893 | 0.067 | 0.067 |
| 0.1-0.2 | 1275 | 0.148 | 0.124 |
| 0.2-0.3 | 603 | 0.239 | 0.196 |
| 0.3-0.4 | 147 | 0.339 | 0.293 |
| 0.4-0.5 * | 26 | 0.440 | 0.500 |
| 0.5-0.6 * | 8 | 0.547 | 0.875 |
| 0.6-0.7 * | 5 | 0.660 | 0.400 |
| 0.7-0.8 * | 1 | 0.793 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-31 | RNA | KTM | 0.79 | 41.3 | 55 min |
| LX 139 | 2026-10-30 | SWR | ZRH | 0.67 | 27.1 | 39 min |
| LX 139 | 2026-11-01 | SWR | ZRH | 0.64 | 27.3 | 40 min |
| VJ 877 | 2026-10-26 | VJC | SGN | 0.59 | 23.0 | 78 min |
| LX 139 | 2026-10-31 | SWR | ZRH | 0.57 | 21.6 | 42 min |

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
| 42715b6@2026-10-29T14:57:07+00:00 | 1242 | 0.7179 | 0.1066 | 0.3616 | 10.5 | 2026-10-29T19:04:17+00:00 | 2026-11-01T09:29:58+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 1682 | 0.6428 | 0.1151 | 0.3866 | 10.8 | 2026-10-25T18:29:55+00:00 | 2026-10-29T13:25:39+00:00 |
| f6ae66c@2026-11-01T10:28:21+00:00 * | 34 | 0.5833 | 0.1389 | 0.4747 | 9.8 | 2026-11-01T16:14:42+00:00 | 2026-11-01T16:14:42+00:00 |

`*` = thin (< 100 flights — AUC standard error is large, treat as noise). Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'42715b6@2026-10-29T14:57:07+00:00': 1242, '4a4212f@2026-08-25T09:35:34+00:00': 1682, 'f6ae66c@2026-11-01T10:28:21+00:00': 34}
