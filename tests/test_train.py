"""hkia.train: the inbound dropout mask — the one training-time transform that has to reproduce serve-time exactly."""
import numpy as np
import pandas as pd
import pytest

from hkia.features import FEATURES, INBOUND

pytest.importorskip("xgboost")
from hkia import train as T  # noqa: E402


def _split(n: int = 200, known: float = 0.5, seed: int = 7) -> pd.DataFrame:
    """A split-shaped frame: the inbound block plus enough label / identity columns to prove nothing else moves."""
    rng = np.random.default_rng(seed)
    k = (rng.random(n) < known).astype(int)
    return pd.DataFrame({
        "date": "2026-06-01", "flight_no": [f"CX {i}" for i in range(n)],
        "airline": "CPA", "sched_hour": rng.integers(0, 24, n),
        "delay_min": rng.normal(10, 20, n), "delayed15": rng.integers(0, 2, n).astype(float),
        "inbound_known": k,
        "inbound_actual_slack_min": np.where(k == 1, rng.uniform(30, 600, n), np.nan),
        "inbound_lateness_min": np.where(k == 1, rng.normal(0, 20, n), np.nan),
        "inbound_sched_slack_min": np.where(k == 1, rng.uniform(30, 600, n), np.nan),
        "inbound_confidence": np.where(k == 1, 1.0, np.nan),
    })


def test_mask_inbound_rate_zero_is_the_identity():
    df = _split()
    out = T.mask_inbound(df, 0.0, seed=3)
    pd.testing.assert_frame_equal(out, df)
    out.loc[0, "inbound_known"] = 99                       # ... and a copy, so the caller's frame is never mutated
    assert df.loc[0, "inbound_known"] != 99


def test_mask_inbound_rate_one_flips_every_linked_row_into_the_serve_encoding():
    df = _split()
    was_known = df["inbound_known"] == 1
    out = T.mask_inbound(df, 1.0, seed=0)
    assert was_known.any() and (out["inbound_known"] == 0).all()
    assert out.loc[was_known, T.INBOUND_VALUE].isna().all().all()
    # rows that never had a link are untouched — they were already in exactly this encoding
    pd.testing.assert_frame_equal(out.loc[~was_known], df.loc[~was_known])
    assert T.INBOUND_VALUE == [f for f in INBOUND if f != "inbound_known"]


def test_mask_inbound_is_deterministic_per_seed_and_touches_nothing_else():
    df = _split()
    a, b, c = (T.mask_inbound(df, 0.4, seed=s) for s in (1, 1, 2))
    pd.testing.assert_frame_equal(a, b)
    assert not a["inbound_known"].equals(c["inbound_known"])
    flipped = (df["inbound_known"] == 1) & (a["inbound_known"] == 0)
    assert 0 < flipped.sum() < (df["inbound_known"] == 1).sum()      # a share, not all and not none
    assert a.loc[flipped, T.INBOUND_VALUE].isna().all().all()
    # everything outside the inbound block — labels included — is byte-identical
    other = [c_ for c_ in df.columns if c_ not in INBOUND]
    pd.testing.assert_frame_equal(a[other], df[other])
    # the masked rate lands near the requested one (i.i.d. draw, 200 rows)
    kept = a["inbound_known"].sum() / df["inbound_known"].sum()
    assert 0.45 < kept < 0.75


def test_mask_inbound_never_invents_a_link():
    """The mask only removes: a row the model would not have at serving time must not gain one here."""
    df = _split(known=0.0)
    out = T.mask_inbound(df, 1.0, seed=0)
    assert (out["inbound_known"] == 0).all() and out[T.INBOUND_VALUE].isna().all().all()


def test_split_seeds_are_distinct_and_the_ablation_knows_the_inbound_block():
    assert sorted(T.SPLIT_SEED) == ["test", "train", "val"] and len(set(T.SPLIT_SEED.values())) == 3
    assert [f for f in FEATURES if f not in INBOUND] == FEATURES[:-5]
    assert T.PAIRED == ("full", "no_inbound")
