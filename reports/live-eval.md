# Live evaluation — predictions vs actuals

Generated 2026-08-19T10:46:40+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **1057**.

Dates 2026-08-17..2026-08-19; observed P(delay > 15) = 0.2091; median lead time between last score and departure = 23.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6402 | 0.1574 | 0.4905 | 13.682 |
| baseline_airline_hour | 0.6229 | 0.1645 | 0.5092 | 17.253 |
| naive_rate | 0.5 | 0.1654 | 0.5127 | 13.937 |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 1057}
