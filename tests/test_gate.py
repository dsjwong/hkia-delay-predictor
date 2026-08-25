"""scripts/inbound_gate.py: the script that decides whether the inbound block ships, so every gate needs a failing case.

Each test drives `main()` and asserts SystemExit(1) plus the gate name in stdout — the script's contract is "exit
non-zero with one line saying which gate failed", not a table.
"""
import importlib.util
import json

import pytest

from hkia.db import ROOT

spec = importlib.util.spec_from_file_location("inbound_gate", ROOT / "scripts" / "inbound_gate.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def _probes(n_each=200, rate=0.24, span_h=8, k=3, r_serve=0.24, r_train=0.32, p_drop=0.25):
    stamps = [f"2026-08-2{4 + i * span_h // 24}T{(2 + i * span_h) % 24:02d}:00:00+00:00" for i in range(k)]
    return {"probes": [{"probe_utc": t, "n": n_each, "rate": rate} for t in stamps],
            "r_serve": r_serve, "r_train": r_train, "p_drop": p_drop, "rule": "clip(1 - r_serve/r_train, 0, 0.6)"}


def _manifest(ci=(0.004, 0.021), mae=(15.9, 16.0), src="sched", dropout=0.25, serve_rate=None, **kw):
    m = {"features": [f"f{i}" for i in range(38)], "git_sha": "abc1234", "created_at": "2026-08-24T00:00:00+00:00",
         "ablation_test": {"full": {"auc": 0.68}, "no_inbound": {"auc": 0.66}},
         "inbound": {"known_rate": {"train": 0.23, "val": 0.22, "test": 0.24}, "inbound_dropout": dropout,
                     "links_event_source": src, "serve_rate": serve_rate if serve_rate is not None else _probes()},
         "inbound_gate": {"n_test_seeds": 5, "ci_test_seed_0": {"d_auc": list(ci), "d_mae": [-0.13, 0.006]},
                          "mean": {"mae_full": mae[0], "mae_no_inbound": mae[1], "d_auc": 0.009},
                          "per_seed": [{"d_auc": 0.003}, {"d_auc": 0.017}],
                          "sensitivity": {"inbound_dropout": 0.35, "d_auc": 0.026}}}
    m["inbound"].update(kw)
    return m


def _write(tmp_path, manifest, cur_p=0.251, cand_p=0.260):
    p = tmp_path / "MANIFEST.json"
    p.write_text(json.dumps(manifest))
    for name, v in (("cur.json", cur_p), ("cand.json", cand_p)):
        (tmp_path / name).write_text(json.dumps({"horizon": {">12h": {"n": 420, "p_mean": v}}}))
    return [str(p), str(tmp_path / "cur.json"), str(tmp_path / "cand.json")]


def _run(paths, expected_dropout=0.25):
    manifest, cur, cand = paths
    return G.main(["--manifest", manifest, "--expected-dropout", str(expected_dropout),
                   "--current-predict-json", cur, "--candidate-predict-json", cand])


def _fails(capsys, paths, gate, **kw):
    with pytest.raises(SystemExit) as e:
        _run(paths, **kw)
    out = capsys.readouterr().out
    assert e.value.code == 1 and out.splitlines()[-1].startswith(f"FAIL {gate}"), out
    return out


def test_all_gates_green_exits_zero(tmp_path, capsys):
    assert _run(_write(tmp_path, _manifest())) == 0
    assert "PASS: all gates (A-D) green" in capsys.readouterr().out


def test_gate_a_needs_the_auc_ci_entirely_above_zero(tmp_path, capsys):
    out = _fails(capsys, _write(tmp_path, _manifest(ci=(-0.014, 0.018))), "GATE-A")
    assert "includes 0" in out and "spread" in out          # the across-seed spread is reported, not gated
    _fails(capsys, _write(tmp_path, _manifest(ci=(0.0, 0.02))), "GATE-A")    # a CI touching 0 is not "above 0"
    assert _run(_write(tmp_path, _manifest(ci=(0.0001, 0.02)))) == 0


def test_gate_b_fails_when_the_inbound_block_costs_mae(tmp_path, capsys):
    out = _fails(capsys, _write(tmp_path, _manifest(mae=(16.1, 16.0))), "GATE-B")
    assert "worse with the inbound block" in out
    assert _run(_write(tmp_path, _manifest(mae=(16.0, 16.0)))) == 0          # a tie passes


def test_gate_c_fails_on_day_ahead_probability_inflation(tmp_path, capsys):
    out = _fails(capsys, _write(tmp_path, _manifest(), cur_p=0.251, cand_p=0.290), "GATE-C")
    assert ">12h" in out
    assert _run(_write(tmp_path, _manifest(), cur_p=0.251, cand_p=0.270)) == 0   # +0.019, inside the limit
    _fails(capsys, _write(tmp_path, _manifest(), cur_p=0.251, cand_p=0.272), "GATE-C")   # +0.021, over it
    # a candidate that lowers day-ahead probabilities is never a drift failure
    assert _run(_write(tmp_path, _manifest(), cur_p=0.251, cand_p=0.180)) == 0


def test_gate_c_requires_both_predict_summaries(tmp_path, capsys):
    manifest = str(tmp_path / "m.json")
    (tmp_path / "m.json").write_text(json.dumps(_manifest()))
    with pytest.raises(SystemExit) as e:
        G.main(["--manifest", manifest, "--expected-dropout", "0.25"])
    assert e.value.code == 1 and "FAIL GATE-C" in capsys.readouterr().out


def test_gate_d_rejects_links_built_from_actual_departure_times(tmp_path, capsys):
    out = _fails(capsys, _write(tmp_path, _manifest(src="actual")), "GATE-D")
    assert "links_event_source" in out


def test_gate_d_rejects_a_dropout_the_operator_mistyped(tmp_path, capsys):
    _fails(capsys, _write(tmp_path, _manifest(dropout=0.25)), "GATE-D", expected_dropout=0.30)


def test_gate_d_rejects_a_missing_no_inbound_or_sensitivity_row(tmp_path, capsys):
    m = _manifest()
    m["ablation_test"].pop("no_inbound")
    _fails(capsys, _write(tmp_path, m), "GATE-D")
    m = _manifest()
    m["inbound_gate"].pop("sensitivity")
    out = _fails(capsys, _write(tmp_path, m), "GATE-D")
    assert "sensitivity" in out


# ---------------------------------------------------------------- GATE-D: p_drop re-derived from the probes
def test_probes_must_span_six_hours(tmp_path, capsys):
    out = _fails(capsys, _write(tmp_path, _manifest(serve_rate=_probes(k=1))), "GATE-D")
    assert "snapshot" in out                                  # a single probe cannot span anything
    out = _fails(capsys, _write(tmp_path, _manifest(serve_rate=_probes(k=2, span_h=2))), "GATE-D")
    assert "span only 2.0 h" in out and "snapshot" in out


def test_zero_flight_probes_are_ignored_not_counted_as_zero_coverage(tmp_path, capsys):
    """A quiet-hours probe measured nothing; letting it into min(rates)/pooled n would drag r_serve to 0."""
    sr = _probes(n_each=200, k=3, r_serve=0.24)               # 3 good probes, pooled n = 600
    sr["probes"].append({"probe_utc": "2026-08-24T19:00:00+00:00", "n": 0, "rate": 0.0})
    assert _run(_write(tmp_path, _manifest(serve_rate=sr))) == 0
    out = capsys.readouterr().out
    assert "pooled n=600" in out and "1 zero-flight probe(s) ignored" in out
    # ... and it must not drag the thin-data rule down either: pooled n stays 600, so the min-rate rule is not applied
    assert "lowest probe rate" not in out


def test_all_zero_probes_fail_with_a_clear_message(tmp_path, capsys):
    sr = _probes(k=3)
    for p in sr["probes"]:
        p["n"], p["rate"] = 0, 0.0
    out = _fails(capsys, _write(tmp_path, _manifest(serve_rate=sr)), "GATE-D")
    assert "recorded 0 flights" in out and "nothing was measured" in out
    # one good probe among empties is still a snapshot, not a measurement
    sr["probes"][0].update(n=300, rate=0.24)
    out = _fails(capsys, _write(tmp_path, _manifest(serve_rate=sr)), "GATE-D")
    assert "only 1 of 3 probe(s) saw any flights" in out


def test_missing_or_empty_probes_fail(tmp_path, capsys):
    thin = _probes()
    thin["probes"] = []
    _fails(capsys, _write(tmp_path, _manifest(serve_rate=thin)), "GATE-D")
    _fails(capsys, _write(tmp_path, _manifest(serve_rate={})), "GATE-D")


def test_thin_probes_must_take_the_lowest_rate(tmp_path, capsys):
    """Pooled n < 200: r_serve has to be the lowest probe rate, not an average that flatters coverage."""
    sr = _probes(n_each=40, k=3, r_serve=0.24)          # pooled n = 120
    sr["probes"][0]["rate"] = 0.18                       # ... but one probe measured much less
    out = _fails(capsys, _write(tmp_path, _manifest(serve_rate=sr)), "GATE-D")
    assert "lowest probe rate" in out and "0.1800" in out
    sr["r_serve"] = 0.18                                 # take the low end -> p_drop 1 - 0.18/0.32 = 0.4375
    sr["p_drop"] = 0.4375
    assert _run(_write(tmp_path, _manifest(dropout=0.4375, serve_rate=sr)), expected_dropout=0.4375) == 0
    # with a healthy pooled n the same averaged r_serve is fine
    ok = _probes(n_each=200, k=3, r_serve=0.24)
    ok["probes"][0]["rate"] = 0.18
    assert _run(_write(tmp_path, _manifest(serve_rate=ok))) == 0


def test_p_drop_may_be_rounded_up_but_never_down(tmp_path, capsys):
    # formula: clip(1 - 0.24/0.32, 0, 0.6) = 0.25
    out = _fails(capsys, _write(tmp_path, _manifest(dropout=0.10, serve_rate=_probes(p_drop=0.10))), "GATE-D",
                 expected_dropout=0.10)
    assert "below clip" in out and "more inbound coverage than was measured" in out
    assert _run(_write(tmp_path, _manifest(dropout=0.21, serve_rate=_probes(p_drop=0.21))),
                expected_dropout=0.21) == 0              # 0.04 under the formula is inside the tolerance
    assert _run(_write(tmp_path, _manifest(dropout=0.50, serve_rate=_probes(p_drop=0.50))),
                expected_dropout=0.50) == 0              # rounding the dropout UP is always allowed


def test_shipped_dropout_must_equal_the_probe_derived_p_drop(tmp_path, capsys):
    """Both numbers are in the MANIFEST; training with one and recording the other is the failure this catches."""
    out = _fails(capsys, _write(tmp_path, _manifest(dropout=0.30, serve_rate=_probes(p_drop=0.25))), "GATE-D",
                 expected_dropout=0.30)
    assert "does not match the probe-derived p_drop" in out
