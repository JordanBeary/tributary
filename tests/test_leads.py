"""Lead generation invariants, reproduced from the artifact alone.

Same philosophy as the sibling tests: the engine consumes only
lendingclub_marginals.json (via the consumer table it conditions on), so every
claim here — the C14 application mix, the C11 rank-q construction, amount and
timestamp semantics — is checkable without any raw-data download. Ends with the
first three-stage integration run: consumers -> leads -> waterfall.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from simulation.config import SimConfig
from simulation.consumers import CreditModel, IdentityVocab, build_population
from simulation.leads import (
    AMOUNT_MAX, AMOUNT_MIN, AMOUNT_STEP, APP_PROBS,
    QualityModel, build_leads,
)
from simulation.stages import generate_consumers, generate_leads, run_waterfall

SEED = 202608
N_CONSUMERS = 40_000
MONTHS = 12
WINDOW_START = "2025-07-01"


@pytest.fixture(scope="module")
def consumers():
    model = CreditModel.from_params_dir("simulation/params")
    vocab = IdentityVocab.from_faker()
    return build_population(model, vocab, N_CONSUMERS, 0.08,
                            np.random.default_rng(SEED))


@pytest.fixture(scope="module")
def qm():
    return QualityModel.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def leads(consumers, qm):
    return build_leads(consumers, qm, MONTHS, WINDOW_START,
                       np.random.default_rng(SEED + 1))


def test_volume_and_mix(consumers, leads):
    """C14: mean 1.60 applications per record; per-record counts follow the mix."""
    ratio = len(leads) / len(consumers)
    assert 1.55 < ratio < 1.65, f"leads per record = {ratio:.3f}"
    counts = leads.groupby("consumer_record_id").size()
    assert set(counts.unique()) <= {1, 2, 3}
    mix = counts.value_counts(normalize=True).reindex([1, 2, 3]).to_numpy()
    assert np.abs(mix - APP_PROBS).max() < 0.01, f"mix {np.round(mix, 3)}"


def test_q_is_rank_uniform(leads, qm):
    """C11: q is the within-cohort percentile rank of the fitted score —
    uniform on (0,1) and perfectly rank-aligned with the recomputed score."""
    z = qm.score(leads["loan_amnt"].to_numpy(), leads["dti"].to_numpy(),
                 leads["emp_years"].to_numpy())
    assert (leads["q"] > 0).all() and (leads["q"] < 1).all()
    assert stats.spearmanr(leads["q"], z).statistic > 0.9999
    ks = stats.ks_1samp(leads["q"], stats.uniform.cdf).statistic
    assert ks < 0.01, f"q not uniform: KS = {ks:.4f}"


def test_amount_semantics(consumers, leads):
    """First applications snap the consumer's anchor amount; repeats re-request
    with an upward-biased multiplier; everything on the $25 grid."""
    amt = leads["loan_amnt"]
    assert ((amt % AMOUNT_STEP == 0) & (amt >= AMOUNT_MIN)
            & (amt <= AMOUNT_MAX)).all()
    merged = leads.merge(
        consumers[["consumer_record_id", "loan_amnt"]].rename(
            columns={"loan_amnt": "anchor"}),
        on="consumer_record_id")
    first = merged[merged.app_seq == 1]
    snapped = np.clip(np.round(first["anchor"] / AMOUNT_STEP) * AMOUNT_STEP,
                      AMOUNT_MIN, AMOUNT_MAX)
    assert np.allclose(first["loan_amnt"], snapped)
    repeat = merged[merged.app_seq > 1]
    assert (repeat["loan_amnt"] / repeat["anchor"]).median() > 1.05


def test_time_semantics(leads):
    """Timestamps inside the window; app_seq increases with submitted_at per
    record; the file itself is sorted by submitted_at."""
    start = pd.Timestamp(WINDOW_START)
    end = start + pd.Timedelta(days=int(MONTHS * 365.25 / 12))
    assert (leads["submitted_at"] >= start).all()
    assert (leads["submitted_at"] < end).all()
    assert leads["submitted_at"].is_monotonic_increasing
    by_rec = leads.sort_values(["consumer_record_id", "app_seq"])
    grp = by_rec.groupby("consumer_record_id")["submitted_at"]
    assert (grp.apply(lambda s: s.is_monotonic_increasing)).all()
    # Daytime skew: most submissions land in waking hours
    hours = leads["submitted_at"].dt.hour
    assert hours.between(8, 21).mean() > 0.8


def test_conditioning_lineage(consumers, leads):
    """Every lead carries its consumer record's features verbatim."""
    assert leads["lead_uuid"].is_unique
    merged = leads.merge(consumers, on="consumer_record_id",
                         suffixes=("", "_c"))
    assert len(merged) == len(leads)
    for col in ("dti", "annual_inc", "fico_mid", "fico_band", "emp_length",
                "emp_years", "purpose", "addr_state"):
        assert (merged[col] == merged[f"{col}_c"]).all(), f"{col} mismatch"
    # The hidden person key never enters the lead table
    assert "consumer_key" not in leads.columns


def test_determinism(consumers, qm):
    """Same seed, same leads — the reproducibility exit criterion in miniature."""
    a = build_leads(consumers, qm, MONTHS, WINDOW_START,
                    np.random.default_rng(11))
    b = build_leads(consumers, qm, MONTHS, WINDOW_START,
                    np.random.default_rng(11))
    pd.testing.assert_frame_equal(a, b)


def test_three_stage_integration(tmp_path):
    """consumers -> leads -> waterfall end to end at toy scale: the waterfall
    consumes the real leads.parquet and emits events with derived timestamps."""
    cfg = SimConfig(seed=7, scale=0.002, out_dir=tmp_path,
                    private_dir=tmp_path / "private")
    cfg.ensure_dirs()
    generate_consumers(cfg)
    generate_leads(cfg)
    run_waterfall(cfg)

    leads = pd.read_parquet(tmp_path / "leads.parquet")
    events = pd.read_parquet(tmp_path / "auction_events.parquet")
    outcomes = pd.read_parquet(tmp_path / "lead_outcomes.parquet")
    assert len(outcomes) == len(leads)
    assert set(events["lead_uuid"]) <= set(leads["lead_uuid"])
    # Event timestamps derive from submission (tier rounds happen after it)
    first_evt = events.groupby("lead_uuid")["event_at"].min()
    sub = leads.set_index("lead_uuid")["submitted_at"]
    assert (first_evt >= sub.reindex(first_evt.index)).all()
    # Censoring structure survives the chain: some sales, some unsold
    assert 0 < outcomes["sold"].mean() < 1
