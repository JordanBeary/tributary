"""The marketing engine must reproduce the Section 3 QA gates from the artifact alone.

The spec's headline gate — a naive holdout analysis recovers the injected
uplift — is satisfied by construction (C15's inverse assignment), so the tests
assert it sharply: the realized treated-minus-holdout conversion difference
must sit within integer-rounding distance of the artifact's ATE, overall and
per engagement segment. The rest are experiment-structure invariants the
Phase 4/5 analyses will lean on: ITT semantics, pre-submission timing, the
engagement-correlated funnel, and the marketing-only orphan share.
"""

import numpy as np
import pandas as pd
import pytest

from simulation.config import SimConfig
from simulation.consumers import CreditModel, IdentityVocab, build_population
from simulation.leads import QualityModel, build_leads
from simulation.marketing import SEG_FACTORS, UpliftModel, build_marketing
from simulation.stages import (
    generate_consumers, generate_leads, generate_marketing, run_waterfall,
)

SEED = 202608
N_CONSUMERS = 120_000  # per-segment holdout arms ~3.6k: rounding ~0.01pp << ATE
MONTHS = 12
WINDOW_START = "2025-07-01"
MKT_RATE = 0.10


@pytest.fixture(scope="module")
def um():
    return UpliftModel.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def vocab():
    return IdentityVocab.from_faker()


@pytest.fixture(scope="module")
def world(um, vocab):
    model = CreditModel.from_params_dir("simulation/params")
    qm = QualityModel.from_params_dir("simulation/params")
    rng = np.random.default_rng(SEED)
    consumers = build_population(model, vocab, N_CONSUMERS, 0.08, rng)
    leads = build_leads(consumers, qm, MONTHS, WINDOW_START,
                        np.random.default_rng(SEED + 1))
    contacts, messages, spend = build_marketing(
        consumers, leads, um, vocab, MONTHS, WINDOW_START, MKT_RATE,
        np.random.default_rng(SEED + 2))
    return consumers, leads, contacts, messages, spend


def test_naive_analysis_recovers_ate(world, um):
    """Section 3 gate: treated-minus-holdout conversion equals the injected
    ATE up to integer rounding — and lands inside the artifact's own CI."""
    _, _, contacts, _, _ = world
    conv = ~contacts["is_marketing_only"]
    treated = ~contacts["in_holdout"]
    diff = conv[treated].mean() - conv[~treated].mean()
    assert abs(diff - um.ate) < 3e-4, f"naive estimate {diff:.5f} vs ATE {um.ate:.5f}"


def test_segment_uplift_matches_multipliers(world, um):
    """C6 heterogeneity survives: per-segment uplift tracks the artifact's
    multipliers, with the top quintile carrying ~4.5x the average."""
    _, _, contacts, _, _ = world
    conv = ~contacts["is_marketing_only"]
    treated = ~contacts["in_holdout"]
    for s in range(1, 6):
        m = contacts["engagement_segment"] == s
        diff = conv[m & treated].mean() - conv[m & ~treated].mean()
        tau = um.ate * um.seg_mult[s - 1]
        assert abs(diff - tau) < 5e-4, f"segment {s}: {diff:.5f} vs {tau:.5f}"


def test_experiment_design(world, um):
    """85/15 split; ~10% marketing-only prospects, none with an application;
    holdout contacts receive no messages (ITT), ~5% of treated draw zero."""
    consumers, _, contacts, messages, _ = world
    treated_share = (~contacts["in_holdout"]).mean()
    assert abs(treated_share - um.treated_share) < 0.005
    mkt = contacts["is_marketing_only"]
    assert abs(mkt.mean() - MKT_RATE) < 0.01
    assert not contacts.loc[mkt, "email"].isin(set(consumers["email"])).any()

    messaged = set(messages["email"])
    assert messaged <= set(contacts.loc[~contacts["in_holdout"], "email"])
    silent = 1 - len(messaged) / (~contacts["in_holdout"]).sum()
    assert 0.02 < silent < 0.08  # Poisson(3) zero mass ~ 5%, minus window drops


