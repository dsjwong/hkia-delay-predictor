#!/usr/bin/env python
"""Non-inferiority gate for the weekly retrain: ship the candidate only if it is not worse than the shipped model.

Both models are scored on the candidate's own held-out test window (the last 15 % of dates, never seen in the candidate's
fit and later than anything the shipped model was trained on), with the exact serve-time inbound mask `hkia.train` used.
The shipped model is scored the way it serves: raw booster -> its calibrator (identity if it has none).

A strict-superiority gate would almost never pass on ~3-4 weeks of test data, so the question asked is the one that matters
for a weekly refresh -- "is the new model at least as good, within a stated margin?" -- answered with a paired bootstrap
over flights (both models on the same resample), on the difference candidate - current:

    R1  ΔAUC     95 % CI lower bound  > -0.01     (ranking not meaningfully worse)
    R2  ΔMAE     95 % CI upper bound  < +0.30 min (delay minutes not meaningfully worse)
    R3  Δlogloss 95 % CI upper bound  < +0.01     (probabilities, i.e. calibration + sharpness, not meaningfully worse)
    R5  no-inbound sanity: on test rows with NO inbound link known the candidate's mean probability is within
        MAX_UNKNOWN_BIAS of the observed late rate -- the "no inbound yet reads as trouble" failure the one-off inbound
        GATE-C was written for, checked against the label instead of against the shipped model, because a retrained
        model may legitimately move the level. NOT a day-ahead check: those test rows still carry same-day rolling
        stats and as-of weather, which true day-ahead rows (scored the evening before) do not
    R6  day-ahead as-of backtest on the most recent ASOF_DAYS complete days of departed flights (`hkia.asof`: each day
        scored at noon HKT the day before, later actuals blanked, same flights for both models): the candidate must not
        be SEPARABLY worse than the shipped model -- ΔAUC 95 % CI entirely below 0, or Δlog loss 95 % CI entirely
        above 0, blocks the ship. Added after the 2026-11-01 refit, whose live AUC looked worse than its predecessor's
        only because the two had been scored on different days. Not evaluable (too few rows, no db) = no verdict
    R4  the test window has >= MIN_TEST rows and the candidate MANIFEST records a leak-free build with the same inbound
        dropout the shipped model was trained under (links rebuilt from scheduled times; no silent change of the recipe)

Exit 0 and `SHIP` only if all pass; otherwise exit 1 and `HOLD` with the failing gate(s). Always writes --out (JSON) so the
numbers survive a HOLD.

    PYTHONPATH=src python scripts/retrain_gate.py --features data/features.parquet --current models \\
        --candidate models.cand --out reports/retrain-gate.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

MIN_D_AUC = -0.01
MAX_D_MAE = 0.30
MAX_D_LOGLOSS = 0.01
MAX_UNKNOWN_BIAS = 0.03
MIN_TEST = 2000
ASOF_DAYS = 7
MIN_ASOF = 1000
N_BOOT = 2000


def _auc(y, p) -> float:
    from hkia.evaluate import _auc_np
    return float(_auc_np(y, p))


def _ll(y, p) -> float:
    from hkia.calibrate import logloss
    return logloss(y, p)


def paired_deltas(y, r, cand, cur, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Point estimates and 95 % bootstrap CIs of candidate - current for AUC, MAE, log loss.
    `cand` / `cur` = (probabilities, predicted minutes). Rows are resampled jointly, so the CI is on the difference."""
    y, r = np.asarray(y), np.asarray(r, dtype=float)
    n = len(y)
    ae_c, ae_u = np.abs(r - cand[1]), np.abs(r - cur[1])
    pc, pu = np.clip(cand[0], 1e-6, 1 - 1e-6), np.clip(cur[0], 1e-6, 1 - 1e-6)
    nll_c = -(y * np.log(pc) + (1 - y) * np.log(1 - pc))
    nll_u = -(y * np.log(pu) + (1 - y) * np.log(1 - pu))
    rng = np.random.default_rng(seed)
    d_auc, d_mae, d_ll = (np.empty(n_boot) for _ in range(3))
    for i in range(n_boot):
        s = rng.integers(0, n, n)
        d_auc[i] = _auc(y[s], cand[0][s]) - _auc(y[s], cur[0][s])
        d_mae[i] = ae_c[s].mean() - ae_u[s].mean()
        d_ll[i] = nll_c[s].mean() - nll_u[s].mean()
    out = {"n": int(n), "n_boot": n_boot,
           "candidate": {"auc": _auc(y, cand[0]), "mae": float(ae_c.mean()), "logloss": float(nll_c.mean())},
           "current": {"auc": _auc(y, cur[0]), "mae": float(ae_u.mean()), "logloss": float(nll_u.mean())}}
    for k, v in (("d_auc", d_auc), ("d_mae", d_mae), ("d_logloss", d_ll)):
        v = v[np.isfinite(v)]
        lo, hi = np.percentile(v, [2.5, 97.5])
        out[k] = {"ci": [float(lo), float(hi)]}
    out["d_auc"]["point"] = out["candidate"]["auc"] - out["current"]["auc"]
    out["d_mae"]["point"] = out["candidate"]["mae"] - out["current"]["mae"]
    out["d_logloss"]["point"] = out["candidate"]["logloss"] - out["current"]["logloss"]
    return out


