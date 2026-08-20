"""Per-flight explanations of P(delay > 15 min): which three features moved this one prediction, and by how much.

Method — **local SHAP values from XGBoost itself** (`Booster.predict(..., pred_contribs=True)`), no `shap` package. The booster
returns one contribution per feature plus a bias term, in **log-odds**, and they sum exactly to the margin
(`sigmoid(bias + sum(contribs)) == predict_proba`); `tests/test_explain.py` asserts that identity on the saved model.

Units — the card reports **probability points (pp)**, converted from log-odds by local linearisation around this flight's own
prediction:

    pp = 100 * contribution_logodds * p * (1 - p)          (`to_pp`)

i.e. the first-order effect of that feature's log-odds push at the model's operating point p. It is an approximation: the pp
values do not add up to `p - p_base` exactly (the logistic is not linear), and it shrinks near p = 0 or 1 the same way the
logistic does. It is used because "+3 pp" is readable and "+0.21 log-odds" is not; the exact log-odds number is kept in the db
(`explanations.top_json`) and is what the ranking is done on. **Ranking is always by |log-odds|**, which is monotone in |pp| for a
fixed flight, so the top-3 is unaffected by the conversion.

What this is not: a causal claim. A SHAP value says how this model's output moves when the feature is included, given everything
else on the row — it explains the model, not the world. Said in the card footer and in the README.

Layout:
  - `attribute()` needs xgboost (scoring side, `hkia.predict`).
  - everything below `# --- templates` is pandas/stdlib only, so the Streamlit app and `hkia.export_json` can render the stored
    attributions without the training stack installed (Streamlit Cloud has no xgboost).

Storage: table `explanations`, primary key (date, flight_no, scheduled_ts) — **latest score only**, replaced in place on re-score,
never appended (the `predictions` table keeps the history; this one must not grow with it). `prune()` drops rows older than
`KEEP_DAYS` days so the table stays at ~one day of schedule x 3.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from typing import Any, Callable

import numpy as np
import pandas as pd

from .airlines import airline_name
from .airports import airport

TOP_K = 3
KEEP_DAYS = 1          # keep dates >= today-1 HKT: yesterday/today/tomorrow, exactly what hkia.export_json publishes
EXPLAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS explanations (
    date          TEXT NOT NULL,
    flight_no     TEXT NOT NULL,
    scheduled_ts  TEXT NOT NULL,   -- ISO +08:00 (matches flights.scheduled_ts)
    scored_at     TEXT NOT NULL,   -- UTC ISO of the score these attributions belong to
    model_version TEXT NOT NULL,
    p_delay15     REAL NOT NULL,   -- the probability the log-odds -> pp conversion linearises around
    base_logodds  REAL NOT NULL,   -- SHAP bias term (the model's average log-odds)
    top_json      TEXT NOT NULL,   -- [[feature, value, logodds_contribution], ...] top-3 by |contribution|
    PRIMARY KEY (date, flight_no, scheduled_ts)      -- latest only: INSERT OR REPLACE, never appended
);
"""


# ---------------------------------------------------------------- attribution (needs xgboost)
def attribute(model: Any, X: pd.DataFrame, features: list[str]) -> np.ndarray:
    """Batch SHAP contributions in log-odds. Returns (n_rows, n_features + 1); the last column is the bias term.

    `model` is the fitted XGBClassifier from models/xgb_delayed15.joblib; the sklearn wrapper has no pred_contribs argument,
    so this goes through `get_booster()` with the same `iteration_range` predict_proba uses (early stopping picked
    `best_iteration`), which is what makes the sum-to-margin identity hold.
    """
    import xgboost as xgb  # local: the dashboards render stored attributions without the training stack

    booster = model.get_booster() if hasattr(model, "get_booster") else model
    names = list(booster.feature_names or features)
    if names != list(features):
        raise ValueError(f"feature order mismatch: booster {names[:3]}... != features {list(features)[:3]}...")
    best = getattr(model, "best_iteration", None)
    rng = (0, int(best) + 1) if best is not None else (0, 0)
    dm = xgb.DMatrix(X[features], enable_categorical=True, feature_names=names)
    return booster.predict(dm, pred_contribs=True, iteration_range=rng)


