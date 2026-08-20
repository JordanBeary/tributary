"""The consumer engine must reproduce the Section 1 QA gates from the artifact alone.

Same philosophy as test_waterfall.py: the calibration lives entirely in
lendingclub_marginals.json, so the production engine — fed nothing but that
artifact — must land inside the gates 01_lendingclub.ipynb passed. The KS
reference here is a fresh inverse-CDF sample from the artifact's own quantile
tables (the notebook's raw held-out samples need the multi-GB downloads, which
tests must not require); that verifies the sampler is faithful to the fitted
distribution the notebook already gated against the source.

Also asserted: the identity-drift variant structure (C18, superseding the C7
one-shot duplicates) that the ER pipeline will later be scored against, and
the heavy-tailed repeat-application QA gates from repeat_applications.json.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from simulation.config import SimConfig
from simulation.consumers import (
    FICO_BANDS, FICO_EDGES, MUTATION_KINDS,
    CreditModel, IdentityVocab, build_population, load_repeat_pmf,
)
from simulation.stages import generate_consumers

SEED = 202608
N = 150_000  # enough persons for the ±1pp categorical gate
CFG = SimConfig()  # default dials (drift hazard, mutation probs)


@pytest.fixture(scope="module")
def model():
    return CreditModel.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def vocab():
    return IdentityVocab.from_faker()


@pytest.fixture(scope="module")
def pop(model, vocab):
    return build_population(model, vocab, N, CFG.marketing_only_rate,
                            CFG.drift_hazard, CFG.mutation_probs,
                            CFG.params_dir, np.random.default_rng(SEED))


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


def test_variant_structure(pop, base):
    """C18: one base record per person; drifted variants share the person's
    consumer_key, copy the credit profile verbatim, and n_apps sums to the
    person's application count with contiguous variant_seq."""
    assert len(base) == N
    assert pop["consumer_record_id"].is_unique
    variants = pop[pop.is_duplicate]
    assert (variants["variant_seq"] > 0).all()
    assert variants["consumer_key"].isin(set(base["consumer_key"])).all()

    merged = variants.merge(base, on="consumer_key", suffixes=("", "_b"))
    assert len(merged) == len(variants)
    for col in ("loan_amnt", "dti", "annual_inc", "fico_mid", "emp_length",
                "purpose", "addr_state"):
        assert (merged[col] == merged[f"{col}_b"]).all(), f"{col} not copied"

    # variant_seq contiguous 0..V-1 per person
    seqs = pop.sort_values("variant_seq").groupby("consumer_key")["variant_seq"]
    assert (seqs.min() == 0).all()
    assert (seqs.max() + 1 == seqs.count()).all()
    assert (pop["n_apps"] >= 1).all()


def test_repeat_count_gates(pop, base):
    """Per-person application counts reproduce the P-010 artifact's rounded
    QA targets (binomial noise at n=150k is far under the 1pp slack)."""
    import json
    art = json.loads((Path("simulation/params") /
                      "repeat_applications.json").read_text())
    k = pop.groupby("consumer_key")["n_apps"].sum()
    tgt = art["qa_targets_2sf"]
    share = k.value_counts(normalize=True)
    assert abs(share.get(1, 0) - tgt["p1"]) < 0.01
    assert abs(share.get(2, 0) - tgt["p2"]) < 0.01
    assert abs(share.get(3, 0) - tgt["p3"]) < 0.01
    assert abs(share[share.index <= 10].sum() - tgt["mass_le_10"]) < 0.01
    assert abs(k.mean() - tgt["mean"]) < 0.15
    assert k.max() <= art["cap"]


def test_drift_mutation_semantics(pop):
    """C18: each drift event's kinds change the fields they name, measured
    against the person's *previous* variant (mutations compose)."""
    cols = ["first_name", "last_name", "email", "phone", "zip_code",
            "street_address", "city"]
    s = pop.sort_values(["consumer_key", "variant_seq"])
    prev = s.groupby("consumer_key")[cols].shift(1)
    mask = s["variant_seq"] > 0
    kinds = s.loc[mask, "corruption"].str.split(",")
    changed = {c: (s.loc[mask, c] != prev.loc[mask, c]) for c in cols}

    has = {k: kinds.apply(lambda ks, k=k: k in ks) for k in MUTATION_KINDS}
    assert (changed["phone"] == has["new_phone"]).all()
    assert (changed["email"] == has["new_email"]).all()
    assert (changed["zip_code"] <= has["moved_zip"]).all()
    name_changed = changed["first_name"] | changed["last_name"]
    assert (name_changed == has["name_form"]).all()
    # every event mutates something
    assert kinds.str.len().ge(1).all()


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
    args = (CFG.marketing_only_rate, CFG.drift_hazard, CFG.mutation_probs,
            CFG.params_dir)
    a = build_population(model, vocab, 5_000, *args, np.random.default_rng(11))
    b = build_population(model, vocab, 5_000, *args, np.random.default_rng(11))
    pd.testing.assert_frame_equal(a, b)


def test_stage_writes_parquet(tmp_path):
    """The stage contract end to end at toy scale: file written, key present."""
    cfg = SimConfig(seed=7, scale=0.0002, out_dir=tmp_path,
                    private_dir=tmp_path / "private")
    cfg.ensure_dirs()
    generate_consumers(cfg)
    df = pd.read_parquet(tmp_path / "consumers.parquet")
    assert df["consumer_key"].nunique() == cfg.n_persons
    assert {"consumer_record_id", "consumer_key", "email", "fico_mid",
            "n_apps", "variant_seq", "acquisition_channel"} <= set(df.columns)
