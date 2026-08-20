"""Acquisition channels (C16): the declared full-funnel economics, shared.

Moved from marketing.py (C18) so the consumer stage can assign channels at
person grain -- identity drift depends on acquisition channel (messy
channels ship messier data), which requires the channel to exist before
leads are generated. All C16 values are unchanged; the q_tilt correlation
is now applied against a person-level acceptance-score percentile instead
of the realized mean lead quality (same model, person grain).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Values are declared assumptions calibrated to lead-gen industry shape:
# personal-loan paid-search clicks are expensive ($10 CPC at 8% click->contact
# ~ $125 CAC), affiliates sell leads at ~$60 CPL, display retargeting buys
# cheap low-intent clicks that convert worst -- by construction the channel mix
# spans clearly-profitable to unprofitable (C16).
ACQ_CHANNELS = pd.DataFrame({
    "mix":              [0.08,   0.24,   0.08,   0.26,   0.12,   0.14,   0.08],
    "conv_target":      [0.97,   0.95,   0.93,   0.90,   0.85,   0.82,   0.72],
    "seg_tier":         ["high", "high", "mid",  "mid",  "low",  "low",  "low"],
    "q_tilt":           [0.30,   0.40,   0.20,   0.00,   -0.20,  -0.30,  -0.40],
    "click_to_contact": [0.35,   0.12,   0.10,   0.08,   np.nan, 0.025,  0.005],
    "cpc":              [0.0,    0.0,    0.0,    10.00,  np.nan, 1.60,   0.80],
    "cpl":              [np.nan, np.nan, np.nan, np.nan, 60.00,  np.nan, np.nan],
    "ctr":              [np.nan, np.nan, np.nan, 0.045,  np.nan, 0.009,  0.0025],
}, index=pd.Index(["direct", "organic_search", "referral", "paid_search",
                   "affiliate", "paid_social", "display"], name="channel"))

# Engagement-segment mix per intent tier (means 3.4 / 3.0 / 2.6)
SEG_TIER_PROBS = {
    "high": np.array([0.12, 0.16, 0.20, 0.24, 0.28]),
    "mid":  np.array([0.20, 0.20, 0.20, 0.20, 0.20]),
    "low":  np.array([0.28, 0.24, 0.20, 0.16, 0.12]),
}


def stats_rank(x: np.ndarray) -> np.ndarray:
    """Percentile rank in (0,1); ties broken by stable order (x is continuous)."""
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x))
    ranks[order] = np.arange(1, len(x) + 1)
    return ranks / (len(x) + 1)


def converter_prospect_mixes(marketing_only_rate: float,
                             ) -> tuple[np.ndarray, np.ndarray]:
    """Bayes split of the channel mix into converter/prospect mixes.

    Per-channel contact->application conversion targets are rescaled by one
    factor so the pool-weighted rate matches the structural rate implied by
    the marketing-only dial; the intent ordering is what carries the realism.
    """
    a = ACQ_CHANNELS
    scale = (1 - marketing_only_rate) / (a["mix"] * a["conv_target"]).sum()
    conv_rate = (a["conv_target"] * scale).clip(upper=0.995)
    p_conv = (a["mix"] * conv_rate).to_numpy()
    p_pros = (a["mix"] * (1 - conv_rate)).to_numpy()
    return p_conv / p_conv.sum(), p_pros / p_pros.sum()


def assign_converter_channels(q_pct: np.ndarray, marketing_only_rate: float,
                              rng: np.random.Generator) -> np.ndarray:
    """Channel per converter (person grain), mix draw tilted by quality
    percentile (q_tilt) -- high-intent channels deliver better applicants."""
    a = ACQ_CHANNELS
    p_conv, _ = converter_prospect_mixes(marketing_only_rate)
    probs = p_conv[None, :] * (1 + a["q_tilt"].to_numpy()[None, :]
                               * (q_pct[:, None] - 0.5))
    probs /= probs.sum(axis=1, keepdims=True)
    cum = np.cumsum(probs, axis=1)
    draw = rng.uniform(size=len(q_pct))[:, None]
    pick = np.minimum((draw >= cum).sum(axis=1), len(a) - 1)  # float-sum guard
    return a.index.to_numpy()[pick]
