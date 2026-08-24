"""Shared feature contract, temporal split, and mart loaders for Phase 5 models.

Every model trains on the unified warehouse marts (``fct_leads`` /
``fct_auction_events`` / ``fct_marketing_contacts``, D10) -- never on staging
tables or simulation outputs. The feature contract lives here so all four
models agree on what is observable at auction time and what is leakage.

Split discipline (D11): temporal, not random -- train on the first eight
months, validate on the next two (early stopping, calibration, sigma fits),
test on the final two. Leads: 2025-07-01 .. 2026-07-01.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "warehouse" / "tributary.duckdb"
OUT_DIR = Path(__file__).resolve().parent / "out"
SEED = 42

# Temporal split boundaries (D11): eight months train, two valid, two test.
VALID_START = "2026-03-01"
TEST_START = "2026-05-01"

# ── Feature contract: observable when the lead is submitted for auction ──
# Application payload + CRM applicant attributes (known at intake), marketing
# acquisition attributes and pre-submission message activity (via ER), and the
# consumer-entity history (past applications and sales only).
NUMERIC_FEATURES = [
    "loan_amount",
    "annual_income",
    "application_seq",
    "days_since_prior_application",
    "days_since_prior_sale_same_buyer",
    "days_since_prior_sale_any_buyer",
    "msgs_30d_pre",
    "opens_30d_pre",
    "clicks_30d_pre",
    "submitted_dow",
    "submitted_hour",
    "submitted_month_idx",
]
CATEGORICAL_FEATURES = [
    "state",
    "purpose",
    "fico_band",
    "employment_length",
    "acquisition_channel",
    "engagement_segment",
    "recency_bucket",
]
BOOLEAN_FEATURES = [
    "has_marketing_contact",
    "is_repeat_application",
    "is_orphan",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BOOLEAN_FEATURES

# Excluded as leakage: auction outcomes (n_bids, n_bidders, max_bid,
# tiers_offered, deepest_tier, sold*, clearing_price, revenue_usd, winning_*,
# cleared_at_floor, sold_tier_floor), post-sale CRM outcomes (crm_status,
# funded), and consumer_applications_total (counts future applications).
# in_holdout is experiment assignment, not a feature. last_touch_* are
# pre-submission but redundant with msgs/opens/clicks_30d_pre; unused.
LEAKAGE_COLUMNS = [
    "n_bids", "n_bidders", "max_bid", "tiers_offered", "deepest_tier",
    "sold", "sold_tier", "sold_at_utc", "sold_tier_floor", "clearing_price",
    "revenue_usd", "winning_buyer_id", "winning_bid", "n_bids_sold_tier",
    "cleared_at_floor", "crm_status", "funded", "consumer_applications_total",
]

# C19 recency buckets (simulation/params/repeat_demand.json) -- the demand
# dials operate on these, so models get the same discretization as a feature
# alongside the raw day count.
RECENCY_EDGES = [1.0, 7.0, 30.0]
RECENCY_LABELS = ["<1d", "1-7d", "7-30d", "fresh"]

# Fixed per-tier reserve prices in the deployed world (from the auction
# landscape; verified single-valued per tier in the events).
N_TIERS = 6


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(WAREHOUSE), read_only=read_only)


def recency_bucket(days: pd.Series) -> pd.Series:
    """C19 bucket labels from days-since-prior-application (NaN -> fresh)."""
    out = pd.cut(days, bins=[-np.inf] + RECENCY_EDGES + [np.inf],
                 labels=RECENCY_LABELS, right=False)
    return out.cat.add_categories([]).fillna("fresh")


def load_leads(columns: list[str] | None = None) -> pd.DataFrame:
    """One row per auctioned lead with the feature contract applied.

    Returns features + split label + the targets every model needs
    (sold, sold_tier, clearing_price). Extra mart columns via ``columns``.
    """
    extra = ", " + ", ".join(columns) if columns else ""
    with connect() as con:
        df = con.sql(f"""
            select
                lead_uuid, submitted_at_utc, submitted_date,
                loan_amount, annual_income, application_seq,
                days_since_prior_application,
                days_since_prior_sale_same_buyer, days_since_prior_sale_any_buyer,
                msgs_30d_pre, opens_30d_pre::bigint as opens_30d_pre,
                clicks_30d_pre::bigint as clicks_30d_pre,
                dayofweek(submitted_at_utc) as submitted_dow,
                hour(submitted_at_utc) as submitted_hour,
                datediff('month', date '2025-07-01', submitted_date) as submitted_month_idx,
                state, purpose, fico_band, employment_length,
                coalesce(acquisition_channel, 'none') as acquisition_channel,
                coalesce(engagement_segment, -1) as engagement_segment,
                has_marketing_contact, is_repeat_application, is_orphan,
                sold, sold_tier, clearing_price
                {extra}
            from main_marts.fct_leads
        """).df()
    df["recency_bucket"] = recency_bucket(df["days_since_prior_application"])
    for c in CATEGORICAL_FEATURES:
        df[c] = df[c].astype("category")
    df["split"] = np.where(
        df["submitted_date"] < pd.Timestamp(VALID_START), "train",
        np.where(df["submitted_date"] < pd.Timestamp(TEST_START), "valid", "test"))
    return df


def split_frames(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (df[df["split"] == "train"], df[df["split"] == "valid"],
            df[df["split"] == "test"])


def tier_floors() -> np.ndarray:
    """The deployed per-tier reserve schedule, read from the events."""
    with connect() as con:
        f = con.sql("""
            select tier, min(floor_price) lo, max(floor_price) hi
            from main_marts.fct_auction_events group by tier order by tier
        """).df()
    if not np.allclose(f["lo"], f["hi"]):
        raise ValueError("per-tier floors are not constant; revisit model 3")
    return f["lo"].to_numpy()
