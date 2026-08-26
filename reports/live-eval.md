# Live evaluation — predictions vs actuals

Generated 2026-08-26T20:02:26+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3114**.

Dates 2026-08-20..2026-08-27; observed P(delay > 15) = 0.2864; median lead time between last score and departure = 37.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6391 | 0.196 | 0.5827 | 16.19 |
| baseline_airline_hour | 0.6193 | 0.1961 | 0.5799 | 17.66 |
| naive_rate | 0.5 | 0.2044 | 0.5989 | 16.323 |

Coverage: **3114 of 3155** departures in the window (98.7%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3114 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0198 | [-0.0013, +0.0391] | no — CI straddles 0 |
| brier | -0.0001 | [-0.0041, +0.0044] | no — CI straddles 0 |
| logloss | +0.0028 | [-0.0074, +0.0143] | no — CI straddles 0 |
| mae | -1.47 | [-1.7505, -1.1907] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-20 † | 399 | 0.3434 | 0.6320 | 0.6843 | 0.2231 | 19.8 | 19.1 |
| 2026-08-21 | 461 | 0.3059 | 0.6261 | 0.6226 | 0.2057 | 17.9 | 18.4 |
| 2026-08-22 | 451 | 0.3902 | 0.5617 | 0.6649 | 0.2495 | 19.4 | 18.9 |
| 2026-08-23 | 452 | 0.2146 | 0.6040 | 0.6199 | 0.1661 | 13.5 | 16.7 |
| 2026-08-24 | 452 | 0.1947 | 0.5243 | 0.5938 | 0.1621 | 12.8 | 16.2 |
| 2026-08-25 | 434 | 0.2258 | 0.5556 | 0.5614 | 0.1795 | 14.6 | 17.2 |
| 2026-08-26 | 438 | 0.3196 | 0.7291 | 0.6087 | 0.1844 | 15.4 | 17.3 |
| 2026-08-27 *† | 27 | 0.5556 | 0.5750 | 0.6389 | 0.2586 | 20.2 | 16.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 581 | 0.7074 | 0.5924 | 0.6080 | 28.5 |
| < 30 min | 1182 | 0.2327 | 0.6126 | 0.6237 | 15.0 |
| 30–120 min | 1135 | 0.1559 | 0.5975 | 0.6067 | 12.0 |
| 2–12 h | 214 | 0.1355 | 0.4758 | 0.5798 | 11.3 |
| > 12 h * | 2 | 0.0000 | — | — | 7.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 237 | 0.073 | 0.165 |
| 0.1-0.2 | 692 | 0.154 | 0.197 |
| 0.2-0.3 | 796 | 0.250 | 0.250 |
| 0.3-0.4 | 596 | 0.349 | 0.268 |
| 0.4-0.5 | 392 | 0.446 | 0.413 |
| 0.5-0.6 | 234 | 0.543 | 0.440 |
| 0.6-0.7 | 110 | 0.640 | 0.482 |
| 0.7-0.8 | 39 | 0.733 | 0.590 |
| 0.8-0.9 * | 18 | 0.834 | 0.944 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| VJ 985 | 2026-08-20 | VJC | PQC | 0.86 | 43.7 | 24 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 57 calls published at P ≥ 70%**, 40 were actually more than 15 minutes late (70%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-08-26 | JNA | CJU | 0.03 | -0.5 | 24 min |
| CA 412 | 2026-08-24 | CCA | TFU | 0.03 | -7.0 | 26 min |
| OZ 746 | 2026-08-26 | AAR | ICN | 0.04 | -0.6 | 24 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |
| VJ 877 | 2026-08-23 | VJC | SGN | 0.77 | 35.1 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 2e00760@2026-08-16T16:13:29+00:00 | 2534 | 0.6177 | 0.1971 | 0.5846 | 16.2 | 2026-08-19T17:47:19+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 580 | 0.7127 | 0.1912 | 0.5748 | 16.3 | 2026-08-25T09:38:36+00:00 | 2026-08-26T16:08:54+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 2534, '4a4212f@2026-08-25T09:35:34+00:00': 580}
