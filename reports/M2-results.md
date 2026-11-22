# M2 results — baselines vs XGBoost, time-based split

Generated 2026-11-22T11:25:36+00:00 from `data/features.parquet` (81645 rows incl. cancelled; 80940 departed rows with labels used for modelling; git `e2c2178`).

## Split (by date, no shuffling)

|       | date_min   | date_max   |   n_rows |   n_dates |   delayed15_rate |   inbound_known_rate |
|:------|:-----------|:-----------|---------:|----------:|-----------------:|---------------------:|
| train | 2026-05-16 | 2026-09-26 |    56802 |       134 |           0.2644 |               0.2526 |
| val   | 2026-09-27 | 2026-10-10 |     6241 |        14 |           0.1836 |               0.2685 |
| test  | 2026-10-25 | 2026-11-22 |    11878 |        29 |           0.148  |               0.2788 |
| cal   | 2026-10-11 | 2026-10-24 |     6019 |        14 |           0.1538 |               0.2637 |

## Metrics (classification: P(delay > 15 min); regression: delay minutes)

Baseline A = train global rate / mean. Baseline B = airline x scheduled-hour mean from the train split only (fallback: airline mean, then global). `median_train` = predict the train median delay (MAE reference).

|                       |      auc |   logloss |    brier |    mae |
|:----------------------|---------:|----------:|---------:|-------:|
| A_global (val)        |   0.5    |    0.495  |   0.1564 | 17.799 |
| B_airline_hour (val)  |   0.6485 |    0.4781 |   0.1501 | 17.145 |
| A_global (test)       |   0.5    |    0.4585 |   0.1396 | 15.793 |
| B_airline_hour (test) |   0.6142 |    0.4491 |   0.1379 | 15.564 |
| median_train (test)   | nan      |  nan      | nan      | 11.537 |
| XGB (val)             |   0.7138 |    0.4327 |   0.1366 | 12.694 |
| XGB (test)            |   0.6857 |    0.3933 |   0.1191 | 10.96  |
| XGB_calibrated (test) |   0.6857 |    0.3908 |   0.1181 | 10.96  |

## Calibration on test (10 equal-width probability bins) — served, after the `platt` calibrator

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 | 4337 |       0.062 |      0.069 |
| 0.1-0.2 | 4391 |       0.144 |      0.141 |
| 0.2-0.3 | 2020 |       0.241 |      0.216 |
| 0.3-0.4 |  742 |       0.342 |      0.296 |
| 0.4-0.5 |  229 |       0.439 |      0.428 |
| 0.5-0.6 |  101 |       0.543 |      0.446 |
| 0.6-0.7 |   36 |       0.64  |      0.611 |
| 0.7-0.8 |   14 |       0.741 |      0.857 |
| 0.8-0.9 |    7 |       0.83  |      0.571 |
| 0.9-1.0 |    1 |       0.902 |      1     |

## Reliability of the raw model on test (before calibration)

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 | 3340 |       0.067 |      0.063 |
| 0.1-0.2 | 4481 |       0.146 |      0.126 |
| 0.2-0.3 | 2536 |       0.242 |      0.189 |
| 0.3-0.4 |  995 |       0.342 |      0.28  |
| 0.4-0.5 |  336 |       0.438 |      0.372 |
| 0.5-0.6 |  122 |       0.546 |      0.418 |
| 0.6-0.7 |   45 |       0.641 |      0.644 |
| 0.7-0.8 |   15 |       0.743 |      0.867 |
| 0.8-0.9 |    8 |       0.838 |      0.625 |

Calibrator fitted on the date-ordered calibration fold (2026-10-11..2026-10-24, 6019 rows; train < early-stop fold < calibration fold < test). Method chosen by blocked 4-fold out-of-fold log loss on that fold (identity 0.38759, platt 0.38725, isotonic 0.38995) -> **platt**. Served probabilities (`hkia.predict`) are calibrated; SHAP attributions stay on the raw booster. Test before -> after: {'auc': 0.6857, 'logloss': 0.3933, 'brier': 0.1191, 'mae': 10.96} -> {'auc': 0.6857, 'logloss': 0.3908, 'brier': 0.1181, 'mae': 10.96}.

## Feature importance (top 15 by gain) and permutation check on test (3 repeats)

