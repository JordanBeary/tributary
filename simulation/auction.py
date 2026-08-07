"""Waterfall auction engine — the production implementation of design.md Section 3.2.

Consumes ``simulation/params/auction_landscape.json`` (produced and QA-gated by
``analysis/profiling/02_ipinyou.ipynb``) and nothing else: every behavioral
parameter — tier floors, valuation locations, the empirical noise shape (C10),
the declared quality elasticity on rank-q (C11), Beta participation with the
cherry-picking odds shift (C12) — comes from the artifact, so the engine
reproduces the notebook's QA gates from the artifact alone (tests/test_waterfall.py).

Mechanics per lead: tiers are visited in order 1..6. Each tier seats 2-5 buyers
(distribution fitted from iPinYou win rates); each seated buyer bids with a
Beta-distributed base probability whose odds shift with lead quality
(cherry-picking). Bidders draw log-valuations mu_t + elasticity*(q - 0.5) +
sigma_t * Z, with Z from the empirical standardized shape table. If the top
bid clears the tier floor the lead sells at max(second-highest bid, floor)
— second-price with reserve — and the cascade stops; otherwise the lead falls
to the next tier. Unsold after tier 6 = censored (no price ever observed).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json
import numpy as np
import pandas as pd

N_TIERS = 6


@dataclass(frozen=True)
class AuctionLandscape:
    """The calibrated parameterization, loaded verbatim from the artifact."""

    floors: np.ndarray          # per-tier reserve prices ($), calibrated
    mu: np.ndarray              # per-tier log-valuation location
    sigma: np.ndarray           # per-tier valuation noise scale (within-vertical, C11)
    z_probs: np.ndarray         # inverse-CDF grid for the empirical noise shape (C10)
    z_table: np.ndarray
    beta_a: float               # per-seat participation Beta(a, b)
    beta_b: float
    seat_counts: np.ndarray     # bidders-per-auction support (2..5)
    seat_probs: np.ndarray
    elasticity: float           # log-price units per percentile of quality (C11)
    kappa: float                # cherry-picking odds shift (C12)

    @classmethod
    def from_params_dir(cls, params_dir: Path | str) -> "AuctionLandscape":
        p = json.loads((Path(params_dir) / "auction_landscape.json").read_text())
        tiers = p["tier_scale"]["tiers"]
        part = p["participation"]
        z_table = np.asarray(p["price_shape"]["valuation_shape_z"], dtype=float)
        return cls(
            floors=np.array([t["floor"] for t in tiers]),
            mu=np.array([t["mu"] for t in tiers]),
            sigma=np.array([t["sigma"] for t in tiers]),
            z_probs=np.linspace(0.0, 1.0, len(z_table)),
            z_table=z_table,
            beta_a=part["win_rate_beta"][0],
            beta_b=part["win_rate_beta"][1],
            seat_counts=np.array([int(k) for k in part["bidders_per_auction"]]),
            seat_probs=np.array(list(part["bidders_per_auction"].values())),
            elasticity=p["valuation_quality_elasticity"]["elasticity_used"],
            kappa=part["cherry_picking"]["kappa"],
        )


@dataclass
class AuctionResult:
    """Per-lead outcomes plus (optionally) the event-grain log."""

    sold_tier: np.ndarray       # 0-based tier index; -1 = unsold (censored)
    clearing_price: np.ndarray  # 0 where unsold — the price is never observed
    floor_bound: np.ndarray     # sale cleared exactly at the reserve
    events: pd.DataFrame | None = None


def run_auctions(
    q: np.ndarray,
    land: AuctionLandscape,
    rng: np.random.Generator,
    lead_uuid: np.ndarray | None = None,
    emit_events: bool = False,
) -> AuctionResult:
    """Run the full waterfall for an array of leads.

    ``q`` is the within-cohort percentile-rank quality score (uniform on (0,1)
    by construction, C11). ``lead_uuid`` labels event rows when
    ``emit_events`` is set. Vectorized per tier; memory scales with the number
    of still-active leads, so full-scale runs (~2.4M leads) stay in-core.
    """
    n = len(q)
    sold_tier = np.full(n, -1, dtype=np.int8)
    price = np.zeros(n)
    floor_bound = np.zeros(n, dtype=bool)
    active = np.ones(n, dtype=bool)
    event_frames: list[pd.DataFrame] = []
    max_seats = int(land.seat_counts.max())

    for t in range(N_TIERS):
        idx = np.flatnonzero(active)
        if not len(idx):
            break
        seats = rng.choice(land.seat_counts, size=len(idx), p=land.seat_probs)
        seated = np.arange(max_seats)[None, :] < seats[:, None]

        # Participation: Beta base odds shifted by quality (cherry-picking, C12)
        p0 = rng.beta(land.beta_a, land.beta_b, size=(len(idx), max_seats))
        logit = np.log(p0 / (1 - p0)) + land.kappa * (q[idx] - 0.5)[:, None]
        bids_mask = (rng.uniform(size=(len(idx), max_seats)) < 1 / (1 + np.exp(-logit))) & seated

        # Valuations: location + declared elasticity on rank-q + empirical-shape noise
        z = np.interp(rng.uniform(size=(len(idx), max_seats)), land.z_probs, land.z_table)
        vals = np.exp(land.mu[t] + land.elasticity * (q[idx] - 0.5)[:, None]
                      + land.sigma[t] * z)
        vals[~bids_mask] = -np.inf

        order = np.sort(vals, axis=1)
        top, second = order[:, -1], order[:, -2]
        sells = top >= land.floors[t]
        w = idx[sells]
        second_v = np.where(np.isfinite(second[sells]), second[sells], 0.0)
        sold_tier[w] = t
        price[w] = np.maximum(second_v, land.floors[t])
        floor_bound[w] = second_v < land.floors[t]

        if emit_events:
            event_frames.append(_tier_events(
                t, idx, lead_uuid, bids_mask, vals, sells, price, land.floors[t]))
        active[w] = False

    events = None
    if emit_events:
        events = pd.concat(event_frames, ignore_index=True)
    return AuctionResult(sold_tier, price, floor_bound, events)


def _tier_events(t, idx, lead_uuid, bids_mask, vals, sells, price, floor):
    """Build the event-grain rows for one tier: bid_request, bid, win/no_sale.

    Buyer identifiers are structured (``buyer_t{tier}_{seat:03d}``) per the
    no-fictional-names convention. Bids log the buyer's valuation (truthful
    bidding in a second-price auction); only win rows carry a clearing price —
    that is the censoring structure the ML workstream depends on.
    """
    labels = lead_uuid[idx] if lead_uuid is not None else idx
    frames = [pd.DataFrame({
        "event_type": "bid_request", "lead_uuid": labels, "tier": t + 1,
        "buyer_id": pd.NA, "bid_price": np.nan, "clearing_price": np.nan,
        "floor_price": floor,
    })]
    lead_i, seat_i = np.nonzero(bids_mask)
    frames.append(pd.DataFrame({
        "event_type": "bid", "lead_uuid": labels[lead_i], "tier": t + 1,
        "buyer_id": [f"buyer_t{t + 1}_{s:03d}" for s in seat_i],
        "bid_price": vals[lead_i, seat_i], "clearing_price": np.nan,
        "floor_price": floor,
    }))
    frames.append(pd.DataFrame({
        "event_type": np.where(sells, "win", "no_sale"), "lead_uuid": labels,
        "tier": t + 1, "buyer_id": pd.NA, "bid_price": np.nan,
        "clearing_price": np.where(sells, price[idx], np.nan),
        "floor_price": floor,
    }))
    return pd.concat(frames, ignore_index=True)
