# M2 results — baselines vs XGBoost, time-based split

Generated 2026-08-25T09:35:34+00:00 from `data/features.parquet` (43885 rows incl. cancelled; 43374 departed rows with labels used for modelling; git `4a4212f`).

## Split (by date, no shuffling)

|       | date_min   | date_max   |   n_rows |   n_dates |   delayed15_rate |   inbound_known_rate |
|:------|:-----------|:-----------|---------:|----------:|-----------------:|---------------------:|
| train | 2026-05-16 | 2026-07-25 |    29803 |        71 |           0.2771 |               0.2469 |
| val   | 2026-07-26 | 2026-08-10 |     6991 |        16 |           0.3725 |               0.2437 |
| test  | 2026-08-11 | 2026-08-25 |     6580 |        15 |           0.2792 |               0.2473 |

## Metrics (classification: P(delay > 15 min); regression: delay minutes)

Baseline A = train global rate / mean. Baseline B = airline x scheduled-hour mean from the train split only (fallback: airline mean, then global). `median_train` = predict the train median delay (MAE reference).

|                       |      auc |   logloss |    brier |    mae |
|:----------------------|---------:|----------:|---------:|-------:|
| A_global (val)        |   0.5    |    0.6817 |   0.2428 | 22.142 |
| B_airline_hour (val)  |   0.6272 |    0.6619 |   0.2314 | 21.519 |
| A_global (test)       |   0.5    |    0.5922 |   0.2012 | 18.643 |
| B_airline_hour (test) |   0.628  |    0.5702 |   0.1923 | 18.135 |
| median_train (test)   | nan      |  nan      | nan      | 16.633 |
| XGB (val)             |   0.7189 |    0.5919 |   0.2016 | 19.655 |
| XGB (test)            |   0.6931 |    0.5455 |   0.1818 | 15.721 |

## Calibration on test (10 equal-width probability bins)

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 |  965 |       0.07  |      0.112 |
| 0.1-0.2 | 1733 |       0.148 |      0.186 |
| 0.2-0.3 | 1489 |       0.251 |      0.244 |
| 0.3-0.4 | 1074 |       0.346 |      0.351 |
| 0.4-0.5 |  672 |       0.446 |      0.438 |
| 0.5-0.6 |  380 |       0.544 |      0.511 |
| 0.6-0.7 |  179 |       0.645 |      0.631 |
| 0.7-0.8 |   63 |       0.737 |      0.635 |
| 0.8-0.9 |   24 |       0.843 |      0.958 |
| 0.9-1.0 |    1 |       0.92  |      1     |

## Feature importance (top 15 by gain) and permutation check on test (3 repeats)

|                            |   clf gain |   reg gain |   clf perm dAUC |   reg perm dMAE |
|:---------------------------|-----------:|-----------:|----------------:|----------------:|
| airline                    |       16.1 |     1207.5 |          0.0387 |          0.7269 |
| airline_prevday_mean_delay |       13.5 |            |          0.0049 |          0.0396 |
| airline_sameday_mean_delay |            |            |          0.0026 |                 |
| airport_sameday_mean_delay |       14.5 |     1066.5 |          0.0072 |          0.1242 |
| airport_sameday_n          |            |            |          0.0044 |          0.3777 |
| ceiling_ft                 |            |     2523.2 |                 |                 |
| cong_same_hour             |            |            |          0.0025 |          0.0365 |
| dest                       |            |      791.6 |          0.0179 |          0.3217 |
| dest_region                |            |            |          0.0035 |          0.0553 |
| dewp_c                     |       14   |            |                 |                 |
| flt_cat                    |            |      951.5 |                 |                 |
| inbound_actual_slack_min   |            |            |          0.0046 |          0.0603 |
| inbound_confidence         |       17   |            |                 |                 |
| inbound_lateness_min       |       14.5 |      804.4 |          0.01   |          0.0774 |
| inbound_sched_slack_min    |       18.6 |            |          0.0046 |          0.0259 |
| msn_signal                 |       16.1 |     1100   |                 |                 |
| sched_dow                  |            |      955.9 |          0.0038 |                 |
| sched_hour                 |       14.6 |     1062.3 |                 |          0.0465 |
| sched_minute_of_day        |       14.8 |     1082.8 |          0.0202 |          0.4786 |
| tc_signal                  |       24.9 |     3195.3 |                 |                 |
| temp_c                     |       15.2 |     1124.5 |          0.0106 |          0.1449 |
| visib_sm                   |       25   |     1751.4 |                 |                 |
| wspd_kt                    |            |            |                 |          0.0425 |
| wx_rain                    |      175.2 |     7008.6 |          0.0056 |                 |
| wx_ts                      |       45.9 |     3961.2 |                 |          0.0299 |

