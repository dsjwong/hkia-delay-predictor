# Model comparison, 2026-11: Oct 29 refit vs Nov 1 weekly refit, same flights

**Verdict: no rollback.** The live "By model version" drop (AUC 0.718 for `42715b6`, n = 1244, scored Oct 29-Nov 1, vs 0.621 for `f6ae66c`, n = 1228, scored Nov 1-4) is a window effect. Re-scored on the **same flights** both models land within a few thousandths of AUC of each other, and the Nov 1 model is the slightly better one on log loss, Brier and MAE (CIs exclude 0 for those), never worse.

Models: Oct set = `models/` at 9bbe0bd (git `42715b6`, 2026-10-29); Nov set = `models/` at d34b315 (git `f6ae66c`, 2026-11-01). Files are the exact committed ones, extracted from git. Harness: `src/hkia/asof.py` (new). Flights: departed, not cancelled, with a label; none of them was in either model's train/val/cal fold (Oct set trained to 2026-10-04, Nov set to 2026-10-06).

## Method

For a scoring time T the harness blanks every actual departure after T, drops METARs after T (flights scheduled after T get the latest observation <= T, as `hkia.predict`), drops cyclone signals not started by T, gates the inbound block with `now=T`, then runs the serve path (features -> raw booster -> calibrator; regressor for minutes). Inbound links were rebuilt from scheduled times on a scratch copy of the pulled db (`rotations --all --events sched`; the live db was never pushed). Labels are joined after scoring.

- **(a) Day-ahead**: every day scored at noon HKT the day before (inbound unknown, same-day rolling stats empty). Same scheme as the M2-results day-ahead note.
- **(b) Live last-score**: every flight scored at T = the `scored_at` of its last stored live prediction before departure (the live-eval population, n = 2890 for Oct 29-Nov 4, 42 distinct scoring runs), so horizons and inbound coverage are the ones serving actually had (inbound_known 15.7 %).

Harness checks: re-scoring reproduces the stored live `p_delay15` within 0.01 for 97.7 % of the 1244 flights live-scored by `42715b6` and 91.9 % of the 1587 by `f6ae66c` (mean |diff| 0.002 / 0.003). Day-ahead on 2026-10-22..28 gives n = 2954, late rate 0.184, Oct-model mean P 0.198, log loss 0.454, AUC 0.655, MAE 14.3 min against the M2 note's n = 2958, 0.185, 0.203, 0.4518, 0.670, 16.2: same flights and level, but AUC and MAE are not identical (the note's script is not in the repo).

## Same-flight results (Nov minus Oct; paired bootstrap, 2000 resamples over flights, 95 % CI)

| scheme / window | n | AUC Oct / Nov / airline x hour | ΔAUC | ΔMAE (min) | Δlog loss | ΔBrier |
|---|---:|---|---|---|---|---|
| day-ahead, Nov 1-4 | 1619 | 0.634 / 0.648 / 0.621 | +0.014 [+0.002, +0.027] | -0.09 [-0.13, -0.05] | -0.0085 [-0.0116, -0.0054] | -0.0025 [-0.0035, -0.0016] |
| day-ahead, Oct 29-Nov 4 | 2890 | 0.662 / 0.666 / 0.647 | +0.004 [-0.005, +0.013] | -0.11 [-0.14, -0.07] | -0.0076 [-0.0101, -0.0050] | -0.0023 [-0.0031, -0.0015] |
| day-ahead, Oct 7-Nov 4 | 12400 | 0.674 / 0.677 / 0.657 | +0.003 [-0.001, +0.007] | -0.04 [-0.06, -0.03] | -0.0055 [-0.0067, -0.0043] | -0.0017 [-0.0021, -0.0013] |
| live last-score, Nov 1-4 | 1619 | 0.635 / 0.646 / 0.621 | +0.011 [+0.002, +0.021] | -0.09 [-0.13, -0.05] | -0.0048 [-0.0072, -0.0022] | -0.0014 [-0.0022, -0.0007] |
| live last-score, Oct 29-Nov 1 | 1689 | 0.692 / 0.703 / 0.671 | +0.010 [+0.001, +0.020] | -0.20 [-0.25, -0.15] | -0.0034 [-0.0060, -0.0009] | -0.0012 [-0.0021, -0.0004] |
| live last-score, Oct 29-Nov 4 | 2890 | 0.661 / 0.671 / 0.647 | +0.010 [+0.003, +0.017] | -0.16 [-0.20, -0.12] | -0.0037 [-0.0056, -0.0016] | -0.0012 [-0.0018, -0.0006] |

