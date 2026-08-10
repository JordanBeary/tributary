"""Simulation stages — implementation lands in Phase 1.

Each stage takes a SimConfig, reads upstream outputs from cfg.out_dir, and
writes its own outputs there. Signatures and contracts are fixed now so the
loaders (silos/), dbt sources (warehouse/), and ER pipeline (er/) can be
built against them. Fitting details: docs/calibration_spec.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from simulation.auction import AuctionLandscape, run_auctions
from simulation.config import SimConfig
from simulation.consumers import CreditModel, IdentityVocab, build_population
from simulation.leads import QualityModel, build_leads
from simulation.marketing import UpliftModel, build_marketing


def generate_consumers(cfg: SimConfig) -> None:
    """Sample cfg.n_consumers consumer records with credit features + identity.

    - Credit/demographic features from the LendingClub Gaussian copula
      (params: lendingclub_marginals.json).
    - Synthetic identity attributes (name, email, phone, address), sampled
      from en_US vocabularies through the stage RNG stream (C13b).
    - ~cfg.duplicate_rate of the records are duplicates: the same person
      (shared consumer_key) with corrupted identity fields per the C7 mix
      (nickname, typo'd email, new phone). Record count includes duplicates,
      so Section 3.3 volumes hold exactly.
    - Writes consumers.parquet WITH consumer_key, which only the fracture
      stage may strip; the crosswalk goes to cfg.private_dir.
    """
    model = CreditModel.from_params_dir(cfg.params_dir)
    vocab = IdentityVocab.from_faker()
    # Stage-scoped RNG stream: independent of other stages, reproducible per seed
    rng = np.random.default_rng(np.random.SeedSequence([cfg.seed, 1]))
    pop = build_population(model, vocab, cfg.n_consumers, cfg.duplicate_rate, rng)
    pop.to_parquet(cfg.out_dir / "consumers.parquet", index=False)


def generate_leads(cfg: SimConfig) -> None:
    """1-3 applications per consumer over cfg.months; 1.6x consumers in
    expectation (C14 mix).

    Application features conditioned on the consumer credit profile (repeat
    applications re-request upward-jittered amounts); quality score q from the
    fitted acceptance model, consumed as within-cohort percentile rank (C11).
    Writes leads.parquet sorted by submitted_at.
    """
    consumers = pd.read_parquet(cfg.out_dir / "consumers.parquet")
    qm = QualityModel.from_params_dir(cfg.params_dir)
    # Stage-scoped RNG stream: independent of other stages, reproducible per seed
    rng = np.random.default_rng(np.random.SeedSequence([cfg.seed, 2]))
    leads = build_leads(consumers, qm, cfg.months, cfg.window_start, rng)
    leads.to_parquet(cfg.out_dir / "leads.parquet", index=False)


def run_waterfall(cfg: SimConfig) -> None:
    """6-tier sequential waterfall auction per lead (~9M events at scale=1).

    Buyer valuations from the calibrated landscape (auction_landscape.json),
    conditioned on q per C11 with C12 cherry-picking participation. Emits
    event-grain bid_request/bid/win/no_sale rows with naturally censored
    prices: clearing price observed only on sales. Writes
    auction_events.parquet and lead_outcomes.parquet.

    Expects leads.parquet (from generate_leads) with at least: lead_uuid,
    q (within-cohort percentile rank), submitted_at (optional — event
    timestamps are derived from it when present).
    """
    leads = pd.read_parquet(cfg.out_dir / "leads.parquet")
    land = AuctionLandscape.from_params_dir(cfg.params_dir)
    # Stage-scoped RNG stream: independent of other stages, reproducible per seed
    rng = np.random.default_rng(np.random.SeedSequence([cfg.seed, 3]))

    result = run_auctions(leads["q"].to_numpy(), land, rng,
                          lead_uuid=leads["lead_uuid"].to_numpy(), emit_events=True)

    events = result.events
    if "submitted_at" in leads.columns:
        # Tier rounds happen minutes apart, after submission; seeded jitter
        base = leads.set_index("lead_uuid")["submitted_at"]
        offset_min = events["tier"] * 5 + rng.uniform(0, 4, size=len(events))
        events["event_at"] = (base.reindex(events["lead_uuid"]).to_numpy()
                              + pd.to_timedelta(offset_min, unit="m"))
    events.to_parquet(cfg.out_dir / "auction_events.parquet", index=False)

    # Lead-level outcomes (sold tier, censored flag, clearing price) for the
    # CRM silo and the analytics marts
    pd.DataFrame({
        "lead_uuid": leads["lead_uuid"],
        "sold_tier": np.where(result.sold_tier >= 0, result.sold_tier + 1, pd.NA),
        "sold": result.sold_tier >= 0,
        "clearing_price": np.where(result.sold_tier >= 0, result.clearing_price, np.nan),
        "floor_bound": result.floor_bound,
    }).to_parquet(cfg.out_dir / "lead_outcomes.parquet", index=False)


def generate_marketing(cfg: SimConfig) -> None:
    """Pre-submission nurture messages (~4M at scale=1) with randomized
    holdout and a small true uplift on application probability
    (uplift_params.json).

    Contact grain is unique email: consumer records plus never-applier
    prospects (cfg.marketing_only_rate of contacts — the experiment needs
    non-converters, and they double as the marketing-only orphan pathology).
    Every contact enters through an acquisition channel with declared
    full-funnel economics (C16); holdout contacts receive no messages
    (intention-to-treat). Writes marketing_contacts.parquet (audience:
    holdout flag, engagement segment, acquisition channel), messages.parquet
    (sends + funnel events), and channel_spend.parquet (monthly media
    ledger), per C15/C16.
    """
    consumers = pd.read_parquet(cfg.out_dir / "consumers.parquet")
    leads = pd.read_parquet(cfg.out_dir / "leads.parquet")
    um = UpliftModel.from_params_dir(cfg.params_dir)
    vocab = IdentityVocab.from_faker()
    # Stage-scoped RNG stream: independent of other stages, reproducible per seed
    rng = np.random.default_rng(np.random.SeedSequence([cfg.seed, 4]))
    contacts, messages, spend = build_marketing(
        consumers, leads, um, vocab, cfg.months, cfg.window_start,
        cfg.marketing_only_rate, rng)
    contacts.to_parquet(cfg.out_dir / "marketing_contacts.parquet", index=False)
    messages.to_parquet(cfg.out_dir / "messages.parquet", index=False)
    spend.to_parquet(cfg.out_dir / "channel_spend.parquet", index=False)


def fracture_into_silos(cfg: SimConfig) -> None:
    """Apply §2.3 pathologies and write each silo in its native format:

    - auction/  : Parquet partitioned by event date, lead_uuid keys, UTC
    - crm/      : CSV + SQL inserts, integer lead_id + email_sha256,
                  US/Pacific naive timestamps, entity-grain (mutable)
    - marketing/: newline-JSON exports, contact_id = md5(lower(email)),
                  US/Eastern timestamps
    - crosswalk.parquet -> cfg.private_dir (NEVER uploaded; git-ignored)
    """
    raise NotImplementedError("Phase 1: see design.md §2.3")