## Ablation — test AUC when a feature group is removed

| variant                  |   n_features |    auc |   logloss |   brier |     mae |
|:-------------------------|-------------:|-------:|----------:|--------:|--------:|
| full                     |           38 | 0.6931 |    0.5455 |  0.1818 |  15.721 |
| no_weather               |           24 | 0.6714 |    0.5653 |  0.191  | nan     |
| no_rolling               |           32 | 0.6849 |    0.5495 |  0.1835 | nan     |
| no_inbound               |           33 | 0.6724 |    0.5545 |  0.1854 |  15.947 |
| no_weather_no_rolling    |           18 | 0.6798 |    0.5547 |  0.1866 | nan     |
| calendar+congestion only |            9 | 0.6099 |    0.5828 |  0.1978 | nan     |

`mae` is fitted only for `full` and `no_inbound` (the two variants the inbound decision compares). **Leak rule for the inbound block:** link *existence* is rebuilt from scheduled departure times (`rotations --events sched`, so the pairing cannot depend on the label), and the link's *values* are gated at scheduled − 2 h — an inbound that went on blocks after that cutoff counts as unknown, exactly as it would at scoring time. **The ship decision is made at masked coverage:** every row here was trained and tested with `--inbound-dropout 0.25` applied to all three splits (inbound_known rate 0.2473 on test vs 0.3246 in the parquet), i.e. at the coverage deployment actually has, not the coverage the backfill has. The rows above are scored at the train-time test mask (seed 0 + 2); because one mask draw is itself a source of variance, the decision is taken on the mean over 5 independent test masks of the same two fitted models: ΔAUC 0.01875, ΔMAE -0.20228 min (full − no_inbound); 95 % CI on ΔAUC at test seed 0 [0.01284, 0.02361]. Gated in `scripts/inbound_gate.py`.

<!-- interpretation: hand-written, preserved by train.py -->
## Interpretation (hand-written, 2026-08-17)

- **The model beats both baselines, but not by a lot.** On the held-out last two weeks (2026-08-03..16) XGBoost reaches AUC 0.661 vs 0.623 for the airline x hour baseline (B) and 0.5 for the global rate; log loss 0.575 vs 0.585 (B) vs 0.604 (A). For regression it gets MAE 16.6 min vs 18.5 (B) and 17.4 for the "predict the train median" constant. Delay minutes are heavy-tailed (median 7, mean 17), so beating the median by <1 minute is a modest win.
- **Airline and destination carry most of the signal** (largest permutation drop: airline -0.036 AUC, dest -0.030, then scheduled time-of-day). Congestion counts add little on their own (calendar+congestion only: AUC 0.595).
- **Weather is worth about +0.013 AUC / -0.009 log loss** (ablation: full 0.661 vs no_weather 0.648) in a test window with no typhoon. The train/val windows contain Severe Typhoon Noul (signal 8/9 on 25-26 Jul), where mean delay was 120-250 min under signal 8/9 vs 16 min otherwise, so `tc_signal`, `wx_rain`, `visib_sm` get high gain — but this is learned from a handful of days and the test set cannot confirm it. Treat "typhoon adds X min" claims as anecdotal until more storms are in the data.
- **The point-in-time rolling delay features do not help classification on test** (no_rolling AUC 0.664 vs 0.661) though they help log loss/Brier slightly. Same-day airport mean delay is the most useful of them; the airline prior-day mean is nearly noise. They are kept because they are cheap and legitimately available at scoring time.
- **Calibration**: reasonable in the 0.2-0.6 range; the model is under-confident in the lowest bins (predicts 0.07, observed 0.14) — expected because the val split (used for early stopping) was the typhoon fortnight (40% delayed) while train was 27%. Only ~1% of test flights get P > 0.7. Consider isotonic/Platt recalibration on a rolling window in M3.
- **Caveats**: only 93 days of data spanning one season; `sched_month` was deliberately excluded (it is a time proxy with 3 values). Everything here is departures only, passenger flights only, HKT scheduled times, METAR from the IEM archive (hourly, ~99.7% coverage) plus live aviationweather obs.
