"""Baseline B — the airline x scheduled-hour lookup table the model has to beat.

Kept in its own module because it is the only part of `hkia.train` the *dashboards* need: the live report card
(`hkia.evaluate`) scores the same baseline on matured predictions, and the Streamlit app runs on the light
requirements set (pandas / numpy / joblib) with no xgboost or scikit-learn installed. `hkia.train` re-exports both
functions, so the table written to models/baseline_b_airline_hour.joblib and the table used at evaluation time can
never drift apart.

The table is fitted on the training split only: mean of the target per (airline, scheduled hour HKT), falling back to
the airline's own mean and then to the global mean for combinations that never appeared in training.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def baseline_b_table(train: pd.DataFrame, target: str) -> tuple[pd.Series, pd.Series, float]:
    g = train.groupby(["airline", "sched_hour"])[target].mean()
    a = train.groupby("airline")[target].mean()
    return g, a, float(train[target].mean())


def baseline_b_predict(df: pd.DataFrame, table) -> np.ndarray:
    g, a, glob = table
    keys = pd.MultiIndex.from_frame(df[["airline", "sched_hour"]])
    p = g.reindex(keys).to_numpy()
    p_air = a.reindex(df["airline"]).to_numpy()
    return np.where(np.isnan(p), np.where(np.isnan(p_air), glob, p_air), p)
