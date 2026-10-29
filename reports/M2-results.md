# M2 results — baselines vs XGBoost, time-based split

Generated 2026-10-29T14:57:07+00:00 from `data/features.parquet` (71810 rows incl. cancelled; 71145 departed rows with labels used for modelling; git `42715b6`).

## Split (by date, no shuffling)

|       | date_min   | date_max   |   n_rows |   n_dates |   delayed15_rate |   inbound_known_rate |
|:------|:-----------|:-----------|---------:|----------:|-----------------:|---------------------:|
| train | 2026-05-16 | 2026-09-09 |    49770 |       117 |           0.2804 |               0.2484 |
| val   | 2026-09-10 | 2026-09-21 |     4885 |        12 |           0.139  |               0.2938 |
| test  | 2026-10-05 | 2026-10-29 |    10785 |        25 |           0.1543 |               0.2694 |
| cal   | 2026-09-22 | 2026-10-04 |     5705 |        13 |           0.1926 |               0.2659 |

## Metrics (classification: P(delay > 15 min); regression: delay minutes)

Baseline A = train global rate / mean. Baseline B = airline x scheduled-hour mean from the train split only (fallback: airline mean, then global). `median_train` = predict the train median delay (MAE reference).

|                       |      auc |   logloss |    brier |    mae |
|:----------------------|---------:|----------:|---------:|-------:|
| A_global (val)        |   0.5    |    0.4601 |   0.1397 | 16.882 |
| B_airline_hour (val)  |   0.658  |    0.4469 |   0.1368 | 16.489 |
| A_global (test)       |   0.5    |    0.4745 |   0.1464 | 17.714 |
| B_airline_hour (test) |   0.6592 |    0.458  |   0.1416 | 17.192 |
| median_train (test)   | nan      |  nan      | nan      | 12.731 |
| XGB (val)             |   0.7045 |    0.3752 |   0.1134 | 10.539 |
| XGB (test)            |   0.7088 |    0.3948 |   0.1212 | 11.67  |
| XGB_calibrated (test) |   0.7088 |    0.3932 |   0.1205 | 11.67  |

## Calibration on test (10 equal-width probability bins) — served, after the `platt` calibrator

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 | 3630 |       0.065 |      0.059 |
| 0.1-0.2 | 4020 |       0.146 |      0.141 |
| 0.2-0.3 | 2116 |       0.243 |      0.239 |
| 0.3-0.4 |  708 |       0.339 |      0.335 |
| 0.4-0.5 |  211 |       0.441 |      0.441 |
| 0.5-0.6 |   70 |       0.535 |      0.429 |
| 0.6-0.7 |   18 |       0.649 |      0.5   |
| 0.7-0.8 |    7 |       0.731 |      0.571 |
| 0.8-0.9 |    5 |       0.846 |      0.8   |

## Reliability of the raw model on test (before calibration)

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 | 3582 |       0.062 |      0.059 |
| 0.1-0.2 | 3545 |       0.146 |      0.133 |
| 0.2-0.3 | 2113 |       0.244 |      0.215 |
| 0.3-0.4 |  979 |       0.34  |      0.284 |
| 0.4-0.5 |  358 |       0.44  |      0.425 |
| 0.5-0.6 |  140 |       0.545 |      0.414 |
| 0.6-0.7 |   40 |       0.634 |      0.5   |
| 0.7-0.8 |   20 |       0.745 |      0.5   |
| 0.8-0.9 |    5 |       0.842 |      0.8   |
| 0.9-1.0 |    3 |       0.919 |      0.667 |

Calibrator fitted on the date-ordered calibration fold (2026-09-22..2026-10-04, 5705 rows; train < early-stop fold < calibration fold < test). Method chosen by blocked 4-fold out-of-fold log loss on that fold (identity 0.44849, platt 0.44822, isotonic 0.45247) -> **platt**. Served probabilities (`hkia.predict`) are calibrated; SHAP attributions stay on the raw booster. Test before -> after: {'auc': 0.7088, 'logloss': 0.3948, 'brier': 0.1212, 'mae': 11.67} -> {'auc': 0.7088, 'logloss': 0.3932, 'brier': 0.1205, 'mae': 11.67}.

