"""As-of ("what would the service have shown at time T") scoring of departed flights, for fair model-vs-model comparison.

`hkia.predict` scores the live schedule at the moment it runs. This module replays that on flights that have since
departed, so two model directories can be compared on the SAME flights without waiting for the live predictions table
to accrue (which confounds model with window: each version only ever scores the days it was live).

For a scoring time T the replay is, by construction, what serving saw:
  - actual departure times after T are blanked, so same-day rolling delay statistics only see flights that had already
    left by T (and at least 2 h before the target's scheduled time, the training-time point-in-time rule);
  - METARs after T are dropped; flights scheduled after T get the latest observation <= T (persistence), exactly as
    `hkia.predict.apply_latest_weather`;
  - tropical-cyclone signals that had not started by T are dropped, and one in force at T is assumed to stay in force;
  - the inbound block is gated by `now=T` (`features.inbound_features`): nothing is known before scheduled - 2 h.

`day_ahead_times` gives the fixed-horizon scheme (every day scored at noon HKT the day before); `last_score_times`
gives the live scheme (every flight scored at the time of its last stored live prediction before departure).
Labels come from the unblanked flights table and are only ever joined on after scoring.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .features import (DELAY_MAX, DELAY_MIN, build_features, load_flights, load_links, load_metar, load_tc_signals)

HKT = dt.timezone(dt.timedelta(hours=8))
KEY = ["date", "flight_no", "scheduled_ts"]


@dataclass
class Inputs:
    flights: pd.DataFrame
    metar: pd.DataFrame
    tc: pd.DataFrame
    links: pd.DataFrame


def load_inputs(conn) -> Inputs:
    return Inputs(load_flights(conn), load_metar(conn), load_tc_signals(conn), load_links(conn))


def truth(flights: pd.DataFrame) -> pd.DataFrame:
    """Departed, not-cancelled flights with a label, under the same outlier rule as `build_features`."""
    t = flights[(flights["cancelled"] == 0) & flights["actual_ts"].notna()].copy()
    t["delay_min"] = (t["actual_ts"] - t["scheduled_ts"]).dt.total_seconds() / 60
    t = t[(t["delay_min"] >= DELAY_MIN) & (t["delay_min"] <= DELAY_MAX)]
    t["delayed15"] = (t["delay_min"] > 15).astype(int)
    return t[KEY + ["airline", "delay_min", "delayed15"]].reset_index(drop=True)


def asof_frame(inp: Inputs, now: pd.Timestamp, dates: list[str], top_dest: set) -> pd.DataFrame:
    """Feature rows of the not-cancelled flights scheduled on `dates` (HKT, 'YYYY-MM-DD'), as of `now` (tz-aware UTC).

    Only flights from the day before the first target to the day after the last are fed to the builder: every feature
    that looks around a flight (rolling delay means, congestion) reaches at most one calendar day.
    """
    from .predict import apply_latest_weather
    now = pd.Timestamp(now).tz_convert("UTC")
    lo = (pd.Timestamp(min(dates)) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    hi = (pd.Timestamp(max(dates)) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    fl = inp.flights[(inp.flights["date"] >= lo) & (inp.flights["date"] <= hi)].copy()
    fl.loc[fl["actual_ts"] > now, "actual_ts"] = pd.NaT
    metar = inp.metar[inp.metar["report_time"] <= now]
    tc = inp.tc[inp.tc["start_ts"] <= now].copy()
    tc.loc[tc["end_ts"] > now, "end_ts"] = now + pd.Timedelta(days=365)
    feat, _ = build_features(fl, metar, tc, top_dest=top_dest, keep_unlabelled=True, links=inp.links, now=now)
    feat, _ = apply_latest_weather(feat, metar, now)
    return feat[feat["date"].isin(dates) & (feat["cancelled"] == 0)].reset_index(drop=True)


def score_dir(models_dir: Path, feat: pd.DataFrame) -> pd.DataFrame:
    """Serve-path scoring of `feat` with a models/ directory: (p_delay15 calibrated, pred_delay_min), keyed like `feat`.
    The `dest` column is re-encoded to this model's own top-destination set, as `hkia.predict` does by building
    features per model."""
    import joblib

    from .calibrate import load_calibrator
    from .train import to_matrix
    models_dir = Path(models_dir)
    clf = joblib.load(models_dir / "xgb_delayed15.joblib")
    reg = joblib.load(models_dir / "xgb_delay_min.joblib")
    top = set(clf["cats"]["dest"].categories) - {"OTHER"}
    df = feat.copy()
    df["dest"] = df["dest"].where(df["dest"].isin(top), "OTHER")
    X, _ = to_matrix(df, clf["cats"], clf["features"])
    Xr, _ = to_matrix(df, reg["cats"], reg["features"])
    out = df[KEY].copy()
    out["p"] = load_calibrator(models_dir).predict(clf["model"].predict_proba(X)[:, 1])
    out["minutes"] = reg["model"].predict(Xr)
    return out


def baseline_dir(models_dir: Path, feat: pd.DataFrame) -> pd.DataFrame:
    """Airline x scheduled-hour baseline table saved beside a model, applied to `feat` (probability and minutes)."""
    import joblib

    from .baseline import baseline_b_predict
    tabs = joblib.load(Path(models_dir) / "baseline_b_airline_hour.joblib")
    out = feat[KEY].copy()
    out["p"] = baseline_b_predict(feat, tabs["clf"])
    out["minutes"] = baseline_b_predict(feat, tabs["reg"])
    return out


def recent_complete_dates(flights: pd.DataFrame, k: int = 7, min_departed: float = 0.9, after: str | None = None) -> list[str]:
    """The last `k` HKT dates whose not-cancelled flights have (almost) all got an actual time, i.e. whose labels are in.
    `after`: only dates strictly later than this 'YYYY-MM-DD' (e.g. past a model's calibration fold)."""
    f = flights[flights["cancelled"] == 0]
    share = f.groupby("date")["actual_ts"].apply(lambda s: s.notna().mean())
    ok = sorted(d for d, v in share.items() if v >= min_departed and (after is None or d > after))
    return ok[-k:]


def day_ahead_times(dates: list[str], hour_hkt: int = 12) -> dict[str, pd.Timestamp]:
    """date -> scoring time: `hour_hkt`:00 HKT on the previous calendar day."""
    out = {}
    for d in dates:
        t = dt.datetime.combine(dt.date.fromisoformat(d) - dt.timedelta(days=1), dt.time(hour_hkt), tzinfo=HKT)
        out[d] = pd.Timestamp(t).tz_convert("UTC")
    return out


def score_day_ahead(inp: Inputs, dates: list[str], model_dirs: dict[str, Path], top_dest: set,
                    hour_hkt: int = 12) -> pd.DataFrame:
    """Long frame (one row per flight x predictor) of every `dates` day scored `hour_hkt` HKT the day before.
    `model_dirs` name -> models/ directory; a 'baseline:<name>' row is added for each. Labels joined on."""
    return _score_at(inp, [(t, [d]) for d, t in day_ahead_times(dates, hour_hkt).items()], model_dirs, top_dest)


def score_last_live(inp: Inputs, matured: pd.DataFrame, model_dirs: dict[str, Path], top_dest: set) -> pd.DataFrame:
    """Same, but each flight at the time of its last stored live score before departure.
    `matured` = `hkia.evaluate.matured_predictions` output (needs date, flight_no, scheduled_ts, scored_at)."""
    m = matured.copy()
    m["_t"] = pd.to_datetime(m["scored_at"], utc=True, format="ISO8601")
    jobs = []
    for t, g in m.groupby("_t"):
        jobs.append((t, sorted(g["date"].unique()), g))
    return _score_at(inp, jobs, model_dirs, top_dest, restrict=True)


def _score_at(inp, jobs, model_dirs, top_dest, restrict=False) -> pd.DataFrame:
    tr = truth(inp.flights)
    parts = []
    for job in jobs:
        t, dates = job[0], job[1]
        feat = asof_frame(inp, t, dates, top_dest)
        if restrict:
            keys = job[2][["date", "flight_no"]].assign(scheduled_ts=pd.to_datetime(job[2]["scheduled_ts"], utc=True, format="ISO8601"))
            feat = feat.merge(keys, on=KEY, how="inner")
        if feat.empty:
            continue
        for name, d in model_dirs.items():
            s = score_dir(d, feat)
            parts.append(s.assign(predictor=name, scored_at=t))
            b = baseline_dir(d, feat)
            parts.append(b.assign(predictor=f"baseline:{name}", scored_at=t))
        parts.append(feat[KEY].assign(p=np.nan, minutes=np.nan, predictor="_inbound", scored_at=t,
                                      inbound_known=feat["inbound_known"].to_numpy()))
    long = pd.concat(parts, ignore_index=True)
    return long.merge(tr, on=KEY, how="inner")
