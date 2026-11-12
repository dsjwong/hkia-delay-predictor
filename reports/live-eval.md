# Live evaluation — predictions vs actuals

Generated 2026-11-12T00:38:38+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2788**.

Dates 2026-11-05..2026-11-12; observed P(delay > 15) = 0.1313; median lead time between last score and departure = 205.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6705 | 0.1102 | 0.3721 | 10.369 |
| baseline_airline_hour | 0.6219 | 0.1357 | 0.4429 | 15.736 |
| naive_rate | 0.5 | 0.114 | 0.3888 | 10.118 |

Coverage: **2788 of 2864** departures in the window (97.4%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2788 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0486 | [+0.0202, +0.0779] | **yes** |
| brier | -0.0255 | [-0.0289, -0.0220] | **yes** |
| logloss | -0.0708 | [-0.0806, -0.0612] | **yes** |
| mae | -5.37 | [-5.6703, -5.0524] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-05 † | 322 | 0.1304 | 0.5763 | 0.6436 | 0.1194 | 10.5 | 15.8 |
| 2026-11-06 | 418 | 0.1124 | 0.6627 | 0.6070 | 0.1003 | 8.6 | 14.4 |
| 2026-11-07 | 411 | 0.1241 | 0.6909 | 0.6096 | 0.1021 | 9.1 | 15.1 |
| 2026-11-08 | 413 | 0.1525 | 0.6713 | 0.5853 | 0.1249 | 12.9 | 17.5 |
| 2026-11-09 | 404 | 0.1287 | 0.7165 | 0.6587 | 0.1052 | 9.9 | 15.6 |
| 2026-11-10 | 391 | 0.1714 | 0.7526 | 0.6521 | 0.1272 | 11.7 | 16.1 |
| 2026-11-11 | 396 | 0.1010 | 0.6205 | 0.6142 | 0.0955 | 10.2 | 16.1 |
| 2026-11-12 *† | 33 | 0.1212 | 0.7155 | 0.5129 | 0.1019 | 7.8 | 12.0 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 64 | 0.7500 | 0.5859 | 0.4824 | 49.3 |
| < 30 min | 163 | 0.1288 | 0.6925 | 0.6499 | 8.8 |
| 30–120 min | 632 | 0.1250 | 0.6804 | 0.6107 | 9.0 |
| 2–12 h | 1809 | 0.1133 | 0.6675 | 0.6125 | 9.8 |
| > 12 h | 120 | 0.1083 | 0.7890 | 0.6693 | 8.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 700 | 0.070 | 0.056 |
| 0.1-0.2 | 1125 | 0.148 | 0.118 |
| 0.2-0.3 | 700 | 0.243 | 0.156 |
| 0.3-0.4 | 204 | 0.336 | 0.284 |
| 0.4-0.5 | 39 | 0.442 | 0.410 |
| 0.5-0.6 * | 14 | 0.545 | 0.571 |
| 0.6-0.7 * | 5 | 0.629 | 0.400 |
| 0.8-0.9 * | 1 | 0.832 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-11-07 | RNA | KTM | 0.83 | 46.4 | 56 min |
| LX 139 | 2026-11-08 | SWR | ZRH | 0.64 | 27.5 | 43 min |
| VJ 985 | 2026-11-07 | VJC | PQC | 0.63 | 24.1 | 176 min |
| VJ 877 | 2026-11-06 | VJC | SGN | 0.56 | 25.5 | 18 min |
| NZ 080 | 2026-11-10 | ANZ | AKL | 0.56 | 23.1 | 36 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 420 | 2026-11-10 | CCA | CKG | 0.05 | 1.7 | 33 min |
| UO 132 | 2026-11-10 | HKE | KHH | 0.05 | -1.1 | 36 min |
| KL 888 | 2026-11-11 | KLM | AMS | 0.06 | 2.9 | 64 min |
| VJ 985 | 2026-11-10 | VJC | PQC | 0.63 | 32.9 | 0 min |
| OD 606 | 2026-11-10 | MXD | KUL | 0.62 | 43.9 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| f6ae66c@2026-11-01T10:28:21+00:00 | 2788 | 0.6705 | 0.1102 | 0.3721 | 10.4 | 2026-11-04T03:42:06+00:00 | 2026-11-11T11:31:51+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'f6ae66c@2026-11-01T10:28:21+00:00': 2788}
