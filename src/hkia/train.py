"""Baselines + gradient-boosting models with a time-based split. Writes models/ and reports/M2-results.md.

Usage: python -m hkia.train [--features data/features.parquet]

Split: sorted unique dates -> first 70 % train, next 15 % validation (early stopping), last 15 % test.
Baseline A: train global delay rate / mean delay.  Baseline B: airline x scheduled-hour mean from train only
(fallback airline mean, then global).  Model: XGBoost hist with native categoricals.

Inbound block (`--inbound-dropout`): the parquet knows the inbound link of ~1/3 of departures, deployment knows fewer
(the stand is published only ~2-3 h ahead, and `hkia.predict` gates the block at scheduled - 2 h). Training on the
richer distribution would ship a model that leans on a feature it usually will not have, so a random `--inbound-dropout`
share of the linked rows is pushed back to the exact serve-time encoding of a missing link -- in every split, val
included, so early stopping sees the deployment distribution too. The parquet is never modified. Whether the block is
worth shipping at all is decided by `inbound_delta` (paired bootstrap, full vs no_inbound) and `scripts/inbound_gate.py`.
"""
import argparse
import datetime as dt
import json
import logging
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.inspection import permutation_importance
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, roc_auc_score

from .baseline import baseline_b_predict, baseline_b_table
from .db import ROOT
from .evaluate import _auc_np       # acyclic: hkia.evaluate imports only hkia.db + hkia.features
from .features import CATEGORICAL, FEATURES, INBOUND, NUMERIC

log = logging.getLogger("hkia.train")
INTERP_MARK = "<!-- interpretation: hand-written, preserved by train.py -->"
WEATHER = ["temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "flt_cat",
           "wx_rain", "wx_ts", "wx_fog", "metar_age_min", "tc_signal", "msn_signal"]
ROLLING = [f for f in NUMERIC if f.endswith("_mean_delay") or f.endswith("_n") and "day" in f]
INBOUND_VALUE = [f for f in INBOUND if f != "inbound_known"]   # NaN'd together; inbound_known stays a real 0/1
PAIRED = ("full", "no_inbound")     # the two variants that also get a regressor + per-row test predictions
SPLIT_SEED = {"train": 0, "val": 1, "test": 2}   # distinct mask draws per split, derived from --mask-seed
N_BOOT = 2000
N_TEST_SEEDS = 5
SENSITIVITY_STEP = 0.10
CLF_PARAMS = dict(n_estimators=2000, learning_rate=0.03, max_depth=6, min_child_weight=20, subsample=0.8,
                  colsample_bytree=0.8, reg_lambda=2.0, tree_method="hist", enable_categorical=True,
                  max_cat_to_onehot=1, early_stopping_rounds=100, eval_metric="logloss", random_state=42, n_jobs=4)
REG_PARAMS = {**CLF_PARAMS, "objective": "reg:absoluteerror", "eval_metric": "mae"}


# ---------- data ----------

def time_split(df: pd.DataFrame, train_frac=0.70, val_frac=0.15) -> dict[str, pd.DataFrame]:
    dates = np.array(sorted(df["date"].unique()))
    n = len(dates)
    i_tr, i_va = int(round(n * train_frac)), int(round(n * (train_frac + val_frac)))
    parts = {"train": dates[:i_tr], "val": dates[i_tr:i_va], "test": dates[i_va:]}
    return {k: df[df["date"].isin(v)].copy() for k, v in parts.items()}


def mask_inbound(df: pd.DataFrame, rate: float, seed: int = 0) -> pd.DataFrame:
    """Drop the inbound link of an i.i.d. `rate` share of the rows that have one, in the EXACT encoding a serve-time
    miss produces: `inbound_known` -> 0 and the four value features -> NaN.

    Training-time only (the parquet stays as built) and deterministic given `seed`. Rows without a link, every other
    column and both labels are untouched, so this changes the coverage of the inbound block and nothing else.
    """
    out = df.copy()
    if not rate:
        return out
    draw = pd.Series(np.random.default_rng(seed).random(len(out)), index=out.index)
    sel = (out["inbound_known"] == 1) & (draw < rate)
    out.loc[sel, "inbound_known"] = 0
    out.loc[sel, INBOUND_VALUE] = np.nan
    return out


