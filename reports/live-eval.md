# Live evaluation — predictions vs actuals

Generated 2026-09-06T20:23:10+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2874**.

Dates 2026-08-31..2026-09-07; observed P(delay > 15) = 0.1677; median lead time between last score and departure = 123.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6399 | 0.1501 | 0.4676 | 12.584 |
| baseline_airline_hour | 0.6124 | 0.151 | 0.4766 | 15.915 |
| naive_rate | 0.5 | 0.1396 | 0.4522 | 11.03 |

Coverage: **2874 of 2918** departures in the window (98.5%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2874 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0275 | [+0.0032, +0.0518] | **yes** |
| brier | -0.0009 | [-0.0049, +0.0029] | no — CI straddles 0 |
| logloss | -0.0090 | [-0.0194, +0.0013] | no — CI straddles 0 |
| mae | -3.33 | [-3.6493, -3.0006] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-31 † | 398 | 0.1960 | 0.6333 | 0.5908 | 0.1743 | 14.5 | 16.9 |
| 2026-09-01 | 403 | 0.1737 | 0.5722 | 0.6105 | 0.1938 | 15.2 | 15.6 |
| 2026-09-02 | 405 | 0.1802 | 0.6607 | 0.6256 | 0.1432 | 12.3 | 16.6 |
| 2026-09-03 | 393 | 0.1578 | 0.6067 | 0.5606 | 0.1317 | 10.8 | 16.0 |
| 2026-09-04 | 418 | 0.1770 | 0.7245 | 0.6272 | 0.1309 | 10.7 | 15.6 |
| 2026-09-05 | 410 | 0.1195 | 0.6704 | 0.6390 | 0.1133 | 10.8 | 16.3 |
| 2026-09-06 | 410 | 0.1732 | 0.6271 | 0.6146 | 0.1686 | 14.4 | 15.0 |
| 2026-09-07 *† | 37 | 0.1351 | 0.8187 | 0.7781 | 0.1034 | 6.3 | 10.2 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 95 | 0.6947 | 0.6834 | 0.5125 | 38.7 |
| < 30 min | 337 | 0.1484 | 0.6268 | 0.5849 | 10.5 |
| 30–120 min | 1037 | 0.1601 | 0.6537 | 0.6219 | 11.0 |
| 2–12 h | 1397 | 0.1432 | 0.6340 | 0.6313 | 12.5 |
| > 12 h * | 8 | 0.0000 | — | — | 5.9 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 513 | 0.065 | 0.062 |
| 0.1-0.2 | 790 | 0.149 | 0.137 |
| 0.2-0.3 | 671 | 0.248 | 0.171 |
| 0.3-0.4 | 402 | 0.345 | 0.261 |
| 0.4-0.5 | 285 | 0.448 | 0.242 |
| 0.5-0.6 | 127 | 0.543 | 0.244 |
| 0.6-0.7 | 68 | 0.645 | 0.235 |
| 0.7-0.8 * | 17 | 0.736 | 0.294 |
| 0.8-0.9 * | 1 | 0.806 | 1.000 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-09-01 | RNA | KTM | 0.81 | 45.1 | 182 min |
| CX 548 | 2026-09-01 | CPA | HND | 0.76 | 33.8 | 43 min |
| HX 608 | 2026-09-06 | CRK | NRT | 0.75 | 31.4 | 24 min |
| HX 618 | 2026-09-06 | CRK | KIX | 0.74 | 35.0 | 25 min |
| NH 812 | 2026-09-06 | ANA | NRT | 0.72 | 30.4 | 23 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 18 calls published at P ≥ 70%**, 6 were actually more than 15 minutes late (33%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 704 | 2026-09-03 | HKE | BKK | 0.02 | -2.8 | 21 min |
| NH 814 | 2026-09-03 | ANA | HND | 0.03 | -4.8 | 21 min |
| KE 2012 | 2026-09-05 | KAL | ICN | 0.03 | -2.5 | 161 min |
| LX 139 | 2026-08-31 | SWR | ZRH | 0.78 | 29.8 | 15 min |
| CX 520 | 2026-09-01 | CPA | NRT | 0.76 | 40.9 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2874 | 0.6399 | 0.1501 | 0.4676 | 12.6 | 2026-08-30T20:12:56+00:00 | 2026-09-06T17:59:29+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2874}