Log loss / MAE of each model on live last-score Oct 29-Nov 4: Oct 0.3757 / 10.49, Nov 0.3721 / 10.33, airline x hour 0.4407 / 15.98. Sensitivity: resampling whole dates instead of flights (4-29 clusters) keeps every sign; Δlog loss and Δbrier still exclude 0 in favour of the Nov model in all six rows, ΔMAE in 4 of 6, while ΔAUC's CI straddles 0 in 3 of 6 (day-ahead Oct 29-Nov 4 and Oct 7-Nov 4, live Nov 1-4). Model minus airline x hour (Nov model, live Oct 29-Nov 4): ΔAUC +0.025 [-0.001, +0.049], Δlog loss -0.069 [-0.079, -0.058], ΔMAE -5.6 min [-6.0, -5.3].

So the live table's gap is the calendar: on the same four days (Nov 1-4) *both* models score ~0.63-0.65 AUC, on Oct 29-Nov 1 both ~0.69-0.70. The airline x hour baseline moves the same way (0.671 -> 0.621). Daily AUC at n ~ 400 has a standard error of about 0.03, so single-version, single-window numbers in the live table are not comparable across rows.

## Was the Nov 1 refit sound?

- **Recipe**: identical feature list (`features` equal in both MANIFESTs), categories equal except two dest levels (DEL, TFU swap in/out of the top-30), CLF params unchanged, inbound dropout 0.25 / mask seed 0, links `sched` for both.
- **Windows**: train to 2026-09-11 vs 09-09, val 09-12..23 vs 09-10..21, calibration fold 09-24..10-06 (5770 rows) vs 09-22..10-04 (5705), test 10-07..11-01 vs 10-05..10-29. A weekly refit moves every boundary by only 2-3 days, so successive models are close to re-fits of each other (Platt a = 0.887 vs 0.895, b = -0.260 vs -0.261; best iteration 452/466 vs 400/450). That is why the difference between them is small.
- **Calibrator**: Platt in both; no flip. Out-of-fold log loss of the three candidates in the Nov fold: identity 0.4452, Platt 0.4448, isotonic 0.4483 (Oct fold: 0.4485 / 0.4482 / 0.4525). Platt wins by 0.0004 in both, a coin flip that stays harmless because the maps are nearly identical.
- **Gate window**: 2026-10-07..11-01 (n = 11071) is later than anything either model was fitted on, the same flights for both, with the exact serve-time inbound mask; ΔAUC +0.0044 (lower bound +0.0012), Δlog loss -0.0017. It did not flatter the candidate: the same-flight day-ahead ΔAUC over Oct 7-Nov 4 is +0.003. Re-running the gate offline on the same pair today gives the same picture (ΔAUC +0.0038, SHIP).
- **Real weakness of the gate**: its AUC level (0.713) is not what serving achieves (0.65-0.67 live, 0.64-0.68 day-ahead) because its test rows carry same-day rolling statistics and a 27 % inbound rate, which day-ahead rows do not (inbound live coverage here: 15.7 %; 0 % day-ahead). It also saw nothing of the actual serving regime, so a candidate that does worse day-ahead could still pass. Hence R6.

## Decision and gate change

No rollback; `models/` left at the Nov 1 set. `scripts/retrain_gate.py` gained **R6**: both models are scored through `hkia.asof` day-ahead on the last 7 complete, held-out days (past both calibration folds), paired bootstrap over flights, and the ship is blocked only if ΔAUC's 95 % CI is entirely below 0 or Δlog loss's is entirely above 0. Fewer than 1000 flights, or no db, means no verdict (the gate stays passable). `retrain.yml` passes `--asof-days 7`. Offline scenario runs: Nov set as candidate vs Oct set as shipped -> R6 pass (ΔAUC +0.0074 [-0.0012, +0.0159], Δlog loss -0.0088 [-0.0112, -0.0062]), SHIP; Oct set as candidate vs Nov set as shipped -> R6 FAIL (Δlog loss +0.0088 [+0.0062, +0.0112]), HOLD.