def to_matrix(df: pd.DataFrame, cats: dict[str, pd.CategoricalDtype] | None = None, features=FEATURES):
    X = df[features].copy()
    if cats is None:
        cats = {c: pd.CategoricalDtype(sorted(X[c].dropna().unique())) for c in CATEGORICAL if c in features}
    for c, t in cats.items():
        X[c] = X[c].where(X[c].isin(t.categories)).astype(t)  # unseen categories -> NaN (XGBoost handles missing)
    return X, cats


# ---------- baselines ----------
# baseline_b_table / baseline_b_predict live in hkia.baseline (pandas + numpy only) so the dashboards can score the same
# lookup table without xgboost / scikit-learn installed; re-exported here because this is where it is fitted and saved.


# ---------- metrics ----------

def clf_metrics(y, p) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"auc": round(roc_auc_score(y, p), 4), "logloss": round(log_loss(y, p), 4), "brier": round(brier_score_loss(y, p), 4)}


def calibration_table(y, p, bins=10) -> pd.DataFrame:
    edges = np.linspace(0, 1, bins + 1)
    b = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    t = pd.DataFrame({"bin": b, "y": y, "p": p}).groupby("bin").agg(n=("y", "size"), pred_mean=("p", "mean"), obs_rate=("y", "mean"))
    t.index = [f"{edges[i]:.1f}-{edges[i+1]:.1f}" for i in t.index]
    return t.round(3)


# ---------- training ----------

def fit_xgb(model, Xtr, ytr, Xva, yva):
    model.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return model


def gain_importance(model, top=15) -> pd.Series:
    imp = model.get_booster().get_score(importance_type="gain")
    return pd.Series(imp).sort_values(ascending=False).head(top).round(1)


def write_feature_importance(clf, reg, path: Path, top: int = 15) -> None:
    """Precomputed gain importance for the dashboard (so Streamlit Cloud never needs xgboost/joblib to display it)."""
    out = {"importance_type": "gain", "top": top,
           "clf_delayed15": gain_importance(clf, top).to_dict(), "reg_delay_min": gain_importance(reg, top).to_dict()}
    Path(path).write_text(json.dumps(out, indent=2))


def perm_importance(model, X, y, scoring, top=15) -> pd.Series:
    r = permutation_importance(model, X, y, scoring=scoring, n_repeats=3, random_state=0, n_jobs=1)
    return pd.Series(r.importances_mean, index=X.columns).sort_values(ascending=False).head(top).round(4)


def fit_pair(splits, cats, feats, y, r) -> dict:
    """Classifier + MAE regressor of one feature set, fitted on the (already masked) train/val splits."""
    c = {k: v for k, v in cats.items() if k in feats}
    Xtr, _ = to_matrix(splits["train"], c, feats)
    Xva, _ = to_matrix(splits["val"], c, feats)
    return {"clf": fit_xgb(xgb.XGBClassifier(**CLF_PARAMS), Xtr, y["train"], Xva, y["val"]),
            "reg": fit_xgb(xgb.XGBRegressor(**REG_PARAMS), Xtr, r["train"], Xva, r["val"]),
            "features": feats, "cats": c}


