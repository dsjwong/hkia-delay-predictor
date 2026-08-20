"""hkia.explain: SHAP extraction on a deterministic synthetic model, template coverage, latest-only storage."""
import datetime as dt
import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hkia import explain as E
from hkia.db import ROOT
from hkia.features import CATEGORICAL, FEATURES

HKT = dt.timezone(dt.timedelta(hours=8))
xgb = pytest.importorskip("xgboost")


# ---------------------------------------------------------------- attribution
def _toy_model(n: int = 400):
    """A tiny, seeded XGBClassifier over three features where the label depends almost entirely on `wx_ts`."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "wx_ts": rng.integers(0, 2, n),
        "cong_pm60": rng.integers(20, 70, n),
        "airline": pd.Categorical(rng.choice(["CPA", "HDA"], n), categories=["CPA", "HDA"]),
    })
    y = ((df["wx_ts"] == 1) ^ (rng.uniform(size=n) < 0.05)).astype(int)
    m = xgb.XGBClassifier(n_estimators=30, max_depth=3, learning_rate=0.3, tree_method="hist",
                          enable_categorical=True, random_state=0, n_jobs=1)
    m.fit(df, y)
    return m, df, list(df.columns)


def test_contributions_sum_to_the_margin_and_rank_the_driver():
    m, X, feats = _toy_model()
    c = E.attribute(m, X, feats)
    assert c.shape == (len(X), len(feats) + 1)
    # the identity that makes this an exact decomposition of *this* prediction: bias + contributions == the margin
    p = m.predict_proba(X)[:, 1]
    assert np.allclose(1 / (1 + np.exp(-c.sum(axis=1))), p, atol=1e-5)
    # the label was built from wx_ts, so wx_ts must be the top driver on (nearly) every row
    top = np.array(E.top_contributions(c, feats, k=1)).ravel()
    assert (top == feats.index("wx_ts")).mean() > 0.95
    # ...and it pushes P up when the thunderstorm flag is set, down when it is not
    ts = c[:, feats.index("wx_ts")]
    assert (ts[X["wx_ts"] == 1] > 0).all() and (ts[X["wx_ts"] == 0] < 0).all()


def test_explain_frame_stores_top3_with_values_and_is_json_safe():
    m, X, feats = _toy_model()
    c = E.attribute(m, X, feats)
    tgt = pd.DataFrame(index=X.index)
    out = E.explain_frame(tgt, X, c, feats)
    assert list(out.columns) == ["base_logodds", "top_json"] and len(out) == len(X)
    top = json.loads(out["top_json"].iloc[0])
    assert len(top) == 3 and [t[0] for t in top][0] == "wx_ts"
    assert all(isinstance(t[0], str) and isinstance(t[2], float) for t in top)
    assert all(len(t) == 3 for t in top), "no unseen-category flag when every value was seen"
    # values round-trip as plain JSON scalars (numpy ints / pandas categories would not)
    json.dumps(top)
    assert top[0][1] == int(X["wx_ts"].iloc[0])
    assert {t[0] for t in top} <= set(feats)


def test_unseen_category_is_labelled_instead_of_reported_missing():
    """to_matrix maps a category the model never saw to NaN; the card must not then claim the row has no airline."""
    m, X, feats = _toy_model()
    tgt = X.copy()
    tgt["airline"] = "NEW"                     # a carrier that appeared at HKIA after training
    seen = X.copy()
    seen["airline"] = pd.Categorical([None] * len(X), categories=["CPA", "HDA"])   # what to_matrix would produce
    c = E.attribute(m, seen, feats)
    top = json.loads(E.explain_frame(tgt, seen, c, feats)["top_json"].iloc[0])
    item = next(t for t in top if t[0] == "airline")
    assert item[1] == "NEW" and len(item) == 4 and item[3] == 1
    text = E.why(top, p=0.5)[[t[0] for t in top].index("airline")]["text"]
    assert text == "NEW: airline not in the model's training data"
    assert "not on the schedule" not in text


def test_pp_conversion_is_the_logistic_slope():
    # local linearisation: dp/d(logodds) = p(1-p); the sign never flips and it is largest at p = 0.5
    assert E.to_pp(1.0, 0.5) == pytest.approx(25.0)
    assert E.to_pp(-0.4, 0.5) == pytest.approx(-10.0)
    assert abs(E.to_pp(1.0, 0.05)) < abs(E.to_pp(1.0, 0.5))
    assert E.to_pp(0.3, 0.2) > 0 > E.to_pp(-0.3, 0.2)


@pytest.mark.skipif(not (ROOT / "models" / "xgb_delayed15.joblib").exists(), reason="models/ not present")
def test_saved_model_supports_pred_contribs():
    """The shipped sklearn-wrapper artefact must yield contributions that reproduce its own predict_proba."""
    import joblib
    b = joblib.load(ROOT / "models" / "xgb_delayed15.joblib")
    cats, feats = b["cats"], b["features"]
    row = {f: ([cats[f].categories[0]] * 4 if f in cats else np.linspace(1, 40, 4)) for f in feats}
    X = pd.DataFrame(row)
    for c_ in CATEGORICAL:
        X[c_] = X[c_].astype(cats[c_])
    c = E.attribute(b["model"], X, feats)
    assert c.shape == (4, len(feats) + 1)
    assert np.allclose(1 / (1 + np.exp(-c.sum(axis=1))), b["model"].predict_proba(X)[:, 1], atol=1e-5)


# ---------------------------------------------------------------- templates
NOT_A_FEATURE = {"metar", "metar_hist", "tc_signals"}   # db tables named in the same section
DOC_ONLY = {"sched_month"}                   # documented as present in the parquet but excluded from FEATURES


def _documented_features() -> set[str]:
    sec = (ROOT / "docs" / "features.md").read_text().split("## Model features")[1].split("## Weather backfill")[0]
    return {m for m in re.findall(r"`([^`]+)`", sec) if re.fullmatch(r"[a-z][a-z0-9_]*", m)} - NOT_A_FEATURE


def test_every_feature_has_a_label_and_a_template():
    assert set(E.TEMPLATES) == set(FEATURES), "TEMPLATES must cover FEATURES exactly"
    assert set(E.LABELS) == set(FEATURES), "LABELS must cover FEATURES exactly"
    assert len(FEATURES) == 33
    missing = _documented_features() - set(E.TEMPLATES) - DOC_ONLY
    assert not missing, f"documented in docs/features.md but no template in hkia.explain: {sorted(missing)}"


def test_templates_render_plain_english_for_a_plausible_value():
    sample = {"airline": "CPA", "dest": "TPE", "dest_region": "TAIWAN", "terminal": "T1", "flt_cat": "VFR",
              "sched_hour": 18, "sched_minute_of_day": 1115, "sched_dow": 2, "is_holiday": 0, "is_weekend": 1,
              "cong_pm60": 34, "cong_pm30": 18, "cong_same_hour": 22, "n_dest_legs": 1,
              "temp_c": 31.0, "dewp_c": 26.0, "wdir": 90, "wspd_kt": 10, "wgst_kt": 0, "visib_sm": 6.21,
              "ceiling_ft": 1200, "wx_rain": 1, "wx_ts": 1, "wx_fog": 0, "metar_age_min": 45,
              "tc_signal": 8, "msn_signal": 0,
              "airline_prevday_mean_delay": 12.4, "airline_prevday_n": 38,
              "airline_sameday_mean_delay": -3.2, "airline_sameday_n": 14,
              "airport_sameday_mean_delay": 11.0, "airport_sameday_n": 221}
    assert set(sample) == set(FEATURES)
    for f, v in sample.items():
        s = E.line(f, v)
        assert s and s[0].islower() or s[0].isupper() or s[0].isdigit(), f
        assert len(s) < 90, f"{f}: one-liner too long for a card row: {s!r}"
        assert "nan" not in s.lower() and "None" not in s, f"{f}: {s!r}"
    assert E.line("cong_pm60", 34) == "34 other departures scheduled within ±60 min"
    assert E.line("cong_pm60", 70).endswith("(busy)") and E.line("cong_pm60", 12).endswith("(quiet)")
    assert E.line("wx_ts", 1) == "thunderstorm reported at the field"
    assert E.line("wx_ts", 0) == "no thunderstorm in the latest METAR"
    assert E.line("airport_sameday_mean_delay", 11.0) == "HKIA is running 11 min late today so far"
    assert E.line("airline_sameday_mean_delay", -3.2) == "this airline is running 3 min early today so far"
    assert E.line("sched_minute_of_day", 1115) == "scheduled at 18:35 HKT"
    # "the day before", never "yesterday": for a tomorrow flight the referenced day is today
    assert E.line("airline_prevday_mean_delay", 12.4) == "this airline averaged 12 min late the day before"
    assert "yesterday" not in E.line("airline_prevday_n", 38)
    assert E.line("terminal", "t1") == "departs from Terminal 1"
    assert E.line("metar_age_min", float("inf")).startswith("Observation age =")
    assert E.line("tc_signal", 8) == "tropical-cyclone signal 8 in force"
    assert "Cathay" in E.line("airline", "CPA") and "Taipei" in E.line("dest", "TPE")


def test_missing_values_get_their_own_line_and_nothing_raises():
    for f in FEATURES:
        for v in (None, float("nan")):
            s = E.line(f, v)
            assert s and "nan" not in s.lower()
    assert E.line("ceiling_ft", None) == "no cloud ceiling reported (sky clear or scattered)"
    assert E.line("airport_sameday_mean_delay", np.nan) == "no HKIA departures recorded yet that day"
    assert E.line("temp_c", None) == E.NO_METAR
    # unknown feature / nonsense value never raises
    assert E.line("not_a_feature", 3) == "not_a_feature = 3"
    assert E.line("sched_dow", "banana").startswith("Day of week =")


def test_why_and_compact_shape():
    top = [["wx_ts", 1, 0.4], ["airline", "CPA", -0.25], ["cong_pm60", 34, 0.1]]
    rows = E.why(top, p=0.5)
    assert [r["dir"] for r in rows] == [1, -1, 1]
    assert rows[0]["pp"] == pytest.approx(10.0) and rows[0]["label"] == "Thunderstorm"
    assert rows[0]["text"] == "thunderstorm reported at the field"
    c = E.compact(rows)
    assert c == [[1, rows[0]["text"], rows[0]["pp"]], [-1, rows[1]["text"], rows[1]["pp"]],
                 [1, rows[2]["text"], rows[2]["pp"]]]
    assert E.why([], 0.5) == [] and E.why(None, 0.5) == []
    assert E.why([["wx_ts"]], 0.5) == []                 # malformed rows are skipped, not raised on


# ---------------------------------------------------------------- storage
def _tgt(date: str, p: float, top: list) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [date], "flight_no": ["CX 255"],
        "scheduled_ts": [pd.Timestamp(f"{date}T08:00:00", tz="UTC")],
        "p_delay15": [p], "base_logodds": [-0.97],
        "top_json": [json.dumps(top, separators=(",", ":"))],
    })


def test_storage_keeps_only_the_latest_score_per_flight():
    conn = sqlite3.connect(":memory:")
    now = dt.datetime(2026, 8, 20, 4, 0, tzinfo=dt.timezone.utc)
    assert E.write(conn, _tgt("2026-08-20", 0.30, [["wx_ts", 0, -0.2]]), "v1", now, HKT) == 1
    # a second score of the same flight replaces the row instead of appending one (the DB-growth rule)
    later = now + dt.timedelta(hours=3)
    assert E.write(conn, _tgt("2026-08-20", 0.62, [["wx_ts", 1, 0.5]]), "v1", later, HKT) == 1
    # a third score with identical p and attributions is not rewritten at all (no churn on the committed db)
    later2 = now + dt.timedelta(hours=6)
    assert E.write(conn, _tgt("2026-08-20", 0.62, [["wx_ts", 1, 0.5]]), "v1", later2, HKT) == 0
    rows = conn.execute("SELECT scored_at, p_delay15, top_json FROM explanations").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == later.isoformat(timespec="seconds") and rows[0][1] == 0.62
    assert json.loads(rows[0][2])[0][2] == 0.5
    # and a flight with a different scheduled time is a different row
    other = _tgt("2026-08-20", 0.4, [["wx_ts", 1, 0.3]])
    other["scheduled_ts"] = [pd.Timestamp("2026-08-20T09:00:00", tz="UTC")]
    E.write(conn, other, "v1", later, HKT)
    assert conn.execute("SELECT COUNT(*) FROM explanations").fetchone()[0] == 2


def test_prune_drops_dates_outside_the_window():
    conn = sqlite3.connect(":memory:")
    now = dt.datetime(2026, 8, 20, 4, 0, tzinfo=dt.timezone.utc)   # 12:00 HKT on the 20th
    for d in ("2026-08-16", "2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21"):
        E.write(conn, _tgt(d, 0.4, [["wx_ts", 1, 0.3]]), "v1", now, HKT)
    assert E.prune(conn, now, HKT) == 3                             # 16th, 17th, 18th
    kept = [r[0] for r in conn.execute("SELECT date FROM explanations ORDER BY date")]
    assert kept == ["2026-08-19", "2026-08-20", "2026-08-21"]       # yesterday / today / tomorrow
    assert E.prune(conn, now, HKT) == 0                             # idempotent


def test_write_is_a_noop_without_attributions():
    conn = sqlite3.connect(":memory:")
    now = dt.datetime(2026, 8, 20, 4, 0, tzinfo=dt.timezone.utc)
    assert E.write(conn, pd.DataFrame(), "v1", now, HKT) == 0
    assert E.write(conn, pd.DataFrame({"date": ["x"]}), "v1", now, HKT) == 0


def test_load_returns_rendered_rows_and_tolerates_a_missing_table():
    conn = sqlite3.connect(":memory:")
    assert E.load(conn, "2026-08-20") == {}
    now = dt.datetime(2026, 8, 20, 4, 0, tzinfo=dt.timezone.utc)
    E.write(conn, _tgt("2026-08-20", 0.5, [["wx_ts", 1, 0.4], ["cong_pm60", 70, -0.2]]), "v1", now, HKT)
    got = E.load(conn, "2026-08-20")
    key = ("CX 255", pd.Timestamp("2026-08-20T08:00:00", tz="UTC").tz_convert(HKT).isoformat())
    assert list(got) == [key]
    assert [r["text"] for r in got[key]] == ["thunderstorm reported at the field",
                                             "70 other departures scheduled within ±60 min (busy)"]
    assert got[key][0]["pp"] == pytest.approx(10.0)
    assert E.load(conn, "2026-08-19") == {}


def test_module_is_importable_without_xgboost(monkeypatch):
    """The dashboards render stored attributions on Streamlit Cloud, which has no xgboost — only `attribute` may need it."""
    src = Path(E.__file__).read_text()
    head = src.split("# ---------------------------------------------------------------- templates")[0]
    assert "import xgboost" not in head.split("def attribute")[0], "xgboost must not be a module-level import"
    assert "import xgboost" in src.split("def attribute")[1].split("def ")[0]
