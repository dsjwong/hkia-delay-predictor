#!/usr/bin/env python
"""Ship gate for the inbound (turnaround) feature block: pass/fail, not a table to eyeball.

Exits 0 only if every check passes; on the first failure it prints one line saying which gate failed and why, and
exits 1. Nothing here is advisory -- if it fails, the candidate models do not ship.

    GATE-A  the 95 % CI (paired bootstrap, test-mask seed 0) on ΔAUC = AUC(full) - AUC(no_inbound) is entirely > 0
    GATE-B  mean MAE(full) over the 5 test-mask seeds is no worse than mean MAE(no_inbound)
    GATE-C  day-ahead drift: mean p_delay15 in the > 12 h horizon bucket does not rise by more than +0.02 absolute
            against the currently deployed models, scored on the same scratch db
    GATE-D  the candidate MANIFEST records a leak-free build: links_event_source == "sched", the expected
            --inbound-dropout, a known_rate per split, the no_inbound ablation row, and the sensitivity row --
            plus the dropout rate RE-DERIVED from the recorded probe data (see below), not taken on trust

The dropout re-derivation matters: `--expected-dropout` and `MANIFEST.inbound.inbound_dropout` are both typed by the
same operator, so checking one against the other proves only that they typed it twice. The probes recorded in
`MANIFEST.inbound.serve_rate` (from `hkia.train --serve-rate-json`, stored verbatim) are measurements, so the gate
recomputes p_drop from them and fails if the shipped number does not follow. Expected shape:

    {"probes": [{"probe_utc": "2026-08-24T02:00:00+00:00", "n": 480, "rate": 0.21, ...per-horizon sub-objects...},
                ...],
     "r_serve": 0.23, "r_train": 0.32, "p_drop": 0.28, "rule": "clip(1 - r_serve/r_train, 0, 0.6)"}

and the checks on it are:

    (a) at least 2 probes recorded `n` > 0 and their `probe_utc` timestamps span >= 6 h (one snapshot is not a
        coverage measurement -- inbound coverage swings with the rotations cron and the time of day). Probes with
        `n` == 0 measured nothing and are ignored throughout, not counted as zero coverage
    (b) pooled n = sum of the non-empty probes' `n`; if that is < 200, the recorded `r_serve` must be <= the MINIMUM
        of their rates (the "take the lower end when thin" rule -- under-estimating serve coverage is the safe side)
    (c) |clip(1 - r_serve/r_train, 0, 0.6) - recorded p_drop| <= 0.05, OR the recorded p_drop is HIGHER than the
        formula (rounding the dropout up is always allowed: it trains for less inbound coverage than measured)
    (d) MANIFEST.inbound.inbound_dropout == the recorded p_drop

(The names are GATE-A..D on purpose. An earlier, unrelated gate in this project used G1-G4; do not conflate them.)

Usage
-----
GATE-A/B/D read the candidate MANIFEST.json alone:

    .venv/bin/python scripts/inbound_gate.py --manifest models.cand/MANIFEST.json --expected-dropout 0.30

GATE-C needs two scoring summaries produced by running `hkia.predict` twice over the SAME scratch database -- once
with the deployed models, once with the candidate ones -- so the only thing that differs is the model:

    cp data/hkia.db /tmp/gate.db
    HKIA_DB=/tmp/gate.db .venv/bin/python -m hkia.predict --models models \\
        --no-dedupe --summary-json /tmp/gate-current.json
    HKIA_DB=/tmp/gate.db .venv/bin/python -m hkia.predict --models models.cand \\
        --no-dedupe --summary-json /tmp/gate-candidate.json
    .venv/bin/python scripts/inbound_gate.py --manifest models.cand/MANIFEST.json --expected-dropout 0.30 \\
        --current-predict-json /tmp/gate-current.json --candidate-predict-json /tmp/gate-candidate.json

Why GATE-C exists: the inbound block is knowable only inside ~2 h of departure, so day-ahead rows all score with
inbound_known = 0. A model that reads "no inbound on stand" as "trouble" instead of "nothing known yet" would quietly
raise every tomorrow-flight probability -- invisible in the test metrics, obvious here.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

MAX_P_DRIFT = 0.02          # GATE-C: absolute rise allowed in the > 12 h bucket mean p_delay15
DRIFT_BUCKET = ">12h"
REQUIRED_SPLITS = ("train", "val", "test")
MIN_PROBE_SPAN_H = 6.0      # GATE-D(a): non-empty probes must cover at least this many hours
MIN_LIVE_PROBES = 2         # GATE-D(a): ... and there must be at least this many of them
THIN_POOLED_N = 200         # GATE-D(b): below this pooled n, r_serve must take the lowest probe rate
P_DROP_TOL = 0.05           # GATE-D(c): allowed shortfall of the shipped p_drop against the formula
P_DROP_MAX = 0.6            # the clip in the dropout rule


def fail(gate: str, reason: str) -> None:
    print(f"FAIL {gate}: {reason}")
    sys.exit(1)


def load(path: str | None, what: str) -> dict | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        fail("GATE-input", f"{what} not found: {p}")
    try:
        return json.loads(p.read_text())
    except ValueError as e:
        fail("GATE-input", f"{what} is not readable JSON ({p}): {e}")
    return None


def gate_a(gate: dict) -> None:
    ci = (gate.get("ci_test_seed_0") or {}).get("d_auc")
    if not ci or len(ci) != 2:
        fail("GATE-A", "MANIFEST.inbound_gate has no ΔAUC bootstrap CI at test seed 0")
    lo, hi = ci
    seeds = [p["d_auc"] for p in gate.get("per_seed", [])]
    spread = f"per-seed ΔAUC {seeds} (spread {max(seeds) - min(seeds):+.4f})" if seeds else "no per-seed ΔAUC recorded"
    if lo <= 0:
        fail("GATE-A", f"ΔAUC 95 % CI [{lo:+.5f}, {hi:+.5f}] includes 0 — the inbound block is not separable "
                       f"from noise on this test split; {spread}")
    print(f"pass GATE-A: ΔAUC 95 % CI [{lo:+.5f}, {hi:+.5f}] entirely above 0; {spread}")


def gate_b(gate: dict) -> None:
    m = gate.get("mean") or {}
    full, none = m.get("mae_full"), m.get("mae_no_inbound")
    if full is None or none is None:
        fail("GATE-B", "MANIFEST.inbound_gate.mean has no mae_full / mae_no_inbound")
    n = gate.get("n_test_seeds")
    if full > none:
        fail("GATE-B", f"mean MAE over {n} test-mask seeds is worse with the inbound block: "
                       f"{full:.4f} vs {none:.4f} ({full - none:+.4f} min)")
    print(f"pass GATE-B: mean MAE over {n} test-mask seeds {full:.4f} (full) <= {none:.4f} (no_inbound), "
          f"{full - none:+.4f} min")


def gate_c(current: dict | None, candidate: dict | None) -> None:
    if current is None or candidate is None:
        fail("GATE-C", "day-ahead drift not checked — pass --current-predict-json and --candidate-predict-json "
                       "(see this script's docstring for the two exact predict commands)")
    cur_b = (current.get("horizon") or {}).get(DRIFT_BUCKET) or {}
    can_b = (candidate.get("horizon") or {}).get(DRIFT_BUCKET) or {}
    if cur_b.get("p_mean") is None or can_b.get("p_mean") is None:
        fail("GATE-C", f"no flights in the {DRIFT_BUCKET} horizon bucket in one of the two summaries "
                       f"(n={cur_b.get('n')} current, n={can_b.get('n')} candidate) — score a scratch db that "
                       f"contains tomorrow's schedule")
    d = can_b["p_mean"] - cur_b["p_mean"]
    if d > MAX_P_DRIFT:
        fail("GATE-C", f"day-ahead mean p_delay15 rises {d:+.4f} in the {DRIFT_BUCKET} bucket "
                       f"({cur_b['p_mean']:.4f} -> {can_b['p_mean']:.4f}, n={can_b['n']}), over the "
                       f"+{MAX_P_DRIFT} limit — the candidate reads 'no inbound known yet' as 'late'")
    print(f"pass GATE-C: day-ahead mean p_delay15 {cur_b['p_mean']:.4f} -> {can_b['p_mean']:.4f} ({d:+.4f}, "
          f"n={can_b['n']}, limit +{MAX_P_DRIFT})")


def _num(v, field: str):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        fail("GATE-D", f"serve_rate.{field} is {v!r}, not a number — the probe file did not record a measured rate")
    return float(v)


def gate_d_probes(inb: dict, dropout) -> None:
    """Re-derive the dropout rate from the recorded probes instead of trusting the number the operator typed."""
    sr = inb.get("serve_rate")
    if not sr:
        fail("GATE-D", "MANIFEST.inbound.serve_rate is empty — retrain with --serve-rate-json so the dropout rate "
                       "can be re-derived from measured serve-time coverage")
    probes = sr.get("probes") or []
    if not probes:
        fail("GATE-D", "serve_rate.probes is empty — p_drop cannot be checked against anything measured")
    try:
        stamps = {id(p): dt.datetime.fromisoformat(p["probe_utc"]) for p in probes}
    except (KeyError, TypeError, ValueError) as e:
        fail("GATE-D", f"serve_rate.probes has a bad or missing probe_utc: {e}")
    # a probe that saw no flights measured nothing: its rate is 0 by construction, and letting it into min(rates) or
    # the pooled n would drive r_serve to 0 and the dropout to the clip — fail-closed, but for the wrong reason
    live = [p for p in probes if int(p.get("n") or 0) > 0]
    if not live:
        fail("GATE-D", f"all {len(probes)} probe(s) in serve_rate recorded 0 flights — nothing was measured, so "
                       f"p_drop cannot be re-derived (probe during hours with departures on the schedule)")
    if len(live) < MIN_LIVE_PROBES:
        fail("GATE-D", f"only {len(live)} of {len(probes)} probe(s) saw any flights, under the {MIN_LIVE_PROBES} "
                       f"needed — one non-empty probe is a snapshot, not a coverage measurement")
    span_h = (max(stamps[id(p)] for p in live) - min(stamps[id(p)] for p in live)).total_seconds() / 3600
    if span_h < MIN_PROBE_SPAN_H:
        fail("GATE-D", f"the {len(live)} non-empty probe(s) span only {span_h:.1f} h, under the "
                       f"{MIN_PROBE_SPAN_H:g} h minimum — inbound coverage swings with the rotations cron and the "
                       f"time of day, so this is a snapshot, not a measurement")
    rates = [_num(p.get("rate"), "probes[].rate") for p in live]
    pooled_n = sum(int(p["n"]) for p in live)
    r_serve, r_train = _num(sr.get("r_serve"), "r_serve"), _num(sr.get("r_train"), "r_train")
    if pooled_n < THIN_POOLED_N and r_serve > min(rates) + 1e-9:
        fail("GATE-D", f"pooled probe n is {pooled_n} (< {THIN_POOLED_N}), so r_serve must take the lowest probe rate "
                       f"{min(rates):.4f}, but {r_serve:.4f} was recorded — on thin data the dropout has to be set "
                       f"from the low end of coverage, not the average")
    if r_train <= 0:
        fail("GATE-D", f"serve_rate.r_train is {r_train} — cannot re-derive p_drop")
    p_drop = _num(sr.get("p_drop"), "p_drop")
    derived = min(max(1 - r_serve / r_train, 0.0), P_DROP_MAX)
    if p_drop < derived - P_DROP_TOL:
        fail("GATE-D", f"recorded p_drop {p_drop:.4f} is below clip(1 - {r_serve:.4f}/{r_train:.4f}, 0, {P_DROP_MAX}) "
                       f"= {derived:.4f} by more than {P_DROP_TOL} — the model was trained for more inbound coverage "
                       f"than was measured at serving time")
    if dropout is None or abs(float(dropout) - p_drop) > 1e-9:
        fail("GATE-D", f"inbound_dropout {dropout!r} does not match the probe-derived p_drop {p_drop} recorded in "
                       f"serve_rate")
    skipped = len(probes) - len(live)
    print(f"pass GATE-D probes: {len(live)} non-empty probe(s) over {span_h:.1f} h"
          f"{f' ({skipped} zero-flight probe(s) ignored)' if skipped else ''}, pooled n={pooled_n}, "
          f"r_serve={r_serve}, r_train={r_train}, formula {derived:.4f} -> shipped p_drop {p_drop}")


def gate_d(manifest: dict, expected_dropout: float) -> None:
    inb = manifest.get("inbound") or {}
    src = inb.get("links_event_source")
    if src != "sched":
        fail("GATE-D", f"links_event_source is {src!r}, not 'sched' — the training links were paired on actual "
                       f"departure times, which depend on the label (rebuild with `rotations --events sched`)")
    got = inb.get("inbound_dropout")
    if got != expected_dropout:
        fail("GATE-D", f"inbound_dropout in the MANIFEST is {got!r}, expected {expected_dropout!r}")
    rates = inb.get("known_rate") or {}
    missing = [s for s in REQUIRED_SPLITS if rates.get(s) is None]
    if missing:
        fail("GATE-D", f"MANIFEST.inbound.known_rate is missing splits: {missing}")
    if "no_inbound" not in (manifest.get("ablation_test") or {}):
        fail("GATE-D", "MANIFEST.ablation_test has no `no_inbound` row")
    if not (manifest.get("inbound_gate") or {}).get("sensitivity"):
        fail("GATE-D", "MANIFEST.inbound_gate has no sensitivity row (refit at dropout + 0.10)")
    print(f"pass GATE-D: links_event_source=sched, inbound_dropout={got}, known_rate={rates}, "
          f"no_inbound + sensitivity rows present")
    gate_d_probes(inb, got)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, help="candidate models/MANIFEST.json")
    ap.add_argument("--expected-dropout", type=float, required=True, help="the --inbound-dropout the retrain used")
    ap.add_argument("--current-manifest", help="deployed models/MANIFEST.json (context only, no gate depends on it)")
    ap.add_argument("--current-predict-json", help="predict --summary-json written with the DEPLOYED models")
    ap.add_argument("--candidate-predict-json", help="predict --summary-json written with the CANDIDATE models")
    a = ap.parse_args(argv)

    manifest = load(a.manifest, "candidate MANIFEST")
    current_manifest = load(a.current_manifest, "current MANIFEST")
    gate = manifest.get("inbound_gate") or {}
    if not gate:
        fail("GATE-A", f"{a.manifest} has no `inbound_gate` block — it was not written by a train.py that "
                       f"evaluates the inbound block")
    print(f"candidate {a.manifest}: {len(manifest.get('features', []))} features, git {manifest.get('git_sha')}, "
          f"built {manifest.get('created_at')}")
    if current_manifest:
        print(f"deployed  {a.current_manifest}: {len(current_manifest.get('features', []))} features, "
              f"git {current_manifest.get('git_sha')}, built {current_manifest.get('created_at')}")
    gate_a(gate)
    gate_b(gate)
    gate_c(load(a.current_predict_json, "current predict summary"),
           load(a.candidate_predict_json, "candidate predict summary"))
    gate_d(manifest, a.expected_dropout)
    print("PASS: all gates (A-D) green — the inbound block may ship")
    return 0


if __name__ == "__main__":
    sys.exit(main())