|                            |   clf gain |   reg gain |   clf perm dAUC |   reg perm dMAE |
|:---------------------------|-----------:|-----------:|----------------:|----------------:|
| airline                    |       19.6 |     1839   |          0.0471 |          0.682  |
| airline_prevday_mean_delay |       25.8 |     2278.3 |          0.0262 |          0.1249 |
| airline_prevday_n          |            |            |          0.0018 |          0.0168 |
| airline_sameday_mean_delay |            |            |          0.0039 |          0.0257 |
| airline_sameday_n          |            |            |          0.0008 |          0.0283 |
| airport_sameday_mean_delay |       24.4 |     1870.9 |          0.0025 |                 |
| airport_sameday_n          |            |            |          0.0009 |          0.2733 |
| ceiling_ft                 |            |     2284.9 |                 |                 |
| cong_pm30                  |            |            |                 |          0.0241 |
| cong_pm60                  |            |            |                 |          0.0279 |
| dest                       |       15.2 |     1339.1 |          0.0362 |          0.3753 |
| dest_region                |            |            |                 |          0.0398 |
| inbound_actual_slack_min   |            |            |                 |          0.0157 |
| inbound_known              |       23.4 |            |                 |                 |
| inbound_lateness_min       |       32.5 |     1713.8 |          0.0123 |          0.0503 |
| inbound_sched_slack_min    |       23.1 |     1290.1 |          0.0036 |          0.0221 |
| msn_signal                 |       21.5 |     1652.3 |                 |                 |
| sched_hour                 |       19.1 |     1690.3 |          0.0018 |          0.0175 |
| sched_minute_of_day        |       18.1 |     1481.8 |          0.0113 |          0.3429 |
| tc_signal                  |       31.6 |     3569.3 |                 |                 |
| temp_c                     |       19.7 |     1958.3 |          0.0009 |                 |
| visib_sm                   |       21.7 |     1595.9 |                 |                 |
| wdir                       |            |            |          0.0017 |                 |
| wx_rain                    |      199.5 |    11257.7 |          0.0022 |                 |
| wx_ts                      |       45   |     4341.9 |                 |                 |

## Ablation — test AUC when a feature group is removed

| variant                  |   n_features |    auc |   logloss |   brier |     mae |
|:-------------------------|-------------:|-------:|----------:|--------:|--------:|
| full                     |           38 | 0.6857 |    0.3933 |  0.1191 |  10.96  |
| no_weather               |           24 | 0.6876 |    0.3939 |  0.1192 | nan     |
| no_rolling               |           32 | 0.6655 |    0.4045 |  0.1231 | nan     |
| no_inbound               |           33 | 0.6663 |    0.3995 |  0.1209 |  11.057 |
| no_weather_no_rolling    |           18 | 0.6595 |    0.4341 |  0.133  | nan     |
| calendar+congestion only |            9 | 0.5473 |    0.454  |  0.1384 | nan     |

`mae` is fitted only for `full` and `no_inbound` (the two variants the inbound decision compares). **Leak rule for the inbound block:** link *existence* is rebuilt from scheduled departure times (`rotations --events sched`, so the pairing cannot depend on the label), and the link's *values* are gated at scheduled − 2 h — an inbound that went on blocks after that cutoff counts as unknown, exactly as it would at scoring time. **The ship decision is made at masked coverage:** every row here was trained and tested with `--inbound-dropout 0.25` applied to all three splits (inbound_known rate 0.2788 on test vs 0.3747 in the parquet), i.e. at the coverage deployment actually has, not the coverage the backfill has. The rows above are scored at the train-time test mask (seed 0 + 2); because one mask draw is itself a source of variance, the decision is taken on the mean over 5 independent test masks of the same two fitted models: ΔAUC 0.01864, ΔMAE -0.10002 min (full − no_inbound); 95 % CI on ΔAUC at test seed 0 [0.01481, 0.025]. Gated in `scripts/inbound_gate.py`.

<!-- interpretation: hand-written, preserved by train.py -->
## Interpretation (hand-written, 2026-08-17; update 2026-10-29)

