"""The auction engine must reproduce the Section 2 QA gates from the artifact alone.

This is the profiling notebooks' stated exit condition for the simulator
(02_ipinyou.ipynb, Result section): the calibration lives entirely in
auction_landscape.json, so the production engine — fed nothing but that
artifact and a quality vector — must land inside the same gates the notebook
passed. Rank-q (C11) is uniform on (0,1) by construction, which is what makes
an artifact-only test possible: no LendingClub sampling needed here.
"""

import numpy as np
import pytest
from scipy import stats

from simulation.auction import N_TIERS, AuctionLandscape, run_auctions

SEED = 202608
N_LEADS = 100_000


@pytest.fixture(scope="module")
def land():
    return AuctionLandscape.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def result(land):
    rng = np.random.default_rng(SEED)
    q = rng.uniform(size=N_LEADS)  # rank-q is uniform by construction (C11)
    return q, run_auctions(q, land, np.random.default_rng(SEED + 1))


def test_censoring_gate(result):
    """C2: unsold (censored) fraction in 35-45%."""
    _, r = result
    censored = (r.sold_tier < 0).mean()
    assert 0.35 <= censored <= 0.45, f"censored fraction {censored:.3f}"


def test_monotone_sell_through(result):
    """Per-tier sell rate strictly declining from tier 1 to 6."""
    _, r = result
    reached = np.array([len(r.sold_tier) - np.isin(r.sold_tier, np.arange(t)).sum()
                        for t in range(N_TIERS)])
    rate = np.array([(r.sold_tier == t).sum() for t in range(N_TIERS)]) / reached
    assert np.all(np.diff(rate) < 0), f"tier rates not monotone: {np.round(rate, 3)}"


def test_elasticity_gate(result):
    """C9/C11: Spearman(q, clearing price) on sold leads > 0.3."""
    q, r = result
    sold = r.sold_tier >= 0
    rho = stats.spearmanr(q[sold], r.clearing_price[sold]).statistic
    assert rho > 0.3, f"Spearman(q, price) = {rho:.3f}"


def test_adverse_selection_cascade(result):
    """C11 diagnostic, asserted here: mean q by sold tier strictly descends."""
    q, r = result
    mean_q = [q[r.sold_tier == t].mean() for t in range(N_TIERS)]
    assert np.all(np.diff(mean_q) < 0), f"mean q by tier: {np.round(mean_q, 3)}"


def test_prices_respect_reserves(result):
    """Every sale clears at or above its tier floor; unsold leads have no price."""
    _, r = result
    land = AuctionLandscape.from_params_dir("simulation/params")
    sold = r.sold_tier >= 0
    assert np.all(r.clearing_price[sold] >= land.floors[r.sold_tier[sold]] - 1e-9)
    assert np.all(r.clearing_price[~sold] == 0)


def test_determinism(land):
    """Same seed, same results — the reproducibility exit criterion in miniature."""
    q = np.random.default_rng(7).uniform(size=20_000)
    a = run_auctions(q, land, np.random.default_rng(11))
    b = run_auctions(q, land, np.random.default_rng(11))
    assert np.array_equal(a.sold_tier, b.sold_tier)
    assert np.array_equal(a.clearing_price, b.clearing_price)


def test_event_grain_consistency(land):
    """Event log agrees with per-lead outcomes: one bid_request and one
    win/no_sale per lead-tier offered; win prices match clearing prices;
    bids carry structured buyer ids."""
    rng = np.random.default_rng(23)
    q = rng.uniform(size=5_000)
    uuids = np.array([f"lead_{i:05d}" for i in range(len(q))])
    r = run_auctions(q, land, np.random.default_rng(29), lead_uuid=uuids,
                     emit_events=True)
    ev = r.events

    wins = ev[ev.event_type == "win"]
    assert len(wins) == (r.sold_tier >= 0).sum()
    merged = wins.set_index("lead_uuid")["clearing_price"]
    sold_idx = np.flatnonzero(r.sold_tier >= 0)
    assert np.allclose(merged.loc[uuids[sold_idx]].to_numpy(),
                       r.clearing_price[sold_idx])

    # Each offered lead-tier has exactly one terminal event (win or no_sale)
    reqs = ev[ev.event_type == "bid_request"].groupby("lead_uuid").size()
    terms = ev[ev.event_type.isin(["win", "no_sale"])].groupby("lead_uuid").size()
    assert reqs.equals(terms)

    bids = ev[ev.event_type == "bid"]
    assert bids["buyer_id"].str.match(r"buyer_t[1-6]_\d{3}").all()
    # Censoring structure: only win rows ever carry a clearing price
    assert ev.loc[ev.event_type != "win", "clearing_price"].isna().all()
