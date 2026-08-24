# Live evaluation — predictions vs actuals

Generated 2026-08-24T18:58:49+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **3128**.

Dates 2026-08-18..2026-08-25; observed P(delay > 15) = 0.266; median lead time between last score and departure = 33.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6375 | 0.1887 | 0.5642 | 15.554 |
| baseline_airline_hour | 0.6417 | 0.1852 | 0.555 | 17.356 |
| naive_rate | 0.5 | 0.1952 | 0.5792 | 15.734 |

Coverage: **3128 of 3165** departures in the window (98.8%) carry a prediction written before they left; the rest were never scored in time and are excluded. They are not a random sample — a flight the cron misses is usually one that departed shortly after being scheduled — so the observed late rate above is the rate among *scored* flights, a little higher than the airport's.

## Model minus airline × hour baseline

Paired bootstrap, 2,000 resamples over the 3128 matured flights.

| metric | delta | 95 % CI | separable from noise? |
|---|---:|---|---|
| auc | -0.0042 | [-0.0238, +0.0159] | no — CI straddles 0 |
| brier | +0.0035 | [-0.0006, +0.0071] | no — CI straddles 0 |
| logloss | +0.0092 | [-0.0011, +0.0186] | no — CI straddles 0 |
| mae | -1.80 | [-2.0791, -1.5120] | **yes** |

The model is separably better on: mae. A metric whose CI straddles 0 is a margin this window cannot distinguish from luck — it is reported, not claimed.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-18 † | 403 | 0.2531 | 0.7011 | 0.6454 | 0.1700 | 14.8 | 17.9 |
| 2026-08-19 | 439 | 0.1845 | 0.5825 | 0.6825 | 0.1530 | 11.9 | 15.2 |
| 2026-08-20 | 440 | 0.3250 | 0.6489 | 0.6859 | 0.2145 | 19.3 | 18.9 |
| 2026-08-21 | 461 | 0.3059 | 0.6261 | 0.6224 | 0.2057 | 17.9 | 18.4 |
| 2026-08-22 | 451 | 0.3902 | 0.5617 | 0.6620 | 0.2495 | 19.4 | 18.9 |
| 2026-08-23 | 452 | 0.2146 | 0.6040 | 0.6225 | 0.1661 | 13.5 | 16.6 |
| 2026-08-24 | 451 | 0.1929 | 0.5268 | 0.6020 | 0.1608 | 12.3 | 15.7 |
| 2026-08-25 *† | 31 | 0.1613 | 0.3769 | 0.3038 | 0.1635 | 9.9 | 13.7 |

`*` = thin day (< 100 flights — AUC standard error is large, treat as noise). `†` = partial day (the rolling window starts and ends part-way through a day).

## By forecast horizon (minutes between the last score and the **scheduled** departure)

| horizon | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| after STD | 565 | 0.6743 | 0.5663 | 0.5713 | 29.4 |
| < 30 min | 1305 | 0.2107 | 0.6418 | 0.6639 | 13.8 |
| 30–120 min | 1052 | 0.1426 | 0.6048 | 0.6530 | 11.4 |
| 2–12 h | 204 | 0.1275 | 0.4542 | 0.5935 | 10.2 |
| > 12 h * | 2 | 0.0000 | — | — | 7.2 |

`*` = thin bucket (< 100 flights — AUC standard error is large, treat as noise). The horizon is measured against the *timetable*, not the actual departure: `actual_ts - scored_at` would be a function of the delay itself (a flight is only ever scored 6 h before it leaves because it left 6 h late), so bucketing on it would stratify by the outcome. `after STD` = the last score was written after the scheduled time, i.e. the flight was already visibly running late.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 329 | 0.073 | 0.137 |
| 0.1-0.2 | 793 | 0.153 | 0.190 |
| 0.2-0.3 | 842 | 0.249 | 0.251 |
| 0.3-0.4 | 559 | 0.348 | 0.288 |
| 0.4-0.5 | 313 | 0.445 | 0.431 |
| 0.5-0.6 | 176 | 0.541 | 0.409 |
| 0.6-0.7 | 82 | 0.640 | 0.439 |
| 0.7-0.8 * | 19 | 0.730 | 0.368 |
| 0.8-0.9 * | 15 | 0.841 | 0.933 |

`*` = fewer than 30 flights in the bin: the observed rate moves by 1/n per flight, so these points wander a long way on their own.

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-22 | RNA | KTM | 0.89 | 55.1 | 40 min |
| RA 410 | 2026-08-18 | RNA | KTM | 0.88 | 59.3 | 235 min |
| VJ 985 | 2026-08-18 | VJC | PQC | 0.87 | 39.9 | 28 min |
| VJ 985 | 2026-08-20 | VJC | PQC | 0.86 | 43.7 | 24 min |
| LX 139 | 2026-08-24 | SWR | ZRH | 0.86 | 32.1 | 46 min |

That table is picked *after* the fact — it can only ever contain wins. The honest counterpart: of **all 34 calls published at P ≥ 70%**, 21 were actually more than 15 minutes late (62%).

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| CA 412 | 2026-08-24 | CCA | TFU | 0.03 | -7.0 | 26 min |
| UO 616 | 2026-08-18 | HKE | ICN | 0.03 | -4.1 | 147 min |
| TW 640 | 2026-08-21 | TWB | PUS | 0.04 | -2.1 | 77 min |
| OD 606 | 2026-08-22 | MXD | KUL | 0.81 | 74.0 | -1 min |
| OD 606 | 2026-08-18 | MXD | KUL | 0.79 | 65.1 | 0 min |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 3128}
