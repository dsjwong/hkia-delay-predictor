# Live evaluation — predictions vs actuals

Generated 2026-10-25T20:48:27+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2985**.

Dates 2026-10-19..2026-10-26; observed P(delay > 15) = 0.1849; median lead time between last score and departure = 140.0 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6637 | 0.1441 | 0.4548 | 14.129 |
| baseline_airline_hour | 0.6449 | 0.1544 | 0.4835 | 17.884 |
| naive_rate | 0.5 | 0.1507 | 0.4788 | 13.886 |

Coverage: **2985 of 3029** departures in the window (98.6%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2985 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0188 | [+0.0003, +0.0379] | **yes** |
| brier | -0.0103 | [-0.0133, -0.0073] | **yes** |
| logloss | -0.0287 | [-0.0368, -0.0197] | **yes** |
| mae | -3.75 | [-4.0357, -3.4675] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-19 † | 404 | 0.1386 | 0.6399 | 0.6089 | 0.1190 | 11.9 | 17.7 |
| 2026-10-20 | 431 | 0.1346 | 0.6420 | 0.7145 | 0.1215 | 11.9 | 15.6 |
| 2026-10-21 | 432 | 0.1505 | 0.7223 | 0.7706 | 0.1201 | 10.2 | 14.1 |
| 2026-10-22 | 420 | 0.2810 | 0.6632 | 0.6445 | 0.1913 | 19.0 | 21.1 |
| 2026-10-23 | 396 | 0.1919 | 0.6007 | 0.5620 | 0.1556 | 14.8 | 18.4 |
| 2026-10-24 | 429 | 0.2191 | 0.6541 | 0.6057 | 0.1625 | 17.3 | 20.7 |
| 2026-10-25 | 438 | 0.1849 | 0.6772 | 0.6585 | 0.1420 | 14.5 | 18.3 |
| 2026-10-26 *† | 35 | 0.1143 | 0.4113 | 0.4073 | 0.1124 | 6.2 | 10.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 97 | 0.7216 | 0.6905 | 0.6225 | 54.9 |
| < 30 min | 316 | 0.2057 | 0.7734 | 0.7421 | 14.6 |
| 30–120 min | 999 | 0.1842 | 0.6458 | 0.6139 | 13.8 |
| 2–12 h | 1546 | 0.1488 | 0.6280 | 0.6164 | 11.8 |
| > 12 h * | 27 | 0.1111 | 0.7778 | 0.8819 | 7.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 605 | 0.068 | 0.063 |
| 0.1-0.2 | 938 | 0.147 | 0.160 |
| 0.2-0.3 | 768 | 0.250 | 0.206 |
| 0.3-0.4 | 467 | 0.340 | 0.255 |
| 0.4-0.5 | 134 | 0.441 | 0.381 |
| 0.5-0.6 | 52 | 0.543 | 0.442 |
| 0.6-0.7 * | 12 | 0.643 | 0.667 |
| 0.7-0.8 * | 7 | 0.736 | 0.571 |
| 0.8-0.9 * | 2 | 0.854 | 0.500 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| VJ 985 | 2026-10-22 | VJC | PQC | 0.84 | 42.4 | 33 min |
| VJ 985 | 2026-10-24 | VJC | PQC | 0.79 | 43.9 | 22 min |
| LX 139 | 2026-10-19 | SWR | ZRH | 0.74 | 28.5 | 23 min |
| VJ 877 | 2026-10-23 | VJC | SGN | 0.72 | 34.3 | 34 min |
| JX 236 | 2026-10-22 | SJX | TPE | 0.71 | 41.6 | 51 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 5 were actually more than 15 minutes late (56%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| KE 2012 | 2026-10-23 | KAL | ICN | 0.03 | -0.1 | 29 min |
| EK 381 | 2026-10-26 | UAE | DXB | 0.04 | -1.7 | 19 min |
| CA 420 | 2026-10-19 | CCA | CKG | 0.04 | -2.9 | 131 min |
| RA 410 | 2026-10-24 | RNA | KTM | 0.87 | 62.1 | 5 min |
| OD 606 | 2026-10-22 | MXD | KUL | 0.77 | 65.1 | 5 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2985 | 0.6637 | 0.1441 | 0.4548 | 14.1 | 2026-10-18T06:08:39+00:00 | 2026-10-25T15:11:25+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2985}
