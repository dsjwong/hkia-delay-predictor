# Live evaluation — predictions vs actuals

Generated 2026-08-25T18:56:24+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3122**.

Dates 2026-08-19..2026-08-26; observed P(delay > 15) = 0.2649; median lead time between last score and departure = 36.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6217 | 0.191 | 0.5706 | 15.611 |
| baseline_airline_hour | 0.63 | 0.1859 | 0.5557 | 17.34 |
| naive_rate | 0.5 | 0.1947 | 0.5781 | 15.664 |

Coverage: **3122 of 3159** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3122 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | -0.0083 | [-0.0286, +0.0112] | no — CI straddles 0 |
| brier | +0.0051 | [+0.0013, +0.0091] | no — CI straddles 0 |
| logloss | +0.0149 | [+0.0051, +0.0251] | no — CI straddles 0 |
| mae | -1.73 | [-2.0216, -1.4305] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-19 † | 402 | 0.1915 | 0.5807 | 0.6757 | 0.1576 | 11.8 | 15.3 |
| 2026-08-20 | 440 | 0.3250 | 0.6489 | 0.6899 | 0.2145 | 19.3 | 18.9 |
| 2026-08-21 | 461 | 0.3059 | 0.6261 | 0.6226 | 0.2057 | 17.9 | 18.4 |
| 2026-08-22 | 451 | 0.3902 | 0.5617 | 0.6649 | 0.2495 | 19.4 | 18.9 |
| 2026-08-23 | 452 | 0.2146 | 0.6040 | 0.6199 | 0.1661 | 13.5 | 16.7 |
| 2026-08-24 | 452 | 0.1947 | 0.5243 | 0.5938 | 0.1621 | 12.8 | 16.2 |
| 2026-08-25 | 434 | 0.2258 | 0.5556 | 0.5614 | 0.1795 | 14.6 | 17.2 |
| 2026-08-26 *† | 30 | 0.2333 | 0.7950 | 0.5683 | 0.1635 | 8.7 | 10.3 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 548 | 0.6916 | 0.5538 | 0.5853 | 29.0 |
| < 30 min | 1220 | 0.2197 | 0.6132 | 0.6428 | 14.3 |
| 30–120 min | 1139 | 0.1343 | 0.5796 | 0.6282 | 11.4 |
| 2–12 h | 213 | 0.1268 | 0.4559 | 0.5900 | 11.2 |
| > 12 h * | 2 | 0.0000 | — | — | 7.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 316 | 0.072 | 0.149 |
| 0.1-0.2 | 775 | 0.153 | 0.196 |
| 0.2-0.3 | 825 | 0.249 | 0.258 |
| 0.3-0.4 | 570 | 0.348 | 0.256 |
| 0.4-0.5 | 343 | 0.446 | 0.411 |
| 0.5-0.6 | 177 | 0.541 | 0.401 |
| 0.6-0.7 | 83 | 0.640 | 0.434 |
| 0.7-0.8 * | 19 | 0.730 | 0.421 |
| 0.8-0.9 * | 14 | 0.841 | 0.929 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| LX 139 | 2026-08-25 | SWR | ZRH | 0.88 | 31.4 | 24 min |
| RA 410 | 2026-08-25 | RNA | KTM | 0.88 | 62.9 | 80 min |
| VJ 985 | 2026-08-20 | VJC | PQC | 0.86 | 43.7 | 24 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 33 calls published at P ≥ 70%**, 21 were actually more than 15 minutes late (64%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 412 | 2026-08-24 | CCA | TFU | 0.03 | -7.0 | 26 min |
| OZ 746 | 2026-08-26 | AAR | ICN | 0.04 | -0.6 | 24 min |
| TW 640 | 2026-08-21 | TWB | PUS | 0.04 | -2.1 | 77 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |
| VJ 877 | 2026-08-23 | VJC | SGN | 0.77 | 35.1 | 7 min |

## By model version

| model_version | n | AUC | Brier | log loss | MAE (min) | first scored | last scored |
|---|---:|---:|---:|---:|---:|---|---|
| 2e00760@2026-08-16T16:13:29+00:00 | 2977 | 0.6205 | 0.1909 | 0.5701 | 15.6 | 2026-08-18T18:20:25+00:00 | 2026-08-25T09:05:49+00:00 |
| 4a4212f@2026-08-25T09:35:34+00:00 | 145 | 0.6785 | 0.1934 | 0.5796 | 16.9 | 2026-08-25T09:38:36+00:00 | 2026-08-25T17:52:49+00:00 |

Live confirmation that a newer model version is actually better takes weeks to accrue at this cron cadence — a version with few matured predictions here is not yet evidence either way.

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 2977, '4a4212f@2026-08-25T09:35:34+00:00': 145}