## Feature importance (top 15 by gain) and permutation check on test (3 repeats)

|                            |   clf gain |   reg gain |   clf perm dAUC |   reg perm dMAE |
|:---------------------------|-----------:|-----------:|----------------:|----------------:|
| airline                    |       15.2 |     2667.6 |          0.0504 |          0.7421 |
| airline_prevday_mean_delay |       15.4 |     2574.9 |          0.0143 |          0.0642 |
| airline_sameday_mean_delay |            |            |          0.0029 |                 |
| airline_sameday_n          |            |            |                 |          0.029  |
| airport_sameday_mean_delay |       16.4 |     2791   |          0.0028 |          0.043  |
| airport_sameday_n          |            |            |          0.0031 |          0.1463 |
| ceiling_ft                 |            |     3013.7 |                 |                 |
| cong_pm30                  |            |            |          0.003  |          0.0373 |
| cong_pm60                  |            |            |          0.0019 |                 |
| cong_same_hour             |            |            |          0.0024 |          0.0307 |
| dest                       |            |            |          0.0394 |          0.3821 |
| dest_region                |            |            |          0.0022 |          0.029  |
| inbound_actual_slack_min   |            |            |          0.0018 |          0.0358 |
| inbound_confidence         |       15.8 |     2110.6 |                 |                 |
| inbound_known              |       51.2 |            |                 |                 |
| inbound_lateness_min       |       23.6 |     2272.3 |          0.0183 |          0.0868 |
| inbound_sched_slack_min    |       14.5 |     2001.6 |                 |                 |
| msn_signal                 |       19.7 |     2160.6 |                 |                 |
| sched_dow                  |            |            |          0.0028 |          0.0276 |
| sched_hour                 |       15.9 |     1964.8 |                 |          0.0574 |
| sched_minute_of_day        |       15.8 |     2111.6 |          0.0277 |          0.196  |
| tc_signal                  |       25.8 |     4797.1 |                 |                 |
| temp_c                     |       15.2 |     2552.1 |                 |          0.0517 |
| visib_sm                   |       18.1 |     2259.7 |                 |                 |
| wdir                       |            |            |          0.0039 |                 |
| wx_rain                    |      183.1 |    20617.1 |                 |                 |
| wx_ts                      |       46.3 |     5023.5 |                 |                 |

## Ablation — test AUC when a feature group is removed

| variant                  |   n_features |    auc |   logloss |   brier |     mae |
|:-------------------------|-------------:|-------:|----------:|--------:|--------:|
| full                     |           38 | 0.7088 |    0.3948 |  0.1212 |  11.67  |
| no_weather               |           24 | 0.6979 |    0.411  |  0.1276 | nan     |
| no_rolling               |           32 | 0.699  |    0.3987 |  0.1222 | nan     |
| no_inbound               |           33 | 0.6943 |    0.3997 |  0.1225 |  11.743 |
| no_weather_no_rolling    |           18 | 0.6962 |    0.4492 |  0.1412 | nan     |
| calendar+congestion only |            9 | 0.59   |    0.4825 |  0.1534 | nan     |

`mae` is fitted only for `full` and `no_inbound` (the two variants the inbound decision compares). **Leak rule for the inbound block:** link *existence* is rebuilt from scheduled departure times (`rotations --events sched`, so the pairing cannot depend on the label), and the link's *values* are gated at scheduled − 2 h — an inbound that went on blocks after that cutoff counts as unknown, exactly as it would at scoring time. **The ship decision is made at masked coverage:** every row here was trained and tested with `--inbound-dropout 0.25` applied to all three splits (inbound_known rate 0.2694 on test vs 0.3595 in the parquet), i.e. at the coverage deployment actually has, not the coverage the backfill has. The rows above are scored at the train-time test mask (seed 0 + 2); because one mask draw is itself a source of variance, the decision is taken on the mean over 5 independent test masks of the same two fitted models: ΔAUC 0.01464, ΔMAE -0.07896 min (full − no_inbound); 95 % CI on ΔAUC at test seed 0 [0.01188, 0.02315]. Gated in `scripts/inbound_gate.py`.

