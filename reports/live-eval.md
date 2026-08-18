# Live evaluation — predictions vs actuals

Generated 2026-08-18T18:55:35+00:00. Window: flights departed in the last 7 days; per flight, the last prediction written before its actual departure. Matured predictions: **762**.

Dates 2026-08-17..2026-08-19; observed P(delay > 15) = 0.2297; median lead time between last score and departure = 22.7 min.

| predictor | AUC | Brier | log loss | MAE (min) |
|---|---|---|---|---|
| model | 0.6557 | 0.1652 | 0.5086 | 14.797 |
| baseline_airline_hour | 0.613 | 0.1743 | 0.5331 | 18.216 |
| naive_rate | 0.5 | 0.1769 | 0.5389 | 15.424 |

Model versions in window: {'2e00760@2026-08-16T16:13:29+00:00': 762}
