# Live evaluation — predictions vs actuals

Generated 2026-09-23T21:29:02+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2914**.

Dates 2026-09-17..2026-09-24; observed P(delay > 15) = 0.1373; median lead time between last score and departure = 126.2 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6655 | 0.1149 | 0.3847 | 10.809 |
| baseline_airline_hour | 0.6518 | 0.1363 | 0.4425 | 16.161 |
| naive_rate | 0.5 | 0.1184 | 0.4 | 10.791 |

Coverage: **2914 of 2950** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2914 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0137 | [-0.0091, +0.0357] | no — CI straddles 0 |
| brier | -0.0214 | [-0.0247, -0.0179] | **yes** |
| logloss | -0.0578 | [-0.0678, -0.0474] | **yes** |
| mae | -5.35 | [-5.6690, -5.0283] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-17 † | 364 | 0.1236 | 0.7390 | 0.6792 | 0.1034 | 10.9 | 17.3 |
| 2026-09-18 | 418 | 0.1148 | 0.6810 | 0.6624 | 0.1007 | 8.8 | 14.6 |
| 2026-09-19 | 424 | 0.1486 | 0.6913 | 0.6467 | 0.1193 | 11.9 | 17.1 |
| 2026-09-20 | 423 | 0.1253 | 0.6765 | 0.6537 | 0.1082 | 11.8 | 17.2 |
| 2026-09-21 | 412 | 0.1311 | 0.5944 | 0.5875 | 0.1182 | 10.4 | 15.8 |
| 2026-09-22 | 410 | 0.1756 | 0.7213 | 0.6813 | 0.1305 | 11.7 | 16.7 |
| 2026-09-23 | 424 | 0.1392 | 0.6118 | 0.6791 | 0.1197 | 10.3 | 14.9 |
| 2026-09-24 *† | 39 | 0.1538 | 0.4141 | 0.4343 | 0.1480 | 8.7 | 11.8 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 111 | 0.7117 | 0.5059 | 0.4929 | 47.6 |
| < 30 min | 330 | 0.1515 | 0.7408 | 0.7005 | 10.1 |
| 30–120 min | 1025 | 0.1161 | 0.6350 | 0.6091 | 9.0 |
| 2–12 h | 1433 | 0.1061 | 0.6473 | 0.6352 | 9.4 |
| > 12 h * | 15 | 0.0000 | — | — | 5.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 862 | 0.063 | 0.071 |
| 0.1-0.2 | 1024 | 0.149 | 0.112 |
| 0.2-0.3 | 696 | 0.245 | 0.184 |
| 0.3-0.4 | 239 | 0.339 | 0.247 |
| 0.4-0.5 | 61 | 0.439 | 0.328 |
| 0.5-0.6 * | 23 | 0.542 | 0.565 |
| 0.6-0.7 * | 8 | 0.633 | 0.375 |
| 0.7-0.8 * | 1 | 0.777 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-09-19 | RNA | KTM | 0.78 | 52.8 | 55 min |
| VJ 985 | 2026-09-22 | VJC | PQC | 0.65 | 29.8 | 40 min |
| CX 520 | 2026-09-20 | CPA | NRT | 0.60 | 25.4 | 62 min |
| VJ 877 | 2026-09-23 | VJC | SGN | 0.60 | 24.8 | 49 min |
| OD 606 | 2026-09-22 | MXD | KUL | 0.60 | 46.7 | 158 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 1 calls published at P ≥ 70%**, 1 were actually more than 15 minutes late (100%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-09-18 | JNA | CJU | 0.03 | -1.2 | 20 min |
| CA 110 | 2026-09-23 | CCA | PEK | 0.03 | -3.3 | 28 min |
| UO 604 | 2026-09-21 | HKE | PUS | 0.03 | -6.9 | 26 min |
| VJ 985 | 2026-09-19 | VJC | PQC | 0.70 | 34.0 | 0 min |
| NH 812 | 2026-09-21 | ANA | NRT | 0.66 | 30.1 | 10 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2914 | 0.6655 | 0.1149 | 0.3847 | 10.8 | 2026-09-16T18:58:16+00:00 | 2026-09-23T17:19:02+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2914}
