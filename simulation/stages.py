"""Simulation stages — implementation lands in Phase 1.

Each stage takes a SimConfig, reads upstream outputs from cfg.out_dir, and
writes its own outputs there. Signatures and contracts are fixed now so the
loaders (silos/), dbt sources (warehouse/), and ER pipeline (er/) can be
built against them. Fitting details: docs/calibration_spec.md.
"""

from __future__ import annotations

from simulation.config import SimConfig


def generate_consumers(cfg: SimConfig) -> None:
    """Sample cfg.n_consumers consumers with credit features + identity.

    - Credit/demographic features from the LendingClub Gaussian copula
      (params: lendingclub_marginals.json).
    - Identity attributes (name, email, phone, address) via Faker.
    - Injects ~cfg.duplicate_rate duplicate consumers with corrupted identity
      fields (nickname, typo'd email, new phone).
    - Writes consumers.parquet WITH consumer_key, which only the fracture
      stage may strip; the crosswalk goes to cfg.private_dir.
    """
    raise NotImplementedError("Phase 1: see docs/calibration_spec.md §1")


def generate_leads(cfg: SimConfig) -> None:
    """1-3 applications per consumer over cfg.months; ~1.6x consumers total.

    Application features conditioned on the consumer credit profile; quality
    score q from the fitted acceptance model. Writes leads.parquet.
    """
    raise NotImplementedError("Phase 1: see docs/calibration_spec.md §1")


def run_waterfall(cfg: SimConfig) -> None:
    """6-tier sequential waterfall auction per lead (~9M events at scale=1).

    Buyer valuations ~ lognormal landscape (auction_landscape.json),
    conditioned on q. Emits event-grain bid_request/bid/win/no_sale rows with
    naturally censored prices: clearing price observed only on sales.
    Writes auction_events.parquet.
    """
    raise NotImplementedError("Phase 1: see docs/calibration_spec.md §2")


def generate_marketing(cfg: SimConfig) -> None:
    """Pre-submission nurture messages (~4M at scale=1) with randomized
    holdout and a small true uplift on application probability
    (uplift_params.json). Writes messages.parquet.
    """
    raise NotImplementedError("Phase 1: see docs/calibration_spec.md §3")


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
