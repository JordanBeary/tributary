"""C19 gates reproduced from the artifacts alone (repeat_demand.json).

Recency-dependent demand: leads whose person applied recently must win less
and clear lower, in the fitted ratios; the funded flag must ride a modest
price gradient with the artifact CVR preserved as the mean. As with the other
engine tests, everything here runs from the committed artifacts and synthetic
uniform inputs -- no private data, no generated tree.
"""

import json

import numpy as np
import pytest

from simulation.auction import AuctionLandscape, run_auctions
from simulation.repeat_demand import RepeatDemand, funded_flags

SEED = 202608
N = 150_000
# The dials were fitted on the real lead pool (quality mildly correlated with
# recency); these gates re-measure on a uniform-q pool, so they carry a wider
# tolerance than the fit's own 0.02.
RATIO_TOL = 0.07


@pytest.fixture(scope="module")
def land():
    return AuctionLandscape.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def demand():
    return RepeatDemand.from_params_dir("simulation/params")


@pytest.fixture(scope="module")
def targets():
    return json.loads(open("simulation/params/repeat_demand.json").read())["kpi_ratio_targets"]


def _stats(q, land, o, v):
    r = run_auctions(q, land, np.random.default_rng(SEED + 1),
                     recency_odds=np.full(len(q), o), recency_price=np.full(len(q), v))
    sold = r.sold_tier >= 0
    return sold.mean(), r.clearing_price[sold].mean()


def test_recency_ratio_gates(land, demand, targets):
    """Win-rate and price-per-sold ratios (recent vs fresh) match the artifact."""
    rng = np.random.default_rng(SEED)
    q = rng.uniform(size=N)
    w3, p3 = _stats(q, land, demand.odds_mult[3], demand.price_mult[3])
    for b in range(3):
        wb, pb = _stats(q, land, demand.odds_mult[b], demand.price_mult[b])
        assert abs(wb / w3 - targets["win_rate"][b]) < RATIO_TOL, \
            f"bucket {b} win ratio {wb / w3:.3f}"
        assert abs(pb / p3 - targets["price_per_sold"][b]) < RATIO_TOL, \
            f"bucket {b} price ratio {pb / p3:.3f}"


def test_recency_none_is_pre_c19(land):
    """Omitting the recency arrays reproduces the unamended engine exactly."""
    rng = np.random.default_rng(SEED)
    q = rng.uniform(size=20_000)
    a = run_auctions(q, land, np.random.default_rng(SEED + 2))
    b = run_auctions(q, land, np.random.default_rng(SEED + 2),
                     recency_odds=np.ones(len(q)), recency_price=np.ones(len(q)))
    assert np.array_equal(a.sold_tier, b.sold_tier)
    assert np.allclose(a.clearing_price, b.clearing_price)


def test_bucket_edges(demand):
    d = np.array([np.nan, 0.4, 1.0, 6.9, 7.0, 29.9, 30.0, 400.0])
    assert demand.bucket(d).tolist() == [3, 0, 1, 1, 2, 2, 3, 3]


def test_funded_gradient(demand):
    """Mean preserved at the target rate; modest positive lift with price."""
    rng = np.random.default_rng(SEED)
    price = np.exp(rng.normal(5.0, 1.0, size=400_000))  # wide sold-price spread
    rate = 0.134
    f = funded_flags(price, rate, demand.funded_beta, np.random.default_rng(SEED + 3))
    assert abs(f.mean() - rate) < 0.004
    qlo, qhi = np.quantile(price, [0.2, 0.8])
    lift = f[price >= qhi].mean() / f[price <= qlo].mean()
    assert 1.1 < lift < 2.0, f"top/bottom-quintile funded lift {lift:.2f}"


def test_funded_beta_zero_is_uniform(demand):
    """beta = 0 reproduces the C17d uniform draw's mean and flatness."""
    rng = np.random.default_rng(SEED)
    price = np.exp(rng.normal(5.0, 1.0, size=400_000))
    f = funded_flags(price, 0.134, 0.0, np.random.default_rng(SEED + 4))
    qlo, qhi = np.quantile(price, [0.2, 0.8])
    assert abs(f[price >= qhi].mean() - f[price <= qlo].mean()) < 0.01
