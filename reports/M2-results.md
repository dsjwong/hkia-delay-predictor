# M2 results — baselines vs XGBoost, time-based split

Generated 2026-11-01T10:28:21+00:00 from `data/features.parquet` (73004 rows incl. cancelled; 72331 departed rows with labels used for modelling; git `f6ae66c`).

## Split (by date, no shuffling)

|       | date_min   | date_max   |   n_rows |   n_dates |   delayed15_rate |   inbound_known_rate |
|:------|:-----------|:-----------|---------:|----------:|-----------------:|---------------------:|
| train | 2026-05-16 | 2026-09-11 |    50583 |       119 |           0.2784 |               0.2491 |
| val   | 2026-09-12 | 2026-09-23 |     4907 |        12 |           0.1392 |               0.2931 |
| test  | 2026-10-07 | 2026-11-01 |    11071 |        26 |           0.1527 |               0.2703 |
| cal   | 2026-09-24 | 2026-10-06 |     5770 |        13 |           0.1901 |               0.264  |

## Metrics (classification: P(delay > 15 min); regression: delay minutes)

Baseline A = train global rate / mean. Baseline B = airline x scheduled-hour mean from the train split only (fallback: airline mean, then global). `median_train` = predict the train median delay (MAE reference).

|                       |      auc |   logloss |    brier |    mae |
|:----------------------|---------:|----------:|---------:|-------:|
| A_global (val)        |   0.5    |    0.4589 |   0.1392 | 16.895 |
| B_airline_hour (val)  |   0.6586 |    0.4455 |   0.1363 | 16.512 |
| A_global (test)       |   0.5    |    0.4717 |   0.1452 | 17.284 |
| B_airline_hour (test) |   0.6615 |    0.4543 |   0.14   | 16.757 |
| median_train (test)   | nan      |  nan      | nan      | 12.421 |
| XGB (val)             |   0.7062 |    0.3748 |   0.1133 | 10.64  |
| XGB (test)            |   0.7134 |    0.3912 |   0.1197 | 11.33  |
| XGB_calibrated (test) |   0.7134 |    0.3891 |   0.1188 | 11.33  |

## Calibration on test (10 equal-width probability bins) — served, after the `platt` calibrator

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 | 3599 |       0.066 |      0.059 |
| 0.1-0.2 | 4155 |       0.145 |      0.132 |
| 0.2-0.3 | 2259 |       0.243 |      0.233 |
| 0.3-0.4 |  718 |       0.339 |      0.331 |
| 0.4-0.5 |  232 |       0.442 |      0.47  |
| 0.5-0.6 |   78 |       0.542 |      0.462 |
| 0.6-0.7 |   15 |       0.647 |      0.533 |
| 0.7-0.8 |   11 |       0.727 |      0.727 |
| 0.8-0.9 |    4 |       0.864 |      0.75  |

## Reliability of the raw model on test (before calibration)

|         |    n |   pred_mean |   obs_rate |
|:--------|-----:|------------:|-----------:|
| 0.0-0.1 | 3461 |       0.064 |      0.058 |
| 0.1-0.2 | 3724 |       0.146 |      0.123 |
| 0.2-0.3 | 2251 |       0.245 |      0.203 |
| 0.3-0.4 | 1047 |       0.342 |      0.306 |
| 0.4-0.5 |  358 |       0.441 |      0.399 |
| 0.5-0.6 |  150 |       0.545 |      0.447 |
| 0.6-0.7 |   54 |       0.637 |      0.5   |
| 0.7-0.8 |   18 |       0.756 |      0.611 |
| 0.8-0.9 |    5 |       0.833 |      0.8   |
| 0.9-1.0 |    3 |       0.925 |      0.667 |

Calibrator fitted on the date-ordered calibration fold (2026-09-24..2026-10-06, 5770 rows; train < early-stop fold < calibration fold < test). Method chosen by blocked 4-fold out-of-fold log loss on that fold (identity 0.44517, platt 0.44479, isotonic 0.44833) -> **platt**. Served probabilities (`hkia.predict`) are calibrated; SHAP attributions stay on the raw booster. Test before -> after: {'auc': 0.7134, 'logloss': 0.3912, 'brier': 0.1197, 'mae': 11.33} -> {'auc': 0.7134, 'logloss': 0.3891, 'brier': 0.1188, 'mae': 11.33}.

