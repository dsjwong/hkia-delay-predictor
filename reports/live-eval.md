# Live evaluation — predictions vs actuals

Generated 2026-11-12T23:35:29+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2826**.

Dates 2026-11-06..2026-11-13; observed P(delay > 15) = 0.1313; median lead time between last score and departure = 210.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6763 | 0.1093 | 0.3698 | 10.258 |
| baseline_airline_hour | 0.6181 | 0.1354 | 0.4423 | 15.723 |
| naive_rate | 0.5 | 0.114 | 0.3888 | 10.074 |

Coverage: **2826 of 2864** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2826 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0582 | [+0.0294, +0.0859] | **yes** |
| brier | -0.0261 | [-0.0296, -0.0227] | **yes** |
| logloss | -0.0725 | [-0.0824, -0.0625] | **yes** |
| mae | -5.46 | [-5.7694, -5.1616] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-06 † | 380 | 0.1158 | 0.6744 | 0.6135 | 0.1027 | 8.7 | 14.8 |
| 2026-11-07 | 411 | 0.1241 | 0.6909 | 0.6096 | 0.1021 | 9.1 | 15.1 |
| 2026-11-08 | 413 | 0.1525 | 0.6713 | 0.5853 | 0.1249 | 12.9 | 17.5 |
| 2026-11-09 | 404 | 0.1287 | 0.7165 | 0.6587 | 0.1052 | 9.9 | 15.6 |
| 2026-11-10 | 391 | 0.1714 | 0.7526 | 0.6521 | 0.1272 | 11.7 | 16.1 |
| 2026-11-11 | 396 | 0.1010 | 0.6205 | 0.6142 | 0.0955 | 10.2 | 16.1 |
| 2026-11-12 | 396 | 0.1212 | 0.6581 | 0.6283 | 0.1036 | 8.7 | 14.7 |
| 2026-11-13 *† | 35 | 0.1714 | 0.4368 | 0.3448 | 0.1494 | 14.9 | 17.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 69 | 0.6812 | 0.6576 | 0.5121 | 45.7 |
| < 30 min | 179 | 0.1173 | 0.6573 | 0.6249 | 8.9 |
| 30–120 min | 601 | 0.1314 | 0.6912 | 0.6259 | 8.9 |
| 2–12 h | 1859 | 0.1151 | 0.6685 | 0.6039 | 9.6 |
| > 12 h | 118 | 0.0847 | 0.8241 | 0.7065 | 8.6 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 722 | 0.069 | 0.053 |
| 0.1-0.2 | 1146 | 0.148 | 0.120 |
| 0.2-0.3 | 705 | 0.242 | 0.155 |
| 0.3-0.4 | 195 | 0.335 | 0.303 |
| 0.4-0.5 | 38 | 0.441 | 0.421 |
| 0.5-0.6 * | 15 | 0.547 | 0.600 |
| 0.6-0.7 * | 4 | 0.632 | 0.500 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| LX 139 | 2026-11-12 | SWR | ZRH | 0.57 | 23.2 | 32 min |
| VJ 877 | 2026-11-06 | VJC | SGN | 0.56 | 25.5 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 622 | 2026-11-12 | HKE | HND | 0.03 | -4.9 | 33 min |
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| UO 132 | 2026-11-10 | HKE | KHH | 0.05 | -1.1 | 36 min |
| VJ 985 | 2026-11-10 | VJC | PQC | 0.63 | 32.9 | 0 min |
| OD 606 | 2026-11-10 | MXD | KUL | 0.62 | 43.9 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2826 | 0.6763 | 0.1093 | 0.3698 | 10.3 | 2026-11-05T00:09:57+00:00 | 2026-11-12T17:12:32+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2826}
