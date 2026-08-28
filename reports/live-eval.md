# Live evaluation — predictions vs actuals

Generated 2026-08-28T02:10:29+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3091**.

Dates 2026-08-21..2026-08-28; observed P(delay > 15) = 0.2908; median lead time between last score and departure = 47.4 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6463 | 0.1981 | 0.5873 | 16.195 |
| baseline_airline_hour | 0.6147 | 0.1987 | 0.5857 | 17.607 |
| naive_rate | 0.5 | 0.2063 | 0.6029 | 16.233 |

Coverage: **3091 of 3225** departures in the window (95.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3091 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | +0.0316 | [+0.0110, +0.0531] | **yes** |
| brier | -0.0006 | [-0.0057, +0.0045] | no — CI straddles 0 |
| logloss | +0.0016 | [-0.0107, +0.0141] | no — CI straddles 0 |
| mae | -1.41 | [-1.7161, -1.1141] | **yes** |

The model is separably better on: auc, mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-21 † | 327 | 0.2997 | 0.6720 | 0.6466 | 0.1932 | 17.6 | 19.4 |
| 2026-08-22 | 451 | 0.3902 | 0.5617 | 0.6649 | 0.2495 | 19.4 | 18.9 |
| 2026-08-23 | 452 | 0.2146 | 0.6040 | 0.6199 | 0.1661 | 13.5 | 16.7 |
| 2026-08-24 | 452 | 0.1947 | 0.5243 | 0.5938 | 0.1621 | 12.8 | 16.2 |
| 2026-08-25 | 434 | 0.2258 | 0.5556 | 0.5614 | 0.1795 | 14.6 | 17.2 |
| 2026-08-26 | 438 | 0.3196 | 0.7291 | 0.6087 | 0.1844 | 16.4 | 18.3 |
| 2026-08-27 | 432 | 0.4306 | 0.5638 | 0.6145 | 0.2611 | 20.7 | 18.3 |
| 2026-08-28 † | 105 | 0.1524 | 0.4586 | 0.4575 | 0.1608 | 11.8 | 12.5 |

`†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 454 | 0.7181 | 0.5677 | 0.5937 | 30.7 |
| < 30 min | 981 | 0.2345 | 0.6280 | 0.6135 | 14.0 |
| 30–120 min | 1113 | 0.1914 | 0.6637 | 0.6043 | 12.2 |
| 2–12 h | 529 | 0.2420 | 0.6778 | 0.6278 | 16.4 |
| > 12 h * | 14 | 0.1429 | 0.7083 | 0.6667 | 10.3 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 239 | 0.073 | 0.163 |
| 0.1-0.2 | 693 | 0.154 | 0.195 |
| 0.2-0.3 | 743 | 0.249 | 0.252 |
| 0.3-0.4 | 534 | 0.347 | 0.266 |
| 0.4-0.5 | 352 | 0.447 | 0.378 |
| 0.5-0.6 | 256 | 0.546 | 0.457 |
| 0.6-0.7 | 197 | 0.646 | 0.487 |
| 0.7-0.8 | 59 | 0.734 | 0.576 |
| 0.8-0.9 * | 18 | 0.834 | 0.889 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |
| VJ 985 | 2026-08-22 | VJC | PQC | 0.85 | 48.7 | 19 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 77 calls published at P ≥ 70%**, 50 were actually more than 15 minutes late (65%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| LJ 714 | 2026-08-26 | JNA | CJU | 0.03 | -0.5 | 24 min |
| CA 412 | 2026-08-24 | CCA | TFU | 0.03 | -7.0 | 26 min |
| TW 640 | 2026-08-27 | TWB | PUS | 0.04 | -1.5 | 26 min |
| VJ 985 | 2026-08-27 | VJC | PQC | 0.86 | 41.7 | 10 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 2e00760@2026-08-16T16:13:29+00:00 | 2001 | 0.6070 | 0.1893 | 0.5685 | 15.3 | 2026-08-21T00:36:38+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 1090 | 0.6747 | 0.2143 | 0.6217 | 17.9 | 2026-08-25T09:38:36+00:00 | 2026-08-27T16:39:39+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 2001, '4a4212f@2026-08-25T09:35:34+00:00': 1090}