## Feature importance (top 15 by gain) and permutation check on test (3 repeats)

|                            |   clf gain |   reg gain |   clf perm dAUC |   reg perm dMAE |
|:---------------------------|-----------:|-----------:|----------------:|----------------:|
| airline                    |       16.3 |     2651   |          0.0472 |          0.7159 |
| airline_prevday_mean_delay |       17.7 |     2957.6 |          0.0145 |          0.0734 |
| airline_prevday_n          |            |            |          0.0025 |                 |
| airline_sameday_mean_delay |            |            |          0.0034 |                 |
| airline_sameday_n          |            |            |                 |          0.0225 |
| airport_sameday_mean_delay |       16.7 |     2862.1 |          0.0016 |          0.0392 |
| airport_sameday_n          |            |            |          0.0045 |          0.1494 |
| ceiling_ft                 |            |     3455   |                 |                 |
| cong_pm30                  |            |            |          0.0035 |          0.038  |
| cong_pm60                  |            |            |                 |          0.0284 |
| cong_same_hour             |            |            |          0.004  |          0.0292 |
| dest                       |       12.6 |            |          0.0363 |          0.4115 |
| dest_region                |            |            |          0.0045 |          0.0394 |
| inbound_known              |       30   |            |                 |                 |
| inbound_lateness_min       |       24   |     1987.4 |          0.0135 |          0.0527 |
| inbound_sched_slack_min    |       18.9 |     2464.2 |          0.0024 |          0.0266 |
| msn_signal                 |       21.5 |     2291.5 |                 |                 |
| sched_dow                  |            |     1692.8 |                 |                 |
| sched_hour                 |       17.7 |     2228   |                 |          0.0249 |
| sched_minute_of_day        |       15.7 |     1950.9 |          0.0172 |          0.1552 |
| tc_signal                  |       26.1 |     4911.9 |                 |                 |
| temp_c                     |       16.7 |     2647   |                 |          0.0362 |
| terminal                   |            |            |          0.0013 |                 |
| visib_sm                   |       19.3 |     2146.3 |                 |                 |
| wdir                       |            |            |          0.0021 |                 |
| wx_rain                    |      178.4 |    16237.5 |                 |                 |
| wx_ts                      |       50.6 |     5337   |                 |                 |

## Ablation — test AUC when a feature group is removed

| variant                  |   n_features |    auc |   logloss |   brier |     mae |
|:-------------------------|-------------:|-------:|----------:|--------:|--------:|
| full                     |           38 | 0.7134 |    0.3912 |  0.1197 |  11.33  |
| no_weather               |           24 | 0.7029 |    0.406  |  0.1256 | nan     |
| no_rolling               |           32 | 0.6998 |    0.3959 |  0.1209 | nan     |
| no_inbound               |           33 | 0.7005 |    0.3951 |  0.1205 |  11.366 |
| no_weather_no_rolling    |           18 | 0.6969 |    0.4475 |  0.1402 | nan     |
| calendar+congestion only |            9 | 0.5833 |    0.4818 |  0.153  | nan     |

`mae` is fitted only for `full` and `no_inbound` (the two variants the inbound decision compares). **Leak rule for the inbound block:** link *existence* is rebuilt from scheduled departure times (`rotations --events sched`, so the pairing cannot depend on the label), and the link's *values* are gated at scheduled − 2 h — an inbound that went on blocks after that cutoff counts as unknown, exactly as it would at scoring time. **The ship decision is made at masked coverage:** every row here was trained and tested with `--inbound-dropout 0.25` applied to all three splits (inbound_known rate 0.2703 on test vs 0.3619 in the parquet), i.e. at the coverage deployment actually has, not the coverage the backfill has. The rows above are scored at the train-time test mask (seed 0 + 2); because one mask draw is itself a source of variance, the decision is taken on the mean over 5 independent test masks of the same two fitted models: ΔAUC 0.01525, ΔMAE -0.04188 min (full − no_inbound); 95 % CI on ΔAUC at test seed 0 [0.01036, 0.02067]. Gated in `scripts/inbound_gate.py`.

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
