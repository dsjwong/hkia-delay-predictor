"""Baselines + gradient-boosting models with a time-based split. Writes models/ and reports/M2-results.md.

Usage: python -m hkia.train [--features data/features.parquet]

Split: sorted unique dates -> first 70 % train, next 15 % validation (early stopping), last 15 % test.
Baseline A: train global delay rate / mean delay.  Baseline B: airline x scheduled-hour mean from train only
(fallback airline mean, then global).  Model: XGBoost hist with native categoricals.
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
from .features import CATEGORICAL, FEATURES, NUMERIC

log = logging.getLogger("hkia.train")
INTERP_MARK = "<!-- interpretation: hand-written, preserved by train.py -->"
WEATHER = ["temp_c", "dewp_c", "wdir", "wspd_kt", "wgst_kt", "visib_sm", "ceiling_ft", "flt_cat",
           "wx_rain", "wx_ts", "wx_fog", "metar_age_min", "tc_signal", "msn_signal"]
ROLLING = [f for f in NUMERIC if f.endswith("_mean_delay") or f.endswith("_n") and "day" in f]
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


def ablation(splits, cats, ytr, yva, yte) -> pd.DataFrame:
    """Test AUC when whole feature groups are removed — the honest 'what adds what' check."""
    variants = {"full": FEATURES,
                "no_weather": [f for f in FEATURES if f not in WEATHER],
                "no_rolling": [f for f in FEATURES if f not in ROLLING],
                "no_weather_no_rolling": [f for f in FEATURES if f not in WEATHER + ROLLING],
                "calendar+congestion only": [f for f in FEATURES if f in NUMERIC and f not in WEATHER + ROLLING]}
    rows = []
    for name, feats in variants.items():
        c = {k: v for k, v in cats.items() if k in feats}
        Xtr, _ = to_matrix(splits["train"], c, feats)
        Xva, _ = to_matrix(splits["val"], c, feats)
        Xte, _ = to_matrix(splits["test"], c, feats)
        m = fit_xgb(xgb.XGBClassifier(**CLF_PARAMS), Xtr, ytr, Xva, yva)
        rows.append({"variant": name, "n_features": len(feats), **clf_metrics(yte, m.predict_proba(Xte)[:, 1])})
    return pd.DataFrame(rows).set_index("variant")


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
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    models_dir, reports_dir = Path(a.models), Path(a.reports)
    models_dir.mkdir(exist_ok=True), reports_dir.mkdir(exist_ok=True)

    feat = pd.read_parquet(a.features)
    df = feat[(feat["cancelled"] == 0) & feat["delay_min"].notna()].reset_index(drop=True)
    splits = time_split(df)
    split_info = {k: {"date_min": v["date"].min(), "date_max": v["date"].max(), "n_rows": len(v),
                      "n_dates": v["date"].nunique(), "delayed15_rate": round(float(v["delayed15"].mean()), 4)}
                  for k, v in splits.items()}
    log.info("split: %s", split_info)

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
    abl = ablation(splits, cats, y["train"], y["val"], y["test"])
    log.info("ablation:\n%s", abl)

    # persist
    joblib.dump({"model": clf, "cats": cats, "features": FEATURES}, models_dir / "xgb_delayed15.joblib")
    joblib.dump({"model": reg, "cats": cats, "features": FEATURES}, models_dir / "xgb_delay_min.joblib")
    joblib.dump({"clf": tabB_c, "reg": tabB_r}, models_dir / "baseline_b_airline_hour.joblib")
    manifest = {"created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "git_sha": git_sha(),
                "xgboost": xgb.__version__, "features": FEATURES, "categorical": CATEGORICAL, "split": split_info,
                "clf_best_iteration": int(clf.best_iteration), "reg_best_iteration": int(reg.best_iteration),
                "params": {k: v for k, v in CLF_PARAMS.items()},
                "metrics": {f"{m}/{s}": v for (m, s), v in results.items()},
                "ablation_test": abl.to_dict(orient="index"), "features_parquet_rows": int(len(feat))}
    (models_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, default=str))
    write_feature_importance(clf, reg, models_dir / "feature_importance.json")
    write_report(reports_dir / "M2-results.md", feat, df, split_info, results, calib, gain_c, gain_r, perm_c, perm_r, abl, manifest)
    return 0


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown()


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
    ]
    # keep the hand-written interpretation (everything from the marker onwards) across re-runs
    old = path.read_text() if path.exists() else ""
    tail = old[old.index(INTERP_MARK):] if INTERP_MARK in old else INTERP_MARK + "\n## Interpretation\n\n(to be written)\n"
    path.write_text("\n".join(lines) + "\n" + tail)
    log.info("wrote %s", path)


if __name__ == "__main__":
    sys.exit(main())
