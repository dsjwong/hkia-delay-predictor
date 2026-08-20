# Live evaluation — predictions vs actuals

Generated 2026-08-20T07:09:59+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **1402**.

Dates 2026-08-17..2026-08-20; observed P(delay > 15) = 0.2375; median lead time between last score and departure = 25.6 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6635 | 0.1681 | 0.5148 | 14.571 |
| baseline_airline_hour | 0.6466 | 0.1734 | 0.5271 | 17.4 |
| naive_rate | 0.5 | 0.1811 | 0.5482 | 15.003 |

Model minus airline × hour baseline: AUC +0.0169 · Brier -0.0053 · log loss -0.0123 · MAE -2.83 min. The margin is modest — this is a lookup table with weather and congestion bolted on, not a crystal ball.

## Per day

| date | n | delayed > 15 | model AUC | baseline AUC | model Brier | model MAE | baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-17 | 293 | 0.2287 | 0.5923 | 0.5372 | 0.1726 | 16.2 | 20.3 |
| 2026-08-18 | 440 | 0.2386 | 0.7012 | 0.6549 | 0.1635 | 14.2 | 17.3 |
| 2026-08-19 | 439 | 0.1845 | 0.5825 | 0.6825 | 0.1530 | 11.9 | 15.2 |
| 2026-08-20 | 230 | 0.3478 | 0.7085 | 0.7267 | 0.1998 | 18.4 | 18.1 |

`*` = thin day (< 20 flights — treat as noise).

## By lead time (minutes between the last score and the actual departure)

| lead time | n | delayed > 15 | model AUC | baseline AUC | model MAE |
|---|---:|---:|---:|---:|---:|
| < 30 min | 811 | 0.1640 | 0.6974 | 0.6718 | 9.3 |
| 30–120 min | 560 | 0.3268 | 0.6190 | 0.6084 | 18.6 |
| 2–12 h | 31 | 0.5484 | 0.7563 | 0.6891 | 79.6 |
| > 12 h * | 0 | — | — | — | — |

`*` = thin bucket (< 20 flights — treat as noise). Scores written far ahead of departure know less: a bucket near 0.5 means no signal there.

## Calibration on live data (10 equal-width probability bins)

| bin | n | pred_mean | obs_rate |
|---|---:|---:|---:|
| 0.0-0.1 | 204 | 0.071 | 0.098 |
| 0.1-0.2 | 458 | 0.149 | 0.188 |
| 0.2-0.3 | 344 | 0.246 | 0.230 |
| 0.3-0.4 | 237 | 0.343 | 0.295 |
| 0.4-0.5 | 93 | 0.440 | 0.387 |
| 0.5-0.6 | 40 | 0.539 | 0.600 |
| 0.6-0.7 | 12 | 0.649 | 0.750 |
| 0.7-0.8 | 8 | 0.748 | 0.375 |
| 0.8-0.9 | 6 | 0.843 | 1.000 |

## Most confident correct calls

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| RA 410 | 2026-08-18 | RNA | KTM | 0.88 | 59.3 | 235 min |
| VJ 985 | 2026-08-18 | VJC | PQC | 0.87 | 39.9 | 28 min |
| LX 139 | 2026-08-18 | SWR | ZRH | 0.84 | 30.7 | 37 min |
| LX 139 | 2026-08-17 | SWR | ZRH | 0.84 | 32.8 | 24 min |
| CX 506 | 2026-08-20 | CPA | KIX | 0.81 | 42.0 | 105 min |

## Biggest misses

| flight | date | airline | dest | P(delay > 15) | predicted min | actual delay |
|---|---|---|---|---:|---:|---:|
| UO 616 | 2026-08-18 | HKE | ICN | 0.03 | -4.1 | 147 min |
| MH 073 | 2026-08-19 | MAS | KUL | 0.05 | 3.7 | 36 min |
| EK 385 | 2026-08-17 | UAE | BKK | 0.06 | 2.8 | 159 min |
| OD 606 | 2026-08-18 | MXD | KUL | 0.79 | 65.1 | 0 min |
| CX 239 | 2026-08-20 | CPA | LHR | 0.77 | 32.5 | -4 min |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 1402}
