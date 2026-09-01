# Live evaluation — predictions vs actuals

Generated 2026-09-01T21:00:53+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3057**.

Dates 2026-08-26..2026-09-02; observed P(delay > 15) = 0.2581; median lead time between last score and departure = 137.5 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6709 | 0.1883 | 0.5582 | 15.813 |
| baseline_airline_hour | 0.6203 | 0.1845 | 0.5535 | 17.18 |
| naive_rate | 0.5 | 0.1915 | 0.5711 | 15.045 |

Coverage: **3057 of 3097** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3057 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0506 | [+0.0284, +0.0727] | **yes** |
| brier | +0.0038 | [-0.0017, +0.0091] | no — CI straddles 0 |
| logloss | +0.0047 | [-0.0080, +0.0175] | no — CI straddles 0 |
| mae | -1.37 | [-1.6444, -1.0863] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-26 † | 398 | 0.3216 | 0.7587 | 0.6215 | 0.1785 | 16.5 | 18.5 |
| 2026-08-27 | 432 | 0.4306 | 0.5638 | 0.6145 | 0.2611 | 20.7 | 18.3 |
| 2026-08-28 | 449 | 0.1893 | 0.6133 | 0.6065 | 0.1714 | 15.1 | 16.7 |
| 2026-08-29 | 444 | 0.2297 | 0.7014 | 0.6879 | 0.1579 | 14.1 | 17.1 |
| 2026-08-30 | 451 | 0.2705 | 0.6491 | 0.6333 | 0.1863 | 14.9 | 17.6 |
| 2026-08-31 | 442 | 0.1991 | 0.6230 | 0.5766 | 0.1751 | 14.8 | 16.9 |
| 2026-09-01 | 403 | 0.1737 | 0.5722 | 0.6105 | 0.1938 | 15.2 | 15.6 |
| 2026-09-02 *† | 38 | 0.2105 | 0.8104 | 0.7771 | 0.1351 | 11.2 | 11.5 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 194 | 0.7835 | 0.6330 | 0.5985 | 38.4 |
| < 30 min | 410 | 0.2098 | 0.7172 | 0.6331 | 13.4 |
| 30–120 min | 892 | 0.2545 | 0.6554 | 0.5787 | 13.8 |
| 2–12 h | 1537 | 0.2082 | 0.6612 | 0.6352 | 14.8 |
| > 12 h * | 24 | 0.1667 | 0.6875 | 0.6438 | 14.0 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 189 | 0.071 | 0.085 |
| 0.1-0.2 | 598 | 0.151 | 0.144 |
| 0.2-0.3 | 603 | 0.250 | 0.187 |
| 0.3-0.4 | 547 | 0.350 | 0.276 |
| 0.4-0.5 | 512 | 0.446 | 0.305 |
| 0.5-0.6 | 307 | 0.545 | 0.384 |
| 0.6-0.7 | 221 | 0.645 | 0.462 |
| 0.7-0.8 | 68 | 0.735 | 0.529 |
| 0.8-0.9 * | 12 | 0.828 | 0.917 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-29 | RNA | KTM | 0.88 | 57.4 | 99 min |
| LX 139 | 2026-08-28 | SWR | ZRH | 0.85 | 31.0 | 59 min |
| LX 139 | 2026-08-29 | SWR | ZRH | 0.85 | 31.3 | 39 min |
| OD 606 | 2026-08-27 | MXD | KUL | 0.84 | 73.2 | 30 min |
| CX 797 | 2026-08-26 | CPA | CGK | 0.81 | 46.2 | 37 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 80 calls published at P ≥ 70%**, 47 were actually more than 15 minutes late (59%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| TW 640 | 2026-08-27 | TWB | PUS | 0.04 | -1.5 | 26 min |
| UO 746 | 2026-08-30 | HKE | PEN | 0.05 | -1.2 | 21 min |
| TW 644 | 2026-09-01 | TWB | ICN | 0.06 | 0.7 | 22 min |
| VJ 985 | 2026-08-27 | VJC | PQC | 0.86 | 41.7 | 10 min |
| TG 601 | 2026-08-27 | THA | BKK | 0.79 | 46.8 | 15 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 3057 | 0.6709 | 0.1883 | 0.5582 | 15.8 | 2026-08-25T22:51:53+00:00 | 2026-09-01T17:30:09+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 3057}
