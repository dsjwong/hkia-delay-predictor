# M2 results — baselines vs XGBoost, time-based split

Generated 2026-08-16T16:13:29+00:00 from `data/features.parquet` (39979 rows incl. cancelled; 39480 departed rows with labels used for modelling; git `2e00760`).

## Split (by date, no shuffling)

|       | date_min   | date_max   |   n_rows |   n_dates |   delayed15_rate |
|:------|:-----------|:-----------|---------:|----------:|-----------------:|
| train | 2026-05-16 | 2026-07-19 |    27135 |        65 |           0.2747 |
| val   | 2026-07-20 | 2026-08-02 |     6093 |        14 |           0.4    |
| test  | 2026-08-03 | 2026-08-16 |     6252 |        14 |           0.2909 |

## Metrics (classification: P(delay > 15 min); regression: delay minutes)

Baseline A = train global rate / mean. Baseline B = airline x scheduled-hour mean from the train split only (fallback: airline mean, then global). `median_train` = predict the train median delay (MAE reference).

|                       |      auc |   logloss |    brier |    mae |
|:----------------------|---------:|----------:|---------:|-------:|
| A_global (val)        |   0.5    |    0.7095 |   0.2557 | 23.114 |
| B_airline_hour (val)  |   0.6427 |    0.6849 |   0.2418 | 22.328 |
| A_global (test)       |   0.5    |    0.6037 |   0.2066 | 19.06  |
| B_airline_hour (test) |   0.6231 |    0.5849 |   0.1979 | 18.532 |
| median_train (test)   | nan      |  nan      | nan      | 17.351 |
| XGB (val)             |   0.7365 |    0.5853 |   0.2008 | 20.631 |
| XGB (test)            |   0.6614 |    0.5754 |   0.1934 | 16.602 |

## Calibration on test (10 equal-width probability bins)

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 |  735 |       0.071 |      0.139 |
| 0.1-0.2 | 1807 |       0.15  |      0.203 |
| 0.2-0.3 | 1694 |       0.246 |      0.278 |
| 0.3-0.4 |  944 |       0.347 |      0.367 |
| 0.4-0.5 |  492 |       0.446 |      0.427 |
| 0.5-0.6 |  359 |       0.548 |      0.526 |
| 0.6-0.7 |  162 |       0.643 |      0.562 |
| 0.7-0.8 |   39 |       0.743 |      0.692 |
| 0.8-0.9 |   19 |       0.845 |      0.789 |
| 0.9-1.0 |    1 |       0.922 |      1     |

## Feature importance (top 15 by gain) and permutation check on test (3 repeats)

|                            |   clf gain |   reg gain |   clf perm dAUC |   reg perm dMAE |
|:---------------------------|-----------:|-----------:|----------------:|----------------:|
| airline                    |       15.4 |     1064.7 |          0.0361 |          0.6637 |
| airline_prevday_mean_delay |       14   |      739.7 |          0.0015 |                 |
| airline_prevday_n          |            |            |                 |          0.047  |
| airline_sameday_mean_delay |            |            |          0.0017 |                 |
| airport_sameday_mean_delay |       17.2 |     1136.7 |          0.0068 |          0.076  |
| airport_sameday_n          |            |            |          0.0091 |          0.364  |
| ceiling_ft                 |            |     2073.9 |                 |                 |
| cong_same_hour             |            |            |          0.0022 |                 |
| dest                       |       10.7 |      757.8 |          0.0296 |          0.3816 |
| dest_region                |            |            |          0.0043 |          0.0563 |
| dewp_c                     |       14.8 |      810.1 |                 |                 |
| flt_cat                    |       12   |      977.4 |                 |                 |
| metar_age_min              |            |            |          0.001  |          0.0331 |
| msn_signal                 |       10.6 |            |                 |                 |
| sched_dow                  |            |      908.6 |          0.0051 |          0.1001 |
| sched_hour                 |       13.5 |     1083   |          0.0009 |          0.0434 |
| sched_minute_of_day        |       13.2 |      954.9 |          0.023  |          0.4642 |
| tc_signal                  |       20.1 |     2685.2 |                 |                 |
| temp_c                     |       15.7 |     1039.8 |          0.008  |          0.1538 |
| terminal                   |       11.9 |            |                 |                 |
| visib_sm                   |       34   |     2033.4 |                 |                 |
| wdir                       |            |            |                 |          0.0329 |
| wspd_kt                    |            |            |                 |          0.025  |
| wx_rain                    |      155.4 |     5840   |          0.0032 |          0.0615 |
| wx_ts                      |       32.5 |     2809   |          0.0009 |          0.0223 |

## Ablation — test AUC when a feature group is removed

| variant                  |   n_features |    auc |   logloss |   brier |
|:-------------------------|-------------:|-------:|----------:|--------:|
| full                     |           33 | 0.6614 |    0.5754 |  0.1934 |
| no_weather               |           19 | 0.6482 |    0.5848 |  0.1984 |
| no_rolling               |           27 | 0.6639 |    0.5889 |  0.1965 |
| no_weather_no_rolling    |           13 | 0.6565 |    0.5761 |  0.1948 |
| calendar+congestion only |            9 | 0.595  |    0.5964 |  0.2036 |

<!-- interpretation: hand-written, preserved by train.py -->
## Interpretation (hand-written, 2026-08-17)

- **The model beats both baselines, but not by a lot.** On the held-out last two weeks (2026-08-03..16) XGBoost reaches AUC 0.661 vs 0.623 for the airline x hour baseline (B) and 0.5 for the global rate; log loss 0.575 vs 0.585 (B) vs 0.604 (A). For regression it gets MAE 16.6 min vs 18.5 (B) and 17.4 for the "predict the train median" constant. Delay minutes are heavy-tailed (median 7, mean 17), so beating the median by <1 minute is a modest win.
- **Airline and destination carry most of the signal** (largest permutation drop: airline -0.036 AUC, dest -0.030, then scheduled time-of-day). Congestion counts add little on their own (calendar+congestion only: AUC 0.595).
- **Weather is worth about +0.013 AUC / -0.009 log loss** (ablation: full 0.661 vs no_weather 0.648) in a test window with no typhoon. The train/val windows contain Severe Typhoon Noul (signal 8/9 on 25-26 Jul), where mean delay was 120-250 min under signal 8/9 vs 16 min otherwise, so `tc_signal`, `wx_rain`, `visib_sm` get high gain — but this is learned from a handful of days and the test set cannot confirm it. Treat "typhoon adds X min" claims as anecdotal until more storms are in the data.
- **The point-in-time rolling delay features do not help classification on test** (no_rolling AUC 0.664 vs 0.661) though they help log loss/Brier slightly. Same-day airport mean delay is the most useful of them; the airline prior-day mean is nearly noise. They are kept because they are cheap and legitimately available at scoring time.
- **Calibration**: reasonable in the 0.2-0.6 range; the model is under-confident in the lowest bins (predicts 0.07, observed 0.14) — expected because the val split (used for early stopping) was the typhoon fortnight (40% delayed) while train was 27%. Only ~1% of test flights get P > 0.7. Consider isotonic/Platt recalibration on a rolling window in M3.
- **Caveats**: only 93 days of data spanning one season; `sched_month` was deliberately excluded (it is a time proxy with 3 values). Everything here is departures only, passenger flights only, HKT scheduled times, METAR from the IEM archive (hourly, ~99.7% coverage) plus live aviationweather obs.
