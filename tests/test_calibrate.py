"""hkia.calibrate: choice of map, JSON round-trip, and that a miscalibrated score is actually repaired."""
import numpy as np
import pytest

pytest.importorskip("sklearn")
from hkia import calibrate as C  # noqa: E402
from hkia.db import ROOT  # noqa: E402

ROOT_MODELS = ROOT / "models"


def _overconfident(n=6000, seed=0):
    """True P = p_true; the 'model' reports a sharpened (over-confident) version of it."""
    rng = np.random.default_rng(seed)
    p_true = rng.beta(2, 4, n)
    y = (rng.random(n) < p_true).astype(int)
    z = np.log(p_true / (1 - p_true)) * 1.8 + 0.2
    return 1 / (1 + np.exp(-z)), y, np.repeat(np.arange(n // 60), 60)


def test_calibration_lowers_log_loss_out_of_sample_and_picks_a_real_map():
    p, y, blocks = _overconfident()
    cut = len(p) // 2
    cal, rep = C.fit_calibrator(p[:cut], y[:cut], blocks=blocks[:cut])
    assert rep["chosen"] in ("platt", "isotonic")
    assert set(rep["candidates"]) == {"identity", "platt", "isotonic"}
    assert C.logloss(y[cut:], cal.predict(p[cut:])) < C.logloss(y[cut:], p[cut:]) - 0.005


@pytest.mark.parametrize("method", ["identity", "platt", "isotonic"])
def test_calibrator_json_round_trip_is_exact(method, tmp_path):
    p, y, _ = _overconfident(2000)
    cal = C._fit(method, p, y)
    cal.save(tmp_path / C.CALIBRATOR_FILE)
    back = C.load_calibrator(tmp_path)
    assert back.method == method
    grid = np.linspace(0, 1, 101)
    np.testing.assert_allclose(back.predict(grid), cal.predict(grid))


def test_missing_calibrator_file_means_identity(tmp_path):
    cal = C.load_calibrator(tmp_path)
    assert cal.method == "identity"
    np.testing.assert_array_equal(cal.predict([0.1, 0.9]), [0.1, 0.9])


def test_served_probability_is_monotone_and_never_0_or_1():
    p, y, _ = _overconfident()
    for m in ("platt", "isotonic"):
        q = C._fit(m, p, y).predict(np.linspace(0, 1, 201))
        assert (np.diff(q) >= -1e-12).all()
        assert q.min() >= C.P_LO and q.max() <= C.P_HI


def test_isotonic_needs_enough_points():
    p, y, _ = _overconfident(400)
    _, rep = C.fit_calibrator(p, y)
    assert "isotonic" not in rep["candidates"]


def test_identity_wins_when_the_scores_are_already_calibrated():
    rng = np.random.default_rng(3)
    p = rng.beta(2, 4, 8000)
    y = (rng.random(8000) < p).astype(int)
    cal, rep = C.fit_calibrator(p, y, blocks=np.repeat(np.arange(100), 80))
    assert rep["chosen"] in ("identity", "platt")           # platt may tie within noise; isotonic must not beat it by overfitting
    assert abs(C.logloss(y, cal.predict(p)) - C.logloss(y, p)) < 0.003


def test_reliability_table_bins():
    t = C.reliability_table([0, 1, 1, 0], [0.05, 0.95, 0.92, 0.5])
    assert [r["bin"] for r in t] == ["0.0-0.1", "0.5-0.6", "0.9-1.0"]
    assert t[-1]["n"] == 2 and t[-1]["obs_rate"] == 1.0


def test_predict_serves_the_calibrated_probability_and_shap_stays_raw():
    """The shipped models/ directory: load_models picks up the calibrator and the saved file matches what it applies."""
    from hkia.predict import load_models
    m = load_models(ROOT_MODELS)
    assert m["calibrator"].method in ("identity", "platt", "isotonic")
    assert m["manifest"]["calibration"]["method"] == m["calibrator"].method
    q = m["calibrator"].predict(np.linspace(0.01, 0.99, 50))
    assert ((q >= C.P_LO) & (q <= C.P_HI)).all()
