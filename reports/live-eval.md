# Live evaluation — predictions vs actuals

Generated 2026-10-18T20:38:48+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3027**.

Dates 2026-10-12..2026-10-19; observed P(delay > 15) = 0.1335; median lead time between last score and departure = 143.3 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.7007 | 0.1135 | 0.3758 | 11.198 |
| baseline_airline_hour | 0.6834 | 0.1313 | 0.4342 | 15.928 |
| naive_rate | 0.5 | 0.1157 | 0.3929 | 10.746 |

Coverage: **3027 of 3069** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3027 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0173 | [-0.0050, +0.0382] | no — CI straddles 0 |
| brier | -0.0178 | [-0.0209, -0.0144] | **yes** |
| logloss | -0.0584 | [-0.0716, -0.0463] | **yes** |
| mae | -4.73 | [-5.0088, -4.4435] | **yes** |

The model is separably better on: brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-12 † | 392 | 0.1276 | 0.6920 | 0.6250 | 0.1038 | 9.8 | 16.1 |
| 2026-10-13 | 423 | 0.1371 | 0.7361 | 0.7383 | 0.1091 | 10.3 | 15.5 |
| 2026-10-14 | 420 | 0.1071 | 0.7107 | 0.7070 | 0.1055 | 10.2 | 15.1 |
| 2026-10-15 | 421 | 0.1116 | 0.7419 | 0.7044 | 0.0940 | 9.1 | 15.1 |
| 2026-10-16 | 448 | 0.1250 | 0.6116 | 0.6268 | 0.1205 | 12.3 | 15.9 |
| 2026-10-17 | 441 | 0.1678 | 0.7029 | 0.6981 | 0.1335 | 14.0 | 17.7 |
| 2026-10-18 | 439 | 0.1458 | 0.7372 | 0.7121 | 0.1197 | 12.6 | 16.7 |
| 2026-10-19 *† | 43 | 0.2326 | 0.6773 | 0.6409 | 0.1742 | 9.3 | 9.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 89 | 0.6292 | 0.5779 | 0.6261 | 47.8 |
| < 30 min | 296 | 0.1453 | 0.7344 | 0.6749 | 12.2 |
| 30–120 min | 966 | 0.1439 | 0.7152 | 0.6839 | 10.0 |
| 2–12 h | 1632 | 0.1011 | 0.6919 | 0.6905 | 9.8 |
| > 12 h * | 44 | 0.0227 | 0.4884 | 0.7209 | 6.5 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 819 | 0.064 | 0.039 |
| 0.1-0.2 | 991 | 0.146 | 0.104 |
| 0.2-0.3 | 671 | 0.246 | 0.191 |
| 0.3-0.4 | 349 | 0.339 | 0.238 |
| 0.4-0.5 | 143 | 0.445 | 0.273 |
| 0.5-0.6 | 40 | 0.542 | 0.275 |
| 0.6-0.7 * | 10 | 0.640 | 0.500 |
| 0.7-0.8 * | 3 | 0.722 | 0.667 |
| 0.8-0.9 * | 1 | 0.870 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-10-17 | RNA | KTM | 0.87 | 57.5 | 101 min |
| VJ 985 | 2026-10-13 | VJC | PQC | 0.73 | 30.9 | 33 min |
| VJ 985 | 2026-10-17 | VJC | PQC | 0.71 | 34.5 | 18 min |
| NH 812 | 2026-10-14 | ANA | NRT | 0.70 | 24.0 | 35 min |
| LX 139 | 2026-10-17 | SWR | ZRH | 0.68 | 21.5 | 32 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 4 calls published at P ≥ 70%**, 3 were actually more than 15 minutes late (75%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 102 | 2026-10-16 | CCA | PEK | 0.03 | -2.8 | 19 min |
| CA 110 | 2026-10-16 | CCA | PEK | 0.04 | -0.9 | 36 min |
| KE 2006 | 2026-10-18 | KAL | ICN | 0.04 | -0.2 | 145 min |
| OD 606 | 2026-10-17 | MXD | KUL | 0.72 | 51.2 | 13 min |
| VJ 985 | 2026-10-15 | VJC | PQC | 0.70 | 28.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3027 | 0.7007 | 0.1135 | 0.3758 | 11.2 | 2026-10-11T07:25:33+00:00 | 2026-10-18T17:38:44+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3027}