def top_contributions(contribs: np.ndarray, features: list[str], k: int = TOP_K) -> list[list[int]]:
    """Indices of the k largest |contribution| per row, bias column excluded, strongest first."""
    c = np.asarray(contribs)[:, : len(features)]
    order = np.argsort(-np.abs(c), axis=1, kind="stable")[:, :k]
    return order.tolist()


def _scalar(v: Any) -> Any:
    """Feature value -> JSON-safe scalar (NaN/NaT -> None, numpy -> python, category -> str)."""
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if math.isnan(f) else round(f, 3)
    if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
        return int(v)
    if isinstance(v, (np.bool_, bool)):
        return int(v)
    s = str(v)
    return None if s in ("nan", "NaT", "None") else s


def _item(feature: str, model_v: Any, raw_v: Any, contrib: float) -> list:
    """One stored attribution: [feature, value, log-odds] — plus a 4th element when the row HAS a value but the model
    never saw that category (`to_matrix` maps unseen categories to NaN). Without the flag the card would say
    "operating carrier not on the schedule" about a carrier printed two lines above it."""
    v, raw = _scalar(model_v), _scalar(raw_v)
    if v is None and raw is not None:
        return [feature, raw, round(float(contrib), 5), 1]
    return [feature, v, round(float(contrib), 5)]


def explain_frame(tgt: pd.DataFrame, X: pd.DataFrame, contribs: np.ndarray, features: list[str],
                  k: int = TOP_K) -> pd.DataFrame:
    """One row per scored flight: base_logodds + top_json (top-k [feature, value, logodds]) — ready for `write`.

    `tgt` carries the raw feature values, `X` the matrix the model actually saw; they differ exactly when a category
    was unseen at training time, which `_item` records rather than hides."""
    order = top_contributions(contribs, features, k)
    base = np.asarray(contribs)[:, len(features)]
    rows = []
    for i, idx in enumerate(order):
        top = [_item(features[j], X.iloc[i, j],
                     tgt[features[j]].iloc[i] if features[j] in tgt.columns else None,
                     contribs[i, j])
               for j in idx]
        rows.append(json.dumps(top, separators=(",", ":"), ensure_ascii=False))
    return pd.DataFrame({"base_logodds": np.round(base, 5), "top_json": rows}, index=tgt.index)


