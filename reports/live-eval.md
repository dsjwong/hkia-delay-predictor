# Live evaluation — predictions vs actuals

Generated 2026-09-08T21:07:54+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **2816**.

Dates 2026-09-02..2026-09-09; observed P(delay > 15) = 0.141; median lead time between last score and departure = 123.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6727 | 0.1227 | 0.4001 | 11.182 |
| baseline_airline_hour | 0.6289 | 0.1396 | 0.4505 | 16.142 |
| naive_rate | 0.5 | 0.1211 | 0.4067 | 10.134 |

Coverage: **2816 of 2854** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 2816 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0438 | [+0.0162, +0.0706] | **yes** |
| brier | -0.0169 | [-0.0206, -0.0132] | **yes** |
| logloss | -0.0504 | [-0.0605, -0.0403] | **yes** |
| mae | -4.96 | [-5.2991, -4.6262] | **yes** |

The model is separably better on: auc, brier, logloss, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-02 † | 367 | 0.1771 | 0.6412 | 0.6329 | 0.1441 | 12.4 | 17.1 |
| 2026-09-03 | 393 | 0.1578 | 0.6067 | 0.5606 | 0.1317 | 10.8 | 16.0 |
| 2026-09-04 | 418 | 0.1770 | 0.7245 | 0.6272 | 0.1309 | 10.7 | 15.6 |
| 2026-09-05 | 410 | 0.1195 | 0.6704 | 0.6390 | 0.1133 | 10.8 | 16.3 |
| 2026-09-06 | 410 | 0.1732 | 0.6271 | 0.6146 | 0.1686 | 14.4 | 15.0 |
| 2026-09-07 | 400 | 0.0975 | 0.7261 | 0.7205 | 0.0904 | 9.9 | 16.5 |
| 2026-09-08 | 384 | 0.0885 | 0.6350 | 0.6201 | 0.0833 | 9.6 | 17.0 |
| 2026-09-09 *† | 34 | 0.0882 | 0.8495 | 0.9032 | 0.0724 | 7.4 | 11.4 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD * | 83 | 0.6386 | 0.5975 | 0.4805 | 40.1 |
| < 30 min | 315 | 0.1429 | 0.6714 | 0.5957 | 9.3 |
| 30–120 min | 1032 | 0.1376 | 0.6805 | 0.6120 | 9.9 |
| 2–12 h | 1369 | 0.1147 | 0.6842 | 0.6713 | 10.9 |
| > 12 h * | 17 | 0.0000 | — | — | 6.4 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 732 | 0.064 | 0.053 |
| 0.1-0.2 | 932 | 0.146 | 0.122 |
| 0.2-0.3 | 670 | 0.245 | 0.176 |
| 0.3-0.4 | 271 | 0.339 | 0.255 |
| 0.4-0.5 | 115 | 0.447 | 0.278 |
| 0.5-0.6 | 58 | 0.549 | 0.241 |
| 0.6-0.7 * | 29 | 0.646 | 0.241 |
| 0.7-0.8 * | 9 | 0.726 | 0.444 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| HX 608 | 2026-09-06 | CRK | NRT | 0.75 | 31.4 | 24 min |
| HX 618 | 2026-09-06 | CRK | KIX | 0.74 | 35.0 | 25 min |
| NH 812 | 2026-09-06 | ANA | NRT | 0.72 | 30.4 | 23 min |
| CX 504 | 2026-09-06 | CPA | NRT | 0.72 | 36.3 | 64 min |
| CX 342 | 2026-09-06 | CPA | SHA | 0.68 | 34.2 | 18 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 9 calls published at P ≥ 70%**, 4 were actually more than 15 minutes late (44%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 704 | 2026-09-03 | HKE | BKK | 0.02 | -2.8 | 21 min |
| NH 814 | 2026-09-03 | ANA | HND | 0.03 | -4.8 | 21 min |
| KE 2012 | 2026-09-05 | KAL | ICN | 0.03 | -2.5 | 161 min |
| DL 088 | 2026-09-06 | DAL | LAX | 0.74 | 38.0 | 10 min |
| OD 606 | 2026-09-06 | MXD | KUL | 0.73 | 69.3 | 0 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 4a4212f@2026-08-25T09:35:34+00:00 | 2816 | 0.6727 | 0.1227 | 0.4001 | 11.2 | 2026-09-01T20:03:26+00:00 | 2026-09-08T15:33:44+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'4a4212f@2026-08-25T09:35:34+00:00': 2816}