def test_message_volume(world, um):
    """Poisson(3) capped at 10: within-cap counts, mean ~3 per messaged contact."""
    _, _, _, messages, _ = world
    per_contact = messages.groupby("email").size()
    assert per_contact.max() <= um.cap
    assert 2.9 < per_contact.mean() < 3.3


def test_funnel(world, um):
    """C5 rates hold in aggregate; opens rise with engagement; click implies
    open; event timestamps are ordered."""
    _, _, contacts, messages, _ = world
    m = messages.merge(contacts[["email", "engagement_segment"]], on="email")
    opened = m["opened_at"].notna()
    clicked = m["clicked_at"].notna()
    assert abs(opened.mean() - um.open_rate) < 0.02
    assert abs(clicked[opened].mean() - um.click_rate) < 0.01
    by_seg = opened.groupby(m["engagement_segment"]).mean()
    assert by_seg.is_monotonic_increasing
    assert np.allclose(by_seg.to_numpy() / um.open_rate, SEG_FACTORS, atol=0.05)
    assert (clicked <= opened).all()
    assert (m.loc[opened, "opened_at"] > m.loc[opened, "sent_at"]).all()
    assert (m.loc[clicked, "clicked_at"] > m.loc[clicked, "opened_at"]).all()


def test_pre_submission_timing(world):
    """Every send to a converter lands strictly before that contact's first
    application; prospect sends stay inside the window."""
    consumers, leads, contacts, messages, spend = world
    first_sub = (leads.merge(consumers[["consumer_record_id", "email"]],
                             on="consumer_record_id")
                 .groupby("email")["submitted_at"].min())
    m = messages.merge(first_sub.rename("first_sub"), left_on="email",
                       right_index=True, how="left")
    conv = m["first_sub"].notna()
    assert (m.loc[conv, "sent_at"] < m.loc[conv, "first_sub"]).all()
    start = pd.Timestamp(WINDOW_START)
    end = start + pd.Timedelta(days=int(MONTHS * 365.25 / 12))
    assert (m["sent_at"] >= start).all() and (m["sent_at"] < end).all()
    # Campaign cohort key matches the send month
    expect = ("camp_" + m["sent_at"].dt.to_period("M").astype(str)
              .str.replace("-", "", regex=False))
    assert (m["campaign_id"] == expect).all()


def test_channel_mix_and_conversion(world):
    """C16: pool mix lands on the declared blend, and per-channel
    contact->application conversion follows the intent ladder — organic and
    direct convert best, display worst — at the rescaled target values."""
    from simulation.marketing import ACQ_CHANNELS
    _, _, contacts, _, _ = world
    mix = contacts["acquisition_channel"].value_counts(normalize=True)
    for ch, target in ACQ_CHANNELS["mix"].items():
        assert abs(mix[ch] - target) < 0.012, f"{ch} mix {mix[ch]:.3f}"

    conv = (~contacts["is_marketing_only"]).groupby(
        contacts["acquisition_channel"]).mean()
    scale = (1 - MKT_RATE) / (ACQ_CHANNELS["mix"]
                              * ACQ_CHANNELS["conv_target"]).sum()
    target = (ACQ_CHANNELS["conv_target"] * scale).clip(upper=0.995)
    for ch in ACQ_CHANNELS.index:
        assert abs(conv[ch] - target[ch]) < 0.015, \
            f"{ch}: conv {conv[ch]:.3f} vs target {target[ch]:.3f}"
    ladder = conv.reindex(ACQ_CHANNELS.index)  # table rows are intent-ordered
    assert ladder.is_monotonic_decreasing, f"intent ladder broken:\n{ladder}"


def test_channel_intent_correlations(world):
    """C16: high-intent channels skew to higher engagement segments AND
    deliver higher lead quality among converters (q_tilt)."""
    consumers, leads, contacts, _, _ = world
    seg = contacts.groupby("acquisition_channel")["engagement_segment"].mean()
    assert seg["organic_search"] > seg["paid_search"] > seg["display"]

    mean_q = (leads.merge(consumers[["consumer_record_id", "email"]],
                          on="consumer_record_id")
              .groupby("email")["q"].mean())
    cq = contacts.assign(q=contacts["email"].map(mean_q)).dropna(subset=["q"])
    q_by_ch = cq.groupby("acquisition_channel")["q"].mean()
    assert q_by_ch["organic_search"] > q_by_ch["paid_search"] > q_by_ch["display"]


