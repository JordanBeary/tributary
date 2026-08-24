"""Phase 5 model-layer gates that need no data or trained models.

The training scripts are evaluated against the warehouse (their metrics JSON
is the record); what belongs in the test suite is the pure math and the
contracts: the Tobit gradients against numerical differentiation, the
feature contract's leakage discipline, the uplift curve on a constructed
case with a known answer, and the counterfactual replay on hand-built bids.
"""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import common, tobit
from models.optimize_floors import replay
from models.train_uplift import uplift_curve


# ── Tobit objective ──

def test_tobit_gradients_match_numerical():
    rng = np.random.default_rng(0)
    n, sigma = 200, 0.7
    mu = rng.normal(1.0, 1.0, n)
    y = rng.normal(1.0, 1.0, n)
    censored = rng.random(n) < 0.5
    grad, hess = tobit.gradients(mu, y, censored, sigma)
    eps = 1e-5
    num_grad = (np.array([tobit.nll(mu + eps * e, y, censored, sigma)
                          for e in np.eye(n)]) -
                np.array([tobit.nll(mu - eps * e, y, censored, sigma)
                          for e in np.eye(n)])) / (2 * eps) * n
    assert np.allclose(grad, num_grad, rtol=1e-4, atol=1e-6)
    assert (hess > 0).all()


def test_tobit_censored_gradient_pushes_mu_down():
    # A censored row (y* below the bound) must pull the prediction down
    grad, _ = tobit.gradients(np.array([2.0]), np.array([0.0]),
                              np.array([True]), 1.0)
    assert grad[0] > 0


def test_tobit_sigma_profile_recovers_truth():
    rng = np.random.default_rng(1)
    n, sigma_true = 50_000, 0.6
    mu = np.zeros(n)
    latent = rng.normal(0.0, sigma_true, n)
    c = -0.3
    censored = latent < c
    y = np.where(censored, c, latent)
    assert abs(tobit.profile_sigma(mu, y, censored) - sigma_true) < 0.02


def test_truncated_mean_exceeds_mu_and_bound():
    mu = np.array([0.0, 1.0, -2.0])
    tm = tobit.truncated_mean(mu, 0.5, 1.0)
    assert (tm > mu).all() and (tm > 0.5).all()


# ── Feature contract ──

def test_leakage_columns_disjoint_from_features():
    assert not set(common.FEATURES) & set(common.LEAKAGE_COLUMNS)


def test_recency_buckets_match_c19_artifact():
    import json
    params = json.loads((common.ROOT / "simulation" / "params" /
                         "repeat_demand.json").read_text())
    assert common.RECENCY_EDGES == params["buckets"]["day_edges"]


def test_recency_bucket_assignment():
    import pandas as pd
    days = pd.Series([0.0, 0.5, 1.0, 6.9, 7.0, 29.9, 30.0, 400.0, np.nan])
    got = common.recency_bucket(days).tolist()
    assert got == ["<1d", "<1d", "1-7d", "1-7d", "7-30d", "7-30d",
                   "fresh", "fresh", "fresh"]


# ── Uplift curve ──

def test_uplift_curve_finds_planted_segment():
    # Two segments; treatment helps only segment A. Ranking by the true
    # uplift must dominate random and end at the pooled ATE.
    rng = np.random.default_rng(2)
    n = 40_000
    seg_a = rng.random(n) < 0.5
    t = rng.random(n) < 0.5
    base = 0.30
    p = base + 0.10 * (seg_a & t)
    y = (rng.random(n) < p).astype(float)
    u_true = seg_a.astype(float)
    frac, gain, auuc = uplift_curve(u_true, y, t.astype(int))
    ate = y[t].mean() - y[~t].mean()
    assert abs(gain[-1] - ate) < 1e-9          # endpoint is the pooled ATE
    assert auuc > 0.005                        # well above random
    # At 50% targeted (all of segment A), the gain is already ~ the full ATE
    mid = np.argmin(np.abs(frac - 0.5))
    assert gain[mid] > 0.8 * ate


# ── Counterfactual replay ──

def test_replay_second_price_with_reserve():
    floors = np.array([100.0, 50.0])
    top1 = np.array([[120.0, np.nan],   # sells tier 1 at max(second, floor)
                     [80.0, 60.0],      # fails tier 1, sells tier 2 at floor
                     [80.0, 40.0],      # never clears: no revenue
                     [np.nan, np.nan]])  # no bids at all
    top2 = np.array([[110.0, np.nan],
                     [np.nan, np.nan],
                     [np.nan, np.nan],
                     [np.nan, np.nan]])
    rev = replay(floors, top1, top2)
    assert rev.tolist() == [110.0, 50.0, 0.0, 0.0]


def test_replay_floor_binds_when_second_bid_below():
    floors = np.array([100.0])
    rev = replay(floors, np.array([[150.0]]), np.array([[70.0]]))
    assert rev.tolist() == [100.0]