def decide(res: dict, cand_manifest: dict, cur_manifest: dict, min_test: int = MIN_TEST) -> dict:
    """Apply R1-R4 to `paired_deltas` output. Returns {"ship": bool, "checks": [{gate, ok, detail}]}."""
    checks = []

    def add(gate, ok, detail):
        checks.append({"gate": gate, "ok": bool(ok), "detail": detail})

    lo = res["d_auc"]["ci"][0]
    add("R1", lo > MIN_D_AUC, f"ΔAUC {res['d_auc']['point']:+.4f}, 95 % CI lower bound {lo:+.4f} (need > {MIN_D_AUC})")
    hi = res["d_mae"]["ci"][1]
    add("R2", hi < MAX_D_MAE, f"ΔMAE {res['d_mae']['point']:+.3f} min, 95 % CI upper bound {hi:+.3f} (need < {MAX_D_MAE})")
    hi = res["d_logloss"]["ci"][1]
    add("R3", hi < MAX_D_LOGLOSS,
        f"Δlog loss {res['d_logloss']['point']:+.4f}, 95 % CI upper bound {hi:+.4f} (need < {MAX_D_LOGLOSS})")
    inb, cur_inb = cand_manifest.get("inbound", {}), cur_manifest.get("inbound", {})
    problems = []
    if res["n"] < min_test:
        problems.append(f"only {res['n']} test rows (< {min_test})")
    if inb.get("links_event_source") != "sched":
        problems.append(f"links_event_source = {inb.get('links_event_source')!r}, not 'sched' (leaky inbound links)")
    if inb.get("inbound_dropout") != cur_inb.get("inbound_dropout"):
        problems.append(f"inbound_dropout {inb.get('inbound_dropout')} != shipped {cur_inb.get('inbound_dropout')}")
    if cand_manifest.get("features") != cur_manifest.get("features"):
        problems.append("feature list differs from the shipped model (a schema change is not a weekly refresh)")
    iu = res.get("inbound_unknown")
    if iu:
        bias = iu["candidate_mean_p"] - iu["observed_rate"]
        add("R5", abs(bias) < MAX_UNKNOWN_BIAS, f"no-inbound rows (n={iu['n']}): mean P {iu['candidate_mean_p']:.3f} vs observed "
            f"{iu['observed_rate']:.3f}, bias {bias:+.3f} (need |bias| < {MAX_UNKNOWN_BIAS}); shipped model {iu['current_mean_p']:.3f}")
    asof = res.get("asof")
    if asof is not None:
        if asof.get("skipped"):
            add("R6", True, f"day-ahead as-of backtest not evaluated: {asof['skipped']}")
        else:
            a_hi, l_lo = asof["d_auc"]["ci"][1], asof["d_logloss"]["ci"][0]
            add("R6", not (a_hi < 0 or l_lo > 0),
                f"day-ahead as-of, {asof['dates'][0]}..{asof['dates'][-1]} (n={asof['n']}): ΔAUC {asof['d_auc']['point']:+.4f} "
                f"[{asof['d_auc']['ci'][0]:+.4f}, {a_hi:+.4f}], Δlog loss {asof['d_logloss']['point']:+.4f} "
                f"[{l_lo:+.4f}, {asof['d_logloss']['ci'][1]:+.4f}], ΔMAE {asof['d_mae']['point']:+.3f} min "
                f"(blocks only if the AUC CI is entirely < 0 or the log loss CI entirely > 0)")
    add("R4", not problems, "; ".join(problems) or f"{res['n']} test rows, links 'sched', dropout {inb.get('inbound_dropout')}, same features")
    return {"ship": all(c["ok"] for c in checks), "checks": checks}