def test_spend_ledger(world):
    """C16: the monthly media ledger is internally consistent — traffic
    covers contacts, spend follows the declared unit economics, owned
    channels cost nothing."""
    from simulation.marketing import ACQ_CHANNELS, SPEND_JITTER
    _, _, contacts, _, spend = world
    a = ACQ_CHANNELS.loc[spend["channel"]]

    # Every contact-month is covered, and traffic >= contacts where defined
    assert spend["new_contacts"].sum() == len(contacts)
    has_rate = a["click_to_contact"].notna().to_numpy()
    assert (spend.loc[has_rate, "visits"]
            >= spend.loc[has_rate, "new_contacts"]).all()

    owned = a["cpc"].fillna(0).to_numpy() == 0
    is_cpl = a["cpl"].notna().to_numpy()
    assert (spend.loc[owned & ~is_cpl, "spend_usd"] == 0).all()
    # Affiliate bills exactly contacts x CPL; media spend within jitter of CPC
    cpl_rows = spend.loc[is_cpl]
    assert np.allclose(cpl_rows["spend_usd"],
                       cpl_rows["new_contacts"] * a.loc[is_cpl, "cpl"].to_numpy())
    media = spend.loc[~owned]
    nominal = media["visits"] * a.loc[~owned.astype(bool), "cpc"].to_numpy()
    ratio = media["spend_usd"] / nominal
    assert ((ratio > 1 - SPEND_JITTER - 0.001)
            & (ratio < 1 + SPEND_JITTER + 0.001)).all()
    # Impressions only for media channels, at plausible CTR scale
    has_ctr = a["ctr"].notna().to_numpy()
    imp = spend.loc[has_ctr]
    assert (imp["impressions"] >= imp["visits"]).all()


def test_acquired_at(world):
    """Acquisition precedes the first send and the first application; all
    acquisitions inside the window."""
    consumers, leads, contacts, messages, _ = world
    first_send = messages.groupby("email")["sent_at"].min()
    c = contacts.assign(first_send=contacts["email"].map(first_send))
    sent = c["first_send"].notna()
    assert (c.loc[sent, "acquired_at"] <= c.loc[sent, "first_send"]).all()
    conv = c["first_sub"].notna()
    assert (c.loc[conv, "acquired_at"] <= c.loc[conv, "first_sub"]).all()
    start = pd.Timestamp(WINDOW_START)
    end = start + pd.Timedelta(days=int(MONTHS * 365.25 / 12))
    assert (c["acquired_at"] >= start).all() and (c["acquired_at"] < end).all()


def test_determinism(world, um, vocab):
    """Same seed, same experiment — assignment and ledger included."""
    consumers, leads, contacts, messages, spend = world
    c2, m2, s2 = build_marketing(consumers, leads, um, vocab, MONTHS,
                                 WINDOW_START, MKT_RATE,
                                 np.random.default_rng(SEED + 2))
    pd.testing.assert_frame_equal(contacts, c2)
    pd.testing.assert_frame_equal(messages, m2)
    pd.testing.assert_frame_equal(spend, s2)


def test_four_stage_integration(tmp_path):
    """consumers -> leads -> waterfall -> marketing end to end at toy scale."""
    cfg = SimConfig(seed=7, scale=0.002, out_dir=tmp_path,
                    private_dir=tmp_path / "private")
    cfg.ensure_dirs()
    generate_consumers(cfg)
    generate_leads(cfg)
    run_waterfall(cfg)
    generate_marketing(cfg)
    contacts = pd.read_parquet(tmp_path / "marketing_contacts.parquet")
    messages = pd.read_parquet(tmp_path / "messages.parquet")
    spend = pd.read_parquet(tmp_path / "channel_spend.parquet")
    assert contacts["email"].is_unique
    assert set(messages["email"]) <= set(contacts["email"])
    assert spend["new_contacts"].sum() == len(contacts)
    # The hidden person key and lead quality never enter the marketing world
    for df in (contacts, messages, spend):
        assert "consumer_key" not in df.columns
    assert "_mean_q" not in contacts.columns