def predict_pair(pair: dict, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    X, _ = to_matrix(df, pair["cats"], pair["features"])
    return pair["clf"].predict_proba(X)[:, 1], pair["reg"].predict(X)


def ablation(splits, cats, y, r) -> tuple[pd.DataFrame, dict]:
    """Test AUC when whole feature groups are removed — the honest 'what adds what' check.

    Returns the table plus the fitted `full` / `no_inbound` pair (classifier + regressor), which `inbound_delta` then
    re-scores on differently masked copies of the test split without refitting anything.
    """
    variants = {"full": FEATURES,
                "no_weather": [f for f in FEATURES if f not in WEATHER],
                "no_rolling": [f for f in FEATURES if f not in ROLLING],
                "no_inbound": [f for f in FEATURES if f not in INBOUND],
                "no_weather_no_rolling": [f for f in FEATURES if f not in WEATHER + ROLLING],
                "calendar+congestion only": [f for f in FEATURES if f in NUMERIC
                                             and f not in WEATHER + ROLLING + INBOUND]}
    rows, fitted = [], {}
    for name, feats in variants.items():
        if name in PAIRED:
            pair = fit_pair(splits, cats, feats, y, r)
            p, yhat = predict_pair(pair, splits["test"])
            fitted[name] = pair
            rows.append({"variant": name, "n_features": len(feats), **clf_metrics(y["test"], p),
                         "mae": round(mean_absolute_error(r["test"], yhat), 3)})
            continue
        c = {k: v for k, v in cats.items() if k in feats}
        Xtr, _ = to_matrix(splits["train"], c, feats)
        Xva, _ = to_matrix(splits["val"], c, feats)
        Xte, _ = to_matrix(splits["test"], c, feats)
        m = fit_xgb(xgb.XGBClassifier(**CLF_PARAMS), Xtr, y["train"], Xva, y["val"])
        rows.append({"variant": name, "n_features": len(feats), **clf_metrics(y["test"], m.predict_proba(Xte)[:, 1])})
    return pd.DataFrame(rows).set_index("variant"), fitted


def _paired_bootstrap(y, r, full, no_inb, n_boot=N_BOOT, seed=0) -> dict:
    """95 % CI on (full - no_inbound) ΔAUC and ΔMAE, resampling *flights* and scoring both models on the same draw.

    Paired, so the CI is on the difference rather than on two independently noisy numbers. ΔAUC > 0 and ΔMAE < 0 are the
    directions that favour keeping the inbound block; a CI straddling 0 means this much test data cannot tell.
    """
    n = len(y)
    ae_f, ae_n = np.abs(r - full[1]), np.abs(r - no_inb[1])
    rng = np.random.default_rng(seed)
    d_auc, d_mae = np.empty(n_boot), np.empty(n_boot)
    for i in range(n_boot):
        s = rng.integers(0, n, n)
        ys = y[s]
        d_auc[i] = _auc_np(ys, full[0][s]) - _auc_np(ys, no_inb[0][s])
        d_mae[i] = ae_f[s].mean() - ae_n[s].mean()
    out = {"n_boot": n_boot}
    for k, v in (("d_auc", d_auc), ("d_mae", d_mae)):
        v = v[np.isfinite(v)]
        out[k] = [round(float(x), 5) for x in np.percentile(v, [2.5, 97.5])] if v.size else None
    return out


def inbound_delta(fitted: dict, test: pd.DataFrame, dropout: float, n_seeds: int = N_TEST_SEEDS,
                  n_boot: int = N_BOOT) -> dict:
    """full vs no_inbound on test, under `n_seeds` independent test-mask seeds — **re-prediction only, no refitting**.

    Both models are fitted once (at the train/val mask seed); only the test split is re-masked. That isolates the
    variance the mask draw itself contributes, which on a single 15 % test split is not negligible and would otherwise
    be read as signal. The bootstrap CI is computed at test seed 0.
    """
    per_seed, ci = [], None
    for s in range(n_seeds):
        te = mask_inbound(test, dropout, s)
        y = te["delayed15"].astype(int).to_numpy()
        r = te["delay_min"].to_numpy(dtype=float)
        pr = {name: predict_pair(pair, te) for name, pair in fitted.items()}
        row = {"test_mask_seed": s, "inbound_known_rate": round(float(te["inbound_known"].mean()), 4),
               "auc_full": round(float(_auc_np(y, pr["full"][0])), 5),
               "auc_no_inbound": round(float(_auc_np(y, pr["no_inbound"][0])), 5),
               "mae_full": round(float(mean_absolute_error(r, pr["full"][1])), 4),
               "mae_no_inbound": round(float(mean_absolute_error(r, pr["no_inbound"][1])), 4)}
        row["d_auc"] = round(row["auc_full"] - row["auc_no_inbound"], 5)
        row["d_mae"] = round(row["mae_full"] - row["mae_no_inbound"], 4)
        per_seed.append(row)
        if s == 0:
            ci = _paired_bootstrap(y, r, pr["full"], pr["no_inbound"], n_boot)
    mean = {k: round(float(np.mean([p[k] for p in per_seed])), 5)
            for k in ("auc_full", "auc_no_inbound", "d_auc", "mae_full", "mae_no_inbound", "d_mae")}
    return {"n_test": int(len(test)), "n_test_seeds": n_seeds, "inbound_dropout": dropout,
            "per_seed": per_seed, "mean": mean, "ci_test_seed_0": ci}


def sensitivity(raw_splits, cats, dropout: float, mask_seed: int, step: float = SENSITIVITY_STEP) -> dict:
    """Report only, never gated: refit full / no_inbound at `dropout + step` to show whether the verdict hinges on the
    assumed serve-time dropout rate. Everything (fit and test) uses the higher rate."""
    d2 = round(min(dropout + step, 1.0), 4)
    sp = {k: mask_inbound(v, d2, mask_seed + SPLIT_SEED[k]) for k, v in raw_splits.items()}
    yy = {k: sp[k]["delayed15"].astype(int).to_numpy() for k in sp}
    rr = {k: sp[k]["delay_min"].to_numpy(dtype=float) for k in sp}
    out = {"inbound_dropout": d2, "inbound_known_rate_test": round(float(sp["test"]["inbound_known"].mean()), 4)}
    for name, feats in (("full", FEATURES), ("no_inbound", [f for f in FEATURES if f not in INBOUND])):
        p, yhat = predict_pair(fit_pair(sp, cats, feats, yy, rr), sp["test"])
        out[f"auc_{name}"] = round(float(_auc_np(yy["test"], p)), 5)
        out[f"mae_{name}"] = round(float(mean_absolute_error(rr["test"], yhat)), 4)
    out["d_auc"] = round(out["auc_full"] - out["auc_no_inbound"], 5)
    out["d_mae"] = round(out["mae_full"] - out["mae_no_inbound"], 4)
    return out


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", default=str(ROOT / "data" / "features.parquet"))
    ap.add_argument("--models", default=str(ROOT / "models"))
    ap.add_argument("--reports", default=str(ROOT / "reports"))
    ap.add_argument("--inbound-dropout", type=float, default=0.0,
                    help="share of linked rows whose inbound block is masked back to 'no link' in every split, to match "
                         "serve-time coverage (see the module docstring); 0 = train on the parquet as built")
    ap.add_argument("--mask-seed", type=int, default=0, help="base seed of the inbound dropout draw")
    ap.add_argument("--serve-rate-json", help="optional JSON recorded verbatim in MANIFEST.inbound.serve_rate "
                                              "(the measured serve-time coverage the dropout rate was chosen from)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    models_dir, reports_dir = Path(a.models), Path(a.reports)
    models_dir.mkdir(exist_ok=True), reports_dir.mkdir(exist_ok=True)

    feat = pd.read_parquet(a.features)
    df = feat[(feat["cancelled"] == 0) & feat["delay_min"].notna()].reset_index(drop=True)
    raw_splits = time_split(df)
    # masking is training-time only and happens immediately after the split, so every downstream fit, early stop,
    # metric and ablation sees one consistent, deployment-shaped inbound coverage
    splits = {k: mask_inbound(v, a.inbound_dropout, a.mask_seed + SPLIT_SEED[k]) for k, v in raw_splits.items()}
    split_info = {k: {"date_min": v["date"].min(), "date_max": v["date"].max(), "n_rows": len(v),
                      "n_dates": v["date"].nunique(), "delayed15_rate": round(float(v["delayed15"].mean()), 4),
                      "inbound_known_rate": round(float(v["inbound_known"].mean()), 4)}
                  for k, v in splits.items()}
    log.info("split: %s (inbound dropout %.2f, mask seed %d)", split_info, a.inbound_dropout, a.mask_seed)

    Xtr, cats = to_matrix(splits["train"])
    Xva, _ = to_matrix(splits["val"], cats)
    Xte, _ = to_matrix(splits["test"], cats)
    y = {k: splits[k]["delayed15"].astype(int).to_numpy() for k in splits}
    r = {k: splits[k]["delay_min"].to_numpy() for k in splits}

    # baselines
    tabB_c = baseline_b_table(splits["train"], "delayed15")
    tabB_r = baseline_b_table(splits["train"], "delay_min")
    results = {}
    for k in ("val", "test"):
        n = len(splits[k])
        results[("A_global", k)] = {**clf_metrics(y[k], np.full(n, tabB_c[2])), "mae": round(mean_absolute_error(r[k], np.full(n, tabB_r[2])), 3)}
        results[("B_airline_hour", k)] = {**clf_metrics(y[k], baseline_b_predict(splits[k], tabB_c)),
                                          "mae": round(mean_absolute_error(r[k], baseline_b_predict(splits[k], tabB_r)), 3)}
    results[("median_train", "test")] = {"mae": round(mean_absolute_error(r["test"], np.full(len(r["test"]), np.median(r["train"]))), 3)}

    # models
    clf = fit_xgb(xgb.XGBClassifier(**CLF_PARAMS), Xtr, y["train"], Xva, y["val"])
    reg = fit_xgb(xgb.XGBRegressor(**REG_PARAMS), Xtr, r["train"], Xva, r["val"])
    p, yhat = {}, {}
    for k, X in (("val", Xva), ("test", Xte)):
        p[k], yhat[k] = clf.predict_proba(X)[:, 1], reg.predict(X)
        results[("XGB", k)] = {**clf_metrics(y[k], p[k]), "mae": round(mean_absolute_error(r[k], yhat[k]), 3)}
    log.info("results: %s", results)
    calib = calibration_table(y["test"], p["test"])
    gain_c, gain_r = gain_importance(clf), gain_importance(reg)
    perm_c = perm_importance(clf, Xte, y["test"], "roc_auc")
    perm_r = perm_importance(reg, Xte, r["test"], "neg_mean_absolute_error")
    abl, fitted = ablation(splits, cats, y, r)
    log.info("ablation:\n%s", abl)
    gate = inbound_delta(fitted, raw_splits["test"], a.inbound_dropout)
    gate["sensitivity"] = sensitivity(raw_splits, cats, a.inbound_dropout, a.mask_seed)
    log.info("inbound gate: mean dAUC %+.4f, mean dMAE %+.3f, CI(seed 0) dAUC %s dMAE %s; sensitivity @%.2f dAUC %+.4f",
             gate["mean"]["d_auc"], gate["mean"]["d_mae"], gate["ci_test_seed_0"]["d_auc"],
             gate["ci_test_seed_0"]["d_mae"], gate["sensitivity"]["inbound_dropout"], gate["sensitivity"]["d_auc"])

    # persist
    joblib.dump({"model": clf, "cats": cats, "features": FEATURES}, models_dir / "xgb_delayed15.joblib")
    joblib.dump({"model": reg, "cats": cats, "features": FEATURES}, models_dir / "xgb_delay_min.joblib")
    joblib.dump({"clf": tabB_c, "reg": tabB_r}, models_dir / "baseline_b_airline_hour.joblib")
    fmeta_path = Path(a.features).with_suffix(".meta.json")
    fmeta = json.loads(fmeta_path.read_text()) if fmeta_path.exists() else {}
    inbound_info = {
        "known_rate": {k: split_info[k]["inbound_known_rate"] for k in split_info},
        "known_rate_unmasked": {k: round(float(v["inbound_known"].mean()), 4) for k, v in raw_splits.items()},
        "inbound_dropout": a.inbound_dropout, "mask_seed": a.mask_seed, "split_seed_offsets": SPLIT_SEED,
        "links_event_source": fmeta.get("links_event_source"), "features_meta": fmeta or None,
        "serve_rate": json.loads(Path(a.serve_rate_json).read_text()) if a.serve_rate_json else None}
    manifest = {"created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "git_sha": git_sha(),
                "xgboost": xgb.__version__, "features": FEATURES, "categorical": CATEGORICAL, "split": split_info,
                "clf_best_iteration": int(clf.best_iteration), "reg_best_iteration": int(reg.best_iteration),
                "params": {k: v for k, v in CLF_PARAMS.items()},
                "metrics": {f"{m}/{s}": v for (m, s), v in results.items()},
                # via to_json: the mae column is NaN for the variants that get no regressor, and a literal NaN in
                # MANIFEST.json would not survive a JSON.parse in the web app
                "ablation_test": json.loads(abl.to_json(orient="index")), "features_parquet_rows": int(len(feat)),
                "inbound": inbound_info, "inbound_gate": gate}
    (models_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, default=str))
    write_feature_importance(clf, reg, models_dir / "feature_importance.json")
    write_report(reports_dir / "M2-results.md", feat, df, split_info, results, calib, gain_c, gain_r, perm_c, perm_r, abl, manifest)
    return 0


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown()


def _ablation_note(manifest: dict) -> str:
    """The two sentences a reader needs to trust the `no_inbound` row: what the leak rule is, and at which inbound
    coverage the ship decision was taken."""
    inb, gate = manifest.get("inbound", {}), manifest.get("inbound_gate", {})
    m = gate.get("mean", {})
    ci = (gate.get("ci_test_seed_0") or {}).get("d_auc")
    return (
        f"`mae` is fitted only for `full` and `no_inbound` (the two variants the inbound decision compares). "
        f"**Leak rule for the inbound block:** link *existence* is rebuilt from scheduled departure times "
        f"(`rotations --events {inb.get('links_event_source', '?')}`, so the pairing cannot depend on the label), and the "
        f"link's *values* are gated at scheduled − 2 h — an inbound that went on blocks after that cutoff counts as "
        f"unknown, exactly as it would at scoring time. **The ship decision is made at masked coverage:** every row here "
        f"was trained and tested with `--inbound-dropout {inb.get('inbound_dropout')}` applied to all three splits "
        f"(inbound_known rate {inb.get('known_rate', {}).get('test')} on test vs "
        f"{inb.get('known_rate_unmasked', {}).get('test')} in the parquet), i.e. at the coverage deployment actually has, "
        f"not the coverage the backfill has. The rows above are scored at the train-time test mask (seed "
        f"{inb.get('mask_seed')} + {inb.get('split_seed_offsets', {}).get('test')}); because one mask draw is itself a "
        f"source of variance, the decision is taken on the mean over {gate.get('n_test_seeds')} independent test masks "
        f"of the same two fitted models: "
        f"ΔAUC {m.get('d_auc')}, ΔMAE {m.get('d_mae')} min (full − no_inbound); 95 % CI on ΔAUC at test seed 0 {ci}. "
        f"Gated in `scripts/inbound_gate.py`.")


def write_report(path, feat, df, split_info, results, calib, gain_c, gain_r, perm_c, perm_r, abl, manifest):
    res = pd.DataFrame(results).T
    res.index = [f"{m} ({s})" for m, s in res.index]
    imp = pd.DataFrame({"clf gain": gain_c, "reg gain": gain_r, "clf perm dAUC": perm_c, "reg perm dMAE": perm_r})
    lines = [
        "# M2 results — baselines vs XGBoost, time-based split", "",
        f"Generated {manifest['created_at']} from `data/features.parquet` ({len(feat)} rows incl. cancelled; "
        f"{len(df)} departed rows with labels used for modelling; git `{manifest['git_sha']}`).", "",
        "## Split (by date, no shuffling)", "", _md(pd.DataFrame(split_info).T), "",
        "## Metrics (classification: P(delay > 15 min); regression: delay minutes)", "",
        "Baseline A = train global rate / mean. Baseline B = airline x scheduled-hour mean from the train split only "
        "(fallback: airline mean, then global). `median_train` = predict the train median delay (MAE reference).", "",
        _md(res), "",
        "## Calibration on test (10 equal-width probability bins)", "", _md(calib), "",
        "## Feature importance (top 15 by gain) and permutation check on test (3 repeats)", "", _md(imp.fillna("")), "",
        "## Ablation — test AUC when a feature group is removed", "", _md(abl), "",
        _ablation_note(manifest), "",
    ]
    # keep the hand-written interpretation (everything from the marker onwards) across re-runs
    old = path.read_text() if path.exists() else ""
    tail = old[old.index(INTERP_MARK):] if INTERP_MARK in old else INTERP_MARK + "\n## Interpretation\n\n(to be written)\n"
    path.write_text("\n".join(lines) + "\n" + tail)
    log.info("wrote %s", path)


if __name__ == "__main__":
    sys.exit(main())
