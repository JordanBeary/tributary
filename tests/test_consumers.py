"""The consumer engine must reproduce the Section 1 QA gates from the artifact alone.

Same philosophy as test_waterfall.py: the calibration lives entirely in
lendingclub_marginals.json, so the production engine — fed nothing but that
artifact — must land inside the gates 01_lendingclub.ipynb passed. The KS
reference here is a fresh inverse-CDF sample from the artifact's own quantile
tables (the notebook's raw held-out samples need the multi-GB downloads, which
tests must not require); that verifies the sampler is faithful to the fitted
distribution the notebook already gated against the source.

Also asserted: the duplicate-injection structure (design Section 2.3, C7 mix)
that the ER pipeline will later be scored against.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from simulation.config import SimConfig
from simulation.consumers import (
    CORRUPTION_PROBS, CORRUPTIONS, FICO_BANDS, FICO_EDGES,
    CreditModel, IdentityVocab, build_population,
)
from simulation.stages import generate_consumers

SEED = 202608
N = 150_000  # 10% scale: enough resolution for the ±1pp categorical gate
DUP_RATE = 0.08


@pytest.fixture(scope="module")
def model():
    return CreditModel.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def vocab():
    return IdentityVocab.from_faker()


@pytest.fixture(scope="module")
def pop(model, vocab):
    return build_population(model, vocab, N, DUP_RATE,
                            np.random.default_rng(SEED))


@pytest.fixture(scope="module")
def base(pop):
    """Distinct persons only — duplicates copy credit rows and would double-count."""
    return pop[~pop.is_duplicate]


def test_ks_gate(model, base):
    """C4: KS distance < 0.05 per numeric marginal vs the artifact's table."""
    ref_rng = np.random.default_rng(7)
    sim = base.assign(annual_inc_log=np.log(base["annual_inc"]))
    for name, table in model.quantiles.items():
        col = "annual_inc_log" if name == "annual_inc_log" else name
        ref = np.interp(ref_rng.uniform(size=200_000), model.probs, table)
        ks = stats.ks_2samp(sim[col].to_numpy(), ref).statistic
        assert ks < 0.05, f"KS({name}) = {ks:.4f}"


def test_categorical_gate(model, base):
    """C4: categorical mixes within ±1pp — including the derived fico_band."""
    import json
    p = json.loads(open("simulation/params/lendingclub_marginals.json").read())
    for cat in ("purpose", "addr_state", "emp_length", "fico_band"):
        target = pd.Series(p["categoricals"][cat], dtype=float)
        if cat == "emp_length":  # simulated mix excludes n/a by construction
            target = target.drop("n/a")
            target = target / target.sum()
        got = base[cat].value_counts(normalize=True).reindex(target.index,
                                                             fill_value=0.0)
        err = float((got - target).abs().max())
        assert err < 0.01, f"{cat} mix off by {err:.4f}"


def test_copula_gate(model, base):
    """C4: max |simulated Spearman - artifact Spearman| < 0.1."""
    import json
    target = np.array(json.loads(
        open("simulation/params/lendingclub_marginals.json").read()
    )["copula"]["spearman"])
    sim = base.assign(annual_inc_log=np.log(base["annual_inc"]))
    simc = sim[["loan_amnt", "dti", "annual_inc_log", "fico_mid", "emp_years"]]
    err = float(np.abs(simc.corr(method="spearman").to_numpy() - target).max())
    assert err < 0.1, f"copula corr max abs err = {err:.4f}"


def test_fico_band_coherent(pop):
    """Every row's band agrees with its score — the divergence from the
    notebook's independent draw is what buys this invariant."""
    derived = FICO_BANDS[np.digitize(pop["fico_mid"], FICO_EDGES)]
    assert (pop["fico_band"].to_numpy() == derived).all()


def test_duplicate_structure(pop, base):
    """Exactly n records; ~duplicate_rate duplicates; every duplicate shares a
    base person's consumer_key and copies the credit profile verbatim."""
    dups = pop[pop.is_duplicate]
    assert len(pop) == N
    assert len(dups) == round(N * DUP_RATE)
    assert pop["consumer_record_id"].is_unique
    assert dups["consumer_key"].isin(set(base["consumer_key"])).all()

    merged = dups.merge(base, on="consumer_key", suffixes=("", "_b"))
    assert len(merged) == len(dups)
    for col in ("loan_amnt", "dti", "annual_inc", "fico_mid", "emp_length",
                "purpose", "addr_state", "last_name", "street_address",
                "city", "zip_code"):
        assert (merged[col] == merged[f"{col}_b"]).all(), f"{col} not copied"


def test_corruption_semantics(pop, base):
    """C7: each corruption kind changes exactly the fields it names."""
    merged = pop[pop.is_duplicate].merge(base, on="consumer_key",
                                         suffixes=("", "_b"))
    changed = {f: merged[f] != merged[f"{f}_b"]
               for f in ("first_name", "email", "phone")}
    kind = merged["corruption"]
    assert (changed["first_name"] == kind.isin(["nickname", "all"])).all()
    assert (changed["email"] == kind.isin(["email_typo", "all"])).all()
    assert (changed["phone"] == kind.isin(["new_phone", "all"])).all()

    # Mix lands near the C7 dial (binomial noise at n=12k is well under 2pp)
    mix = kind.value_counts(normalize=True).reindex(CORRUPTIONS).to_numpy()
    assert np.abs(mix - CORRUPTION_PROBS).max() < 0.02


def test_identity_coherence(vocab, pop, base):
    """Emails well-formed and unique across persons; zips in-state; phones NANP-shaped."""
    assert base["email"].is_unique
    assert pop["email"].str.match(r"^[a-z0-9.]+@[a-z]+\.[a-z]+$").all()
    assert pop["phone"].str.match(r"^[2-9]\d{2}-[2-9]\d{2}-\d{4}$").all()
    lo = pop["addr_state"].map(vocab.zip_lo)
    hi = pop["addr_state"].map(vocab.zip_hi)
    z = pop["zip_code"].astype(int)
    assert ((z >= lo) & (z <= hi)).all()


def test_determinism(model, vocab):
    """Same seed, same population — the reproducibility exit criterion in miniature."""
    a = build_population(model, vocab, 5_000, DUP_RATE, np.random.default_rng(11))
    b = build_population(model, vocab, 5_000, DUP_RATE, np.random.default_rng(11))
    pd.testing.assert_frame_equal(a, b)


def test_stage_writes_parquet(tmp_path):
    """The stage contract end to end at toy scale: file written, key present."""
    cfg = SimConfig(seed=7, scale=0.0002, out_dir=tmp_path,
                    private_dir=tmp_path / "private")
    cfg.ensure_dirs()
    generate_consumers(cfg)
    df = pd.read_parquet(tmp_path / "consumers.parquet")
    assert len(df) == cfg.n_consumers
    assert {"consumer_record_id", "consumer_key", "email", "fico_mid"} <= set(df.columns)