# ---------------------------------------------------------------- storage
def write(conn, tgt: pd.DataFrame, version: str, now: dt.datetime, hkt: dt.timezone) -> int:
    """Replace the stored attributions of every scored flight in `tgt` (needs columns base_logodds / top_json).

    Latest-only by primary key, so a re-score overwrites the flight's row instead of adding one. A row whose
    probability and attributions are byte-identical to the stored one is left alone: an unchanged feature vector
    produces an identical score, and `hkia.predict.decide` does not store that score either — rewriting it would
    only churn the committed db (~1 MB/day over 48 cron runs) and would move `scored_at` away from the score in
    `predictions` that the card displays.
    """
    conn.executescript(EXPLAIN_SCHEMA)
    if not len(tgt) or "top_json" not in tgt.columns:
        return 0
    scored_at = now.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
    dates = sorted({str(d) for d in tgt["date"]})
    stored = {(d, f, s): (p, tj) for d, f, s, p, tj in conn.execute(
        f"SELECT date, flight_no, scheduled_ts, p_delay15, top_json FROM explanations "
        f"WHERE date IN ({','.join('?' * len(dates))})", dates)}
    rows = []
    for r in tgt.itertuples(index=False):
        if not isinstance(r.top_json, str):
            continue
        key = (r.date, r.flight_no, r.scheduled_ts.tz_convert(hkt).isoformat())
        p = float(r.p_delay15)
        if stored.get(key) == (p, r.top_json):
            continue
        rows.append((*key, scored_at, version, p, float(r.base_logodds), r.top_json))
    conn.executemany("INSERT OR REPLACE INTO explanations VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def prune(conn, now: dt.datetime, hkt: dt.timezone, keep_days: int = KEEP_DAYS) -> int:
    """Drop attributions for HKT dates before today - `keep_days` — the table is a rolling window, not a history."""
    cutoff = (now.astimezone(hkt).date() - dt.timedelta(days=keep_days)).isoformat()
    cur = conn.execute("DELETE FROM explanations WHERE date < ?", (cutoff,))
    return cur.rowcount or 0


# ---------------------------------------------------------------- templates (pandas/stdlib only)
def to_pp(logodds: float, p: float) -> float:
    """Log-odds contribution -> probability points, linearised at this flight's own p (see the module docstring)."""
    return 100.0 * float(logodds) * float(p) * (1.0 - float(p))


LABELS: dict[str, str] = {
    "airline": "Airline", "dest": "Destination", "dest_region": "Region", "terminal": "Terminal",
    "flt_cat": "Flight category",
    "sched_hour": "Time of day", "sched_minute_of_day": "Departure slot", "sched_dow": "Day of week",
    "is_holiday": "Public holiday", "is_weekend": "Weekend",
    "cong_pm60": "Congestion ±60 min", "cong_pm30": "Congestion ±30 min", "cong_same_hour": "Departures this hour",
    "n_dest_legs": "Route legs",
    "temp_c": "Temperature", "dewp_c": "Dew point", "wdir": "Wind direction", "wspd_kt": "Wind speed",
    "wgst_kt": "Gusts", "visib_sm": "Visibility", "ceiling_ft": "Cloud ceiling",
    "wx_rain": "Rain", "wx_ts": "Thunderstorm", "wx_fog": "Fog / mist", "metar_age_min": "Observation age",
    "tc_signal": "Typhoon signal", "msn_signal": "Monsoon signal",
    "airline_prevday_mean_delay": "Airline yesterday", "airline_prevday_n": "Airline history yesterday",
    "airline_sameday_mean_delay": "Airline today", "airline_sameday_n": "Airline history today",
    "airport_sameday_mean_delay": "HKIA today", "airport_sameday_n": "HKIA history today",
}

_REGION_NAMES = {
    "CN_MAINLAND": "mainland China", "TAIWAN": "Taiwan", "JAPAN": "Japan", "KOREA": "Korea",
    "SE_ASIA": "South-East Asia", "SOUTH_ASIA": "South Asia", "OCEANIA": "Oceania", "EUROPE": "Europe",
    "N_AMERICA": "North America", "MIDDLE_EAST": "the Middle East", "AFRICA": "Africa",
    "CENTRAL_ASIA": "Central Asia", "RUSSIA": "Russia", "OTHER": "an unmapped region",
}
_FLT_CAT = {"VFR": "clear (VFR)", "MVFR": "marginal (MVFR)", "IFR": "instrument conditions (IFR)",
            "LIFR": "low instrument conditions (LIFR)", "UNK": "unknown"}
_DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _i(v: Any) -> int:
    return int(round(float(v)))


def _band(v: float, lo: float, hi: float, low: str = "quiet", high: str = "busy") -> str:
    return f" ({low})" if v < lo else f" ({high})" if v > hi else ""


def _late(v: float) -> str:
    """'12 min late' / '3 min early' / 'on time' for a signed mean delay."""
    m = _i(v)
    return "on time" if m == 0 else (f"{m} min late" if m > 0 else f"{-m} min early")


# One hand-written line per feature in hkia.features.FEATURES. Factual: what the row says, not what the model "thinks".
# Each takes the raw feature value; a missing value falls through to `_na` in `line()`.
TEMPLATES: dict[str, Callable[[Any], str]] = {
    # -- categorical
    "airline": lambda v: (f"operated by {airline_name(str(v))} ({v})" if airline_name(str(v)) != str(v)
                          else f"operated by {v}"),
    "dest": lambda v: (f"flying to {airport(str(v))[0]} ({v})" if str(v) != "OTHER"
                       else "destination outside the model's top-30 list"),
    "dest_region": lambda v: f"route to {_REGION_NAMES.get(str(v), str(v))}",
    "terminal": lambda v: (f"departs from Terminal {str(v).upper().removeprefix('T')}" if str(v).upper().startswith("T")
                           else "no terminal on the schedule"),
    "flt_cat": lambda v: f"conditions at the field {_FLT_CAT.get(str(v), str(v))}",
    # -- calendar
    "sched_hour": lambda v: f"scheduled in the {_i(v):02d}:00 hour (HKT)",
    "sched_minute_of_day": lambda v: f"scheduled at {_i(v) // 60:02d}:{_i(v) % 60:02d} HKT",
    "sched_dow": lambda v: f"scheduled on a {_DOW[_i(v) % 7]}",
    "is_holiday": lambda v: "Hong Kong public holiday" if _i(v) else "not a public holiday",
    "is_weekend": lambda v: "weekend departure" if _i(v) else "weekday departure",
    # -- congestion
    "cong_pm60": lambda v: f"{_i(v)} other departures scheduled within ±60 min{_band(float(v), 30, 60)}",
    "cong_pm30": lambda v: f"{_i(v)} other departures scheduled within ±30 min{_band(float(v), 16, 32)}",
    "cong_same_hour": lambda v: f"{_i(v)} other departures in the same clock hour{_band(float(v), 15, 30)}",
    "n_dest_legs": lambda v: "single-leg flight" if _i(v) <= 1 else f"{_i(v)}-leg flight (intermediate stop)",
    # -- weather (latest METAR before the scheduled time; for future flights, the latest observation)
    "temp_c": lambda v: f"{_i(v)}°C at the field",
    "dewp_c": lambda v: f"dew point {_i(v)}°C",
    "wdir": lambda v: f"wind from {_i(v):03d}°",
    "wspd_kt": lambda v: f"wind {_i(v)} kt{_band(float(v), 5, 15, 'light', 'strong')}",
    "wgst_kt": lambda v: "no gusts reported" if _i(v) == 0 else f"gusting {_i(v)} kt",
    "visib_sm": lambda v: (f"visibility {float(v):.1f} statute miles (reduced)" if float(v) < 6
                           else "visibility 6+ statute miles (clear)"),
    "ceiling_ft": lambda v: f"cloud ceiling {_i(v):,} ft",
    "wx_rain": lambda v: "rain reported at the field" if _i(v) else "no rain in the latest METAR",
    "wx_ts": lambda v: "thunderstorm reported at the field" if _i(v) else "no thunderstorm in the latest METAR",
    "wx_fog": lambda v: "fog or mist reported at the field" if _i(v) else "no fog or mist in the latest METAR",
    "metar_age_min": lambda v: f"weather observation {_i(v)} min old",
    "tc_signal": lambda v: ("no tropical-cyclone signal in force" if _i(v) == 0
                            else f"tropical-cyclone signal {_i(v)} in force"),
    "msn_signal": lambda v: "strong monsoon signal in force" if _i(v) else "no monsoon signal in force",
    # -- point-in-time rolling delay stats
    # "the day before" is the day before *the flight's own date* (features.py keys on prev_date), which for
    # tomorrow's departures is today — so this must not say "yesterday".
    "airline_prevday_mean_delay": lambda v: f"this airline averaged {_late(v)} the day before",
    "airline_prevday_n": lambda v: f"{_i(v)} of this airline's flights had departed the day before",
    "airline_sameday_mean_delay": lambda v: f"this airline is running {_late(v)} today so far",
    "airline_sameday_n": lambda v: f"{_i(v)} of this airline's flights have departed today so far",
    "airport_sameday_mean_delay": lambda v: f"HKIA is running {_late(v)} today so far",
    "airport_sameday_n": lambda v: f"{_i(v)} departures have left HKIA today so far",
}


# A missing value is itself informative here (no observation, no history yet), so it gets its own hand-written line.
NO_METAR = "no METAR on file near the scheduled time"
MISSING: dict[str, str] = {
    "airline": "operating carrier not on the schedule",
    "dest": "no destination on the schedule",
    "dest_region": "destination not in the region map",
    "terminal": "no terminal on the schedule",
    "flt_cat": NO_METAR,
    "temp_c": NO_METAR, "dewp_c": NO_METAR, "wdir": "wind direction variable or not reported",
    "wspd_kt": NO_METAR, "wgst_kt": NO_METAR, "visib_sm": NO_METAR,
    "ceiling_ft": "no cloud ceiling reported (sky clear or scattered)",
    "metar_age_min": NO_METAR,
    "airline_prevday_mean_delay": "no flights on file for this airline the day before",
    "airline_sameday_mean_delay": "none of this airline's flights have departed yet that day",
    "airport_sameday_mean_delay": "no HKIA departures recorded yet that day",
}


def _na(feature: str) -> str:
    return MISSING.get(feature, f"no {LABELS.get(feature, feature).lower()} on file for this flight")


def _unseen(feature: str, value: Any) -> str:
    """The row has this value but the model never saw the category, so it scored the flight as if it were unknown."""
    return f"{value}: {LABELS.get(feature, feature).lower()} not in the model's training data"


def line(feature: str, value: Any) -> str:
    """Plain-English one-liner for one (feature, value). Never raises: unknown feature / bad value -> a factual fallback."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return _na(feature)
    fn = TEMPLATES.get(feature)
    if fn is None:
        return f"{LABELS.get(feature, feature)} = {value}"
    try:
        return fn(value)
    except (ValueError, TypeError, IndexError, KeyError, OverflowError):
        return f"{LABELS.get(feature, feature)} = {value}"


def why(top: list, p: float, k: int = TOP_K) -> list[dict]:
    """Stored top_json + this flight's p -> renderable rows.

    [{feature, label, value, logodds, pp, dir, text}, ...] — `dir` is +1 when the feature pushed P(delay > 15) up.
    """
    out = []
    for item in (top or [])[:k]:
        try:
            feature, value, logodds = item[0], item[1], float(item[2])
        except (TypeError, ValueError, IndexError):
            continue
        unseen = len(item) > 3 and bool(item[3])
        out.append({"feature": feature, "label": LABELS.get(feature, feature), "value": value,
                    "logodds": round(logodds, 5), "pp": round(to_pp(logodds, p), 2),
                    "dir": 1 if logodds > 0 else -1,
                    "text": _unseen(feature, value) if unseen else line(feature, value)})
    return out


def compact(rows: list[dict]) -> list[list]:
    """`why()` rows -> the JSON shape the web app reads: [[dir, one-liner, pp], ...] (see docs/features.md)."""
    return [[r["dir"], r["text"], r["pp"]] for r in rows]


def load(conn, date: str) -> dict[tuple[str, str], list[dict]]:
    """(flight_no, scheduled_ts) -> `why()` rows for one HKT date; {} when the table does not exist yet."""
    has = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='explanations'").fetchone()
    if not has:
        return {}
    out: dict[tuple[str, str], list[dict]] = {}
    for fn, st, p, top in conn.execute(
            "SELECT flight_no, scheduled_ts, p_delay15, top_json FROM explanations WHERE date=?", (date,)):
        try:
            rows = why(json.loads(top), float(p))
        except (ValueError, TypeError):
            continue
        if rows:
            out[(fn, st)] = rows
    return out


FOOTER = ("Attributions are local SHAP values for this single prediction, in probability points: they explain the model, "
          "not the world.")