**Update 2026-10-29 — models refit, calibrator added.** Everything above this heading is regenerated by `train.py`; the bullets below were written against the 2026-08-17 model and are kept as written, so their numbers are *not* the current model's. The 2026-10-29 refit (117 train days to 2026-09-09 on 117 train days to 2026-09-09, test 2026-10-05..29, 10,785 flights, late rate 15.4 %) reaches AUC 0.709 vs 0.659 for the airline × hour baseline and MAE 11.7 vs 17.2 min (a constant median guess scores 12.7). Calibration: the raw booster was over-confident in the middle of the range (P 0.3–0.4 predicted 0.34, observed 0.28; P 0.5–0.6 predicted 0.55, observed 0.41); a Platt map fitted on the 2026-09-22..10-04 calibration fold fixes P 0.1–0.5 (e.g. 0.3–0.4: 0.34 vs 0.335 observed) but only trims P 0.5–0.6 (0.535 vs 0.43 observed, n = 70), and moves test log loss 0.3948 → 0.3932 — a small gain, because the raw scores were already close to calibrated below P = 0.3, where most flights sit. Above P = 0.6 the test window holds only 18-40 flights per bin: too few to say the top is fixed. `retrain.yml` repeats this weekly behind a non-inferiority gate (`scripts/retrain_gate.py`).

**Day-ahead check (the old one-off `inbound_gate.py` GATE-C failed).** Scored on the live schedule at 2026-10-29 22:59 HKT, the >12 h bucket (tomorrow, Fri 30 Oct) had mean P 0.249 for the refit vs 0.212 for the August model, +0.038 against GATE-C's +0.02 limit. That gate compares two models on one day, so it cannot say which is closer to the truth; a 7-day day-ahead backtest can. Each of 2026-10-22..28 was scored as of noon the day before (flights' actual times after that moment blanked, as live; same-day rolling stats empty, inbound unknown, latest METAR) with both models, n = 2,958 departures, observed late rate 18.5 %: refit mean P 0.203 / log loss 0.4518 / AUC 0.670 / MAE 16.2 min / 4 calls at P >= 0.7, August model 0.218 / 0.4582 / 0.658 / 16.8 min / 9 calls. So over that week the refit was closer to outcomes on every measure, the August model the more over-confident, and the 30 Oct jump is specific to that day's inputs (weather persistence terms and the empty same-day statistics move it) rather than a systematic day-ahead skew. One week is thin evidence and the live bucket is worth watching; the first two live weeks of the refit are the real test.

- **The model beats both baselines, but not by a lot.** On the held-out last two weeks (2026-08-03..16) XGBoost reaches AUC 0.661 vs 0.623 for the airline x hour baseline (B) and 0.5 for the global rate; log loss 0.575 vs 0.585 (B) vs 0.604 (A). For regression it gets MAE 16.6 min vs 18.5 (B) and 17.4 for the "predict the train median" constant. Delay minutes are heavy-tailed (median 7, mean 17), so beating the median by <1 minute is a modest win.
- **Airline and destination carry most of the signal** (largest permutation drop: airline -0.036 AUC, dest -0.030, then scheduled time-of-day). Congestion counts add little on their own (calendar+congestion only: AUC 0.595).
- **Weather is worth about +0.013 AUC / -0.009 log loss** (ablation: full 0.661 vs no_weather 0.648) in a test window with no typhoon. The train/val windows contain Severe Typhoon Noul (signal 8/9 on 25-26 Jul), where mean delay was 120-250 min under signal 8/9 vs 16 min otherwise, so `tc_signal`, `wx_rain`, `visib_sm` get high gain — but this is learned from a handful of days and the test set cannot confirm it. Treat "typhoon adds X min" claims as anecdotal until more storms are in the data.
- **The point-in-time rolling delay features do not help classification on test** (no_rolling AUC 0.664 vs 0.661) though they help log loss/Brier slightly. Same-day airport mean delay is the most useful of them; the airline prior-day mean is nearly noise. They are kept because they are cheap and legitimately available at scoring time.
- **Calibration**: reasonable in the 0.2-0.6 range; the model is under-confident in the lowest bins (predicts 0.07, observed 0.14) — expected because the val split (used for early stopping) was the typhoon fortnight (40% delayed) while train was 27%. Only ~1% of test flights get P > 0.7. Consider isotonic/Platt recalibration on a rolling window in M3.
- **Caveats**: only 93 days of data spanning one season; `sched_month` was deliberately excluded (it is a time proxy with 3 values). Everything here is departures only, passenger flights only, HKT scheduled times, METAR from the IEM archive (hourly, ~99.7% coverage) plus live aviationweather obs.
