# Live evaluation — predictions vs actuals

Generated 2026-08-17T18:56:26+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **313**.

Dates 2026-08-17..2026-08-18; observed P(delay > 15) = 0.2204; median lead time between last score and departure = 22.8 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.5802 | 0.17 | 0.5235 | 14.998 |
| baseline_airline_hour | 0.5409 | 0.1779 | 0.5413 | 19.029 |
| naive_rate | 0.5 | 0.1719 | 0.5275 | 15.112 |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 313}
