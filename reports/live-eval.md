# Live evaluation — predictions vs actuals

Generated 2026-08-19T18:52:49+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **1202**.

Dates 2026-08-17..2026-08-20; observed P(delay > 15) = 0.2138; median lead time between last score and departure = 25.1 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6374 | 0.1604 | 0.498 | 13.669 |
| baseline_airline_hour | 0.6382 | 0.1649 | 0.5088 | 17.125 |
| naive_rate | 0.5 | 0.1681 | 0.519 | 14.097 |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 1202}