def score_model(models_dir: Path, test) -> tuple[np.ndarray, np.ndarray]:
    """(served probability, predicted minutes) of a models/ directory on `test` (already masked)."""
    import joblib

    from hkia.calibrate import load_calibrator
    from hkia.train import to_matrix
    clf = joblib.load(models_dir / "xgb_delayed15.joblib")
    reg = joblib.load(models_dir / "xgb_delay_min.joblib")
    X, _ = to_matrix(test, clf["cats"], clf["features"])
    Xr, _ = to_matrix(test, reg["cats"], reg["features"])
    return load_calibrator(models_dir).predict(clf["model"].predict_proba(X)[:, 1]), reg["model"].predict(Xr)


def asof_deltas(current: Path, candidate: Path, cur_m: dict, cand_m: dict, days: int = ASOF_DAYS, n_boot: int = N_BOOT,
                min_rows: int = MIN_ASOF) -> dict:
    """Candidate - current on the last `days` complete days, day-ahead as-of scoring of both on the same flights.
    Days up to the end of either model's calibration fold are excluded (not held out)."""
    import joblib

    from hkia import asof
    from hkia.db import connect
    try:
        conn = connect()
        inp = asof.load_inputs(conn)
    except Exception as e:  # noqa: BLE001 -- no db / no table: report, never crash the gate
        return {"skipped": f"database unavailable ({type(e).__name__})"}
    after = max(m.get("split", {}).get("cal", {}).get("date_max", "") for m in (cur_m, cand_m)) or None
    dates = asof.recent_complete_dates(inp.flights, days, after=after)
    if not dates:
        return {"skipped": f"no complete held-out day after {after}"}
    top = set()
    for d in (current, candidate):
        top |= set(joblib.load(d / "xgb_delayed15.joblib")["cats"]["dest"].categories)
    long = asof.score_day_ahead(inp, dates, {"cand": candidate, "cur": current}, top - {"OTHER"})
    long = long[long["predictor"].isin(["cand", "cur"])]
    p = long.pivot_table(index=asof.KEY, columns="predictor", values="p")
    m = long.pivot_table(index=asof.KEY, columns="predictor", values="minutes")
    lab = long.drop_duplicates(asof.KEY).set_index(asof.KEY)[["delayed15", "delay_min"]].reindex(p.index)
    if len(p) < min_rows:
        return {"skipped": f"only {len(p)} flights on {dates[0]}..{dates[-1]} (< {min_rows})"}
    res = paired_deltas(lab["delayed15"].to_numpy(), lab["delay_min"].to_numpy(),
                        (p["cand"].to_numpy(), m["cand"].to_numpy()), (p["cur"].to_numpy(), m["cur"].to_numpy()), n_boot)
    return {**res, "dates": dates}