<!-- interpretation: hand-written, preserved by train.py -->
## Interpretation (hand-written, 2026-08-17; update 2026-10-29)

**Update 2026-10-29 — models refit, calibrator added.** Everything above this heading is regenerated by `train.py`; the bullets below were written against the 2026-08-17 model and are kept as written, so their numbers are *not* the shipped model's. The shipped model (refit 2026-10-29 on 117 train days to 2026-09-09, test 2026-10-05..29, 10,785 flights, late rate 15.4 %) reaches AUC 0.709 vs 0.659 for the airline × hour baseline and MAE 11.7 vs 17.2 min (a constant median guess scores 12.7). Calibration: the raw booster was over-confident in the middle of the range (P 0.3–0.4 predicted 0.34, observed 0.28; P 0.5–0.6 predicted 0.55, observed 0.41); a Platt map fitted on the 2026-09-22..10-04 calibration fold fixes P 0.1–0.5 (e.g. 0.3–0.4: 0.34 vs 0.335 observed) but only trims P 0.5–0.6 (0.535 vs 0.43 observed, n = 70), and moves test log loss 0.3948 → 0.3932 — a small gain, because the raw scores were already close to calibrated below P = 0.3, where most flights sit. Above P = 0.6 the test window holds only 18-40 flights per bin: too few to say the top is fixed. `retrain.yml` repeats this weekly behind a non-inferiority gate (`scripts/retrain_gate.py`).

- **The model beats both baselines, but not by a lot.** On the held-out last two weeks (2026-08-03..16) XGBoost reaches AUC 0.661 vs 0.623 for the airline x hour baseline (B) and 0.5 for the global rate; log loss 0.575 vs 0.585 (B) vs 0.604 (A). For regression it gets MAE 16.6 min vs 18.5 (B) and 17.4 for the "predict the train median" constant. Delay minutes are heavy-tailed (median 7, mean 17), so beating the median by <1 minute is a modest win.
- **Airline and destination carry most of the signal** (largest permutation drop: airline -0.036 AUC, dest -0.030, then scheduled time-of-day). Congestion counts add little on their own (calendar+congestion only: AUC 0.595).
- **Weather is worth about +0.013 AUC / -0.009 log loss** (ablation: full 0.661 vs no_weather 0.648) in a test window with no typhoon. The train/val windows contain Severe Typhoon Noul (signal 8/9 on 25-26 Jul), where mean delay was 120-250 min under signal 8/9 vs 16 min otherwise, so `tc_signal`, `wx_rain`, `visib_sm` get high gain — but this is learned from a handful of days and the test set cannot confirm it. Treat "typhoon adds X min" claims as anecdotal until more storms are in the data.
- **The point-in-time rolling delay features do not help classification on test** (no_rolling AUC 0.664 vs 0.661) though they help log loss/Brier slightly. Same-day airport mean delay is the most useful of them; the airline prior-day mean is nearly noise. They are kept because they are cheap and legitimately available at scoring time.
- **Calibration**: reasonable in the 0.2-0.6 range; the model is under-confident in the lowest bins (predicts 0.07, observed 0.14) — expected because the val split (used for early stopping) was the typhoon fortnight (40% delayed) while train was 27%. Only ~1% of test flights get P > 0.7. Consider isotonic/Platt recalibration on a rolling window in M3.
- **Caveats**: only 93 days of data spanning one season; `sched_month` was deliberately excluded (it is a time proxy with 3 values). Everything here is departures only, passenger flights only, HKT scheduled times, METAR from the IEM archive (hourly, ~99.7% coverage) plus live aviationweather obs.
