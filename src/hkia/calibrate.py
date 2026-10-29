"""Post-hoc probability calibration for the P(delay > 15 min) classifier.

The raw XGBoost output is over-confident at the top of the range (live eval: 8 calls at P >= 0.7, 4 late). `hkia.train`
fits one of three maps on a date-ordered calibration fold that sits between train and test, and saves it next to the model as
`models/calibrator_delayed15.json`; `hkia.predict` applies it to every probability it serves. SHAP attributions stay on the
raw model (they are log-odds of the raw booster).

  identity  no change (chosen when neither map beats the raw scores out of fold)
  platt     p' = sigmoid(a * logit(p) + b)
  isotonic  monotone step function, stored as its threshold table and evaluated with np.interp

The map is chosen by **blocked K-fold out-of-fold log loss on the calibration fold** (contiguous date blocks), not by
in-sample log loss -- isotonic always wins in-sample. Isotonic is only a candidate with at least `MIN_ISOTONIC` points.
The stored form is plain JSON (no pickled class), so it survives sklearn / xgboost upgrades and diffs in git.
Needs numpy only to apply; scikit-learn only to fit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

CALIBRATOR_FILE = "calibrator_delayed15.json"
MIN_ISOTONIC = 1000
P_LO, P_HI = 0.005, 0.995      # a served probability is never 0 or 1
EPS = 1e-6


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def logloss(y, p) -> float:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    y = np.asarray(y, dtype=float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


@dataclass
class Calibrator:
    method: str = "identity"                     # identity | platt | isotonic
    params: dict = field(default_factory=dict)

    def predict(self, p) -> np.ndarray:
        p = np.asarray(p, dtype=float)
        if self.method == "identity":
            return p
        if self.method == "platt":
            q = _sigmoid(self.params["a"] * _logit(p) + self.params["b"])
        elif self.method == "isotonic":
            q = np.interp(p, self.params["x"], self.params["y"])
        else:
            raise ValueError(f"unknown calibration method {self.method!r}")
        return np.clip(q, P_LO, P_HI)

    def to_dict(self) -> dict:
        return {"method": self.method, "params": {k: (v if np.isscalar(v) else list(map(float, v))) for k, v in self.params.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> "Calibrator":
        return cls(d["method"], dict(d.get("params", {})))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict()))


def load_calibrator(models_dir: Path) -> Calibrator:
    """The calibrator saved beside a model, or identity when there is none (a model shipped before calibration existed)."""
    f = Path(models_dir) / CALIBRATOR_FILE
    return Calibrator.from_dict(json.loads(f.read_text())) if f.exists() else Calibrator()


def _fit(method: str, p, y) -> Calibrator:
    if method == "identity":
        return Calibrator()
    if method == "platt":
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(C=1e6, max_iter=1000).fit(_logit(p).reshape(-1, 1), y)
        return Calibrator("platt", {"a": float(lr.coef_[0, 0]), "b": float(lr.intercept_[0])})
    if method == "isotonic":
        from sklearn.isotonic import IsotonicRegression
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, y)
        return Calibrator("isotonic", {"x": iso.X_thresholds_.tolist(), "y": iso.y_thresholds_.tolist()})
    raise ValueError(method)


def fit_calibrator(p, y, blocks=None, n_folds: int = 4, min_isotonic: int = MIN_ISOTONIC) -> tuple[Calibrator, dict]:
    """Pick and fit the calibrator on (p, y). `blocks` = a sortable label per row (the date): folds are contiguous runs of
    distinct labels, so a day never straddles a train and a held-out part. Returns (calibrator, report)."""
    p, y = np.asarray(p, dtype=float), np.asarray(y, dtype=int)
    n = len(p)
    blocks = np.arange(n) if blocks is None else np.asarray(blocks)
    uniq = np.array(sorted(set(blocks.tolist())))
    folds = np.array_split(uniq, min(n_folds, len(uniq)))
    methods = ["identity", "platt"] + (["isotonic"] if n >= min_isotonic else [])
    report = {"n": int(n), "n_folds": len(folds), "candidates": {}}
    for m in methods:
        oof = np.empty(n)
        for f in folds:
            te = np.isin(blocks, f)
            if te.all() or not te.any() or len(set(y[~te].tolist())) < 2:
                oof[te] = p[te]
                continue
            oof[te] = _fit(m, p[~te], y[~te]).predict(p[te])
        report["candidates"][m] = {"oof_logloss": round(logloss(y, oof), 5)}
    best = min(report["candidates"], key=lambda m: report["candidates"][m]["oof_logloss"])
    report["chosen"] = best
    return _fit(best, p, y), report


def reliability_table(y, p, bins: int = 10) -> list[dict]:
    """Equal-width bins on [0, 1]: n, mean predicted, observed rate (empty bins omitted)."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    b = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    out = []
    for i in range(bins):
        s = b == i
        if s.any():
            out.append({"bin": f"{edges[i]:.1f}-{edges[i + 1]:.1f}", "n": int(s.sum()),
                        "pred_mean": round(float(p[s].mean()), 3), "obs_rate": round(float(y[s].mean()), 3)})
    return out
