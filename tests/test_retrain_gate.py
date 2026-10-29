"""scripts/retrain_gate.py: the non-inferiority rules R1-R5 decide whether the weekly retrain ships."""
import importlib.util

import numpy as np
import pytest

from hkia.db import ROOT

spec = importlib.util.spec_from_file_location("retrain_gate", ROOT / "scripts" / "retrain_gate.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

pytest.importorskip("sklearn")


def _world(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    z = rng.normal(-1.5, 1.0, n)
    p_true = 1 / (1 + np.exp(-z))
    y = (rng.random(n) < p_true).astype(int)
    r = np.where(y == 1, rng.normal(40, 15, n), rng.normal(2, 8, n))
    return y, r, p_true


def _manifest(**inb):
    return {"features": ["a", "b"], "inbound": {"links_event_source": "sched", "inbound_dropout": 0.25, **inb}}


def _decide(cand, cur, y, r, cand_m=None, cur_m=None, **extra):
    res = G.paired_deltas(y, r, cand, cur, n_boot=300)
    res.update(extra)
    return G.decide(res, cand_m or _manifest(), cur_m or _manifest())


def test_identical_models_pass_every_gate():
    y, r, p = _world()
    out = _decide((p, r), (p, r), y, r)
    assert out["ship"] and all(c["ok"] for c in out["checks"])


def test_a_clearly_better_candidate_ships():
    y, r, p = _world()
    rng = np.random.default_rng(1)
    worse = np.clip(p + rng.normal(0, 0.2, len(p)), 0.01, 0.99)
    out = _decide((p, r), (worse, r + rng.normal(0, 10, len(r))), y, r)
    assert out["ship"]


def test_non_inferior_but_not_better_still_ships():
    """The point of the gate: a statistically indistinguishable (slightly noisier) candidate is allowed through."""
    y, r, p = _world()
    rng = np.random.default_rng(2)
    near = np.clip(p + rng.normal(0, 0.01, len(p)), 0.01, 0.99)
    assert _decide((near, r + 0.05), (p, r), y, r)["ship"]


def test_worse_ranking_fails_r1():
    y, r, p = _world()
    junk = np.random.default_rng(3).random(len(p)) * 0.5 + p * 0.1
    out = _decide((junk, r), (p, r), y, r)
    assert not out["ship"] and not next(c for c in out["checks"] if c["gate"] == "R1")["ok"]


def test_worse_minutes_fail_r2():
    y, r, p = _world()
    out = _decide((p, r + 1.0), (p, r), y, r)
    assert not out["ship"] and not next(c for c in out["checks"] if c["gate"] == "R2")["ok"]


def test_worse_probabilities_fail_r3_even_when_ranking_is_identical():
    """Same ranking (monotone transform) but badly over-confident probabilities: AUC unchanged, log loss worse."""
    y, r, p = _world()
    z = np.log(p / (1 - p))
    sharp = 1 / (1 + np.exp(-3 * z))
    out = _decide((sharp, r), (p, r), y, r)
    byg = {c["gate"]: c["ok"] for c in out["checks"]}
    assert byg["R1"] and not byg["R3"] and not out["ship"]


def test_candidate_that_reads_no_inbound_as_late_fails_r5():
    y, r, p = _world()
    iu = {"n": 3000, "observed_rate": 0.17, "candidate_mean_p": 0.23, "current_mean_p": 0.18}
    out = _decide((p, r), (p, r), y, r, inbound_unknown=iu)
    assert not out["ship"] and not next(c for c in out["checks"] if c["gate"] == "R5")["ok"]


@pytest.mark.parametrize("cand_m", [
    _manifest(links_event_source="actual"),
    _manifest(inbound_dropout=0.0),
    {**_manifest(), "features": ["a", "b", "c"]},
])
def test_recipe_drift_fails_r4(cand_m):
    y, r, p = _world()
    out = _decide((p, r), (p, r), y, r, cand_m=cand_m)
    assert not out["ship"] and not next(c for c in out["checks"] if c["gate"] == "R4")["ok"]


def test_too_small_a_test_window_fails_r4():
    y, r, p = _world(n=500)
    out = _decide((p, r), (p, r), y, r)
    assert not out["ship"] and not next(c for c in out["checks"] if c["gate"] == "R4")["ok"]


def test_render_names_the_failing_gates():
    y, r, p = _world()
    res = G.paired_deltas(y, r, (p, r + 1.0), (p, r), n_boot=200)
    rep = {**res, **G.decide(res, _manifest(), _manifest()), "test_window": ["a", "b"], "candidate_model": "c",
           "current_model": "d", "current_calibrator": "none"}
    assert G.render(rep).splitlines()[-1] == "HOLD: R2"