def run(features: Path, current: Path, candidate: Path, n_boot: int = N_BOOT, asof_days: int = 0) -> dict:
    import pandas as pd

    from hkia import train as T
    cur_m = json.loads((current / "MANIFEST.json").read_text())
    cand_m = json.loads((candidate / "MANIFEST.json").read_text())
    inb = cand_m["inbound"]
    raw = T.carve_calibration(T.time_split(T.modelling_frame(pd.read_parquet(features))))
    test = T.mask_inbound(raw["test"], inb["inbound_dropout"], inb["mask_seed"] + T.SPLIT_SEED["test"])
    y = test["delayed15"].astype(int).to_numpy()
    r = test["delay_min"].to_numpy(dtype=float)
    cand, cur = score_model(candidate, test), score_model(current, test)
    res = paired_deltas(y, r, cand, cur, n_boot)
    unk = (test["inbound_known"] == 0).to_numpy()
    if unk.any():
        res["inbound_unknown"] = {"n": int(unk.sum()), "observed_rate": float(y[unk].mean()),
                                  "candidate_mean_p": float(cand[0][unk].mean()), "current_mean_p": float(cur[0][unk].mean())}
    if asof_days:
        res["asof"] = asof_deltas(current, candidate, cur_m, cand_m, asof_days, n_boot)
    res["test_window"] = [str(test["date"].min()), str(test["date"].max())]
    res["current_model"] = f"{cur_m.get('git_sha')}@{cur_m.get('created_at')}"
    res["candidate_model"] = f"{cand_m.get('git_sha')}@{cand_m.get('created_at')}"
    res["current_calibrator"] = "calibrator_delayed15.json" if (current / "calibrator_delayed15.json").exists() else "none"
    return {**res, **decide(res, cand_m, cur_m)}


def render(rep: dict) -> str:
    c, u = rep["candidate"], rep["current"]
    lines = [f"retrain gate on test window {rep['test_window'][0]}..{rep['test_window'][1]} (n={rep['n']}): "
             f"candidate {rep['candidate_model']} vs current {rep['current_model']} (current calibrator: {rep['current_calibrator']})",
             f"  AUC     {c['auc']:.4f} vs {u['auc']:.4f}", f"  MAE     {c['mae']:.3f} vs {u['mae']:.3f}",
             f"  logloss {c['logloss']:.4f} vs {u['logloss']:.4f}"]
    lines += [f"  {'pass' if k['ok'] else 'FAIL'} {k['gate']}: {k['detail']}" for k in rep["checks"]]
    if rep.get("asof") and not rep["asof"].get("skipped"):
        a = rep["asof"]
        lines.insert(4, f"  day-ahead as-of {a['dates'][0]}..{a['dates'][-1]} (n={a['n']}): AUC {a['candidate']['auc']:.4f} vs "
                        f"{a['current']['auc']:.4f}, logloss {a['candidate']['logloss']:.4f} vs {a['current']['logloss']:.4f}, "
                        f"MAE {a['candidate']['mae']:.3f} vs {a['current']['mae']:.3f}")
    lines.append("SHIP" if rep["ship"] else "HOLD: " + ", ".join(k["gate"] for k in rep["checks"] if not k["ok"]))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", required=True)
    ap.add_argument("--current", default="models")
    ap.add_argument("--candidate", default="models.cand")
    ap.add_argument("--out", help="write the full report JSON here")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--asof-days", type=int, default=0,
                    help="also run R6, the day-ahead as-of backtest over the last N complete days (needs the db; 0 = off)")
    a = ap.parse_args(argv)
    rep = run(Path(a.features), Path(a.current), Path(a.candidate), a.n_boot, a.asof_days)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=2))
    print(render(rep))
    return 0 if rep["ship"] else 1


if __name__ == "__main__":
    sys.exit(main())
