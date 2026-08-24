"""Recency-dependent buyer demand (C19, P-011).

Buyers in real lead marketplaces suppress or discount consumers they have
seen recently (shared dedupe vendors, buyer-side CRM matching), so a lead
whose person applied days ago wins less often and clears lower. The effect
is calibrated from the author's industry duplicate-performance table
(P-011; raw table git-ignored in ``data/private/``, per the conventions
Section 2 redaction rule). The committed artifact
(``simulation/params/repeat_demand.json``) carries only the distilled form:
recency-bucket edges, KPI *ratio* targets (recent vs fresh), and the engine
dials fitted to hit them (``analysis/profiling/05_repeat_demand.py``).

Level discipline (the C15e/C16 pattern): the ratios carry the realism, the
levels stay calibrated -- the fresh bucket's dials are fitted so the
*overall* sell-through and mean clearing price match the pre-C19 engine, so
C2's censoring band and the C1 price anchor are untouched.

The same artifact carries the funded-price gradient (also C19): the CRM
funded flag becomes a mean-preserving logistic in log clearing price, so
higher-priced leads fund modestly more often (supersedes C17d's uniform
draw; the artifact rate is still the mean).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json
import numpy as np

N_BUCKETS = 4  # 0: <1d, 1: 1-7d, 2: 7-30d, 3: fresh (first-ever or >=30d)


@dataclass(frozen=True)
class RepeatDemand:
    """Fitted recency dials, loaded verbatim from the artifact."""

    edges: np.ndarray       # day edges between buckets, e.g. [1, 7, 30]
    odds_mult: np.ndarray   # participation odds multiplier per bucket (0..3)
    price_mult: np.ndarray  # valuation multiplier per bucket (0..3)
    funded_beta: float      # funded log-odds slope on log clearing price

    @classmethod
    def from_params_dir(cls, params_dir: Path | str) -> "RepeatDemand":
        p = json.loads((Path(params_dir) / "repeat_demand.json").read_text())
        return cls(
            edges=np.asarray(p["buckets"]["day_edges"], dtype=float),
            odds_mult=np.asarray(p["fitted_dials"]["participation_odds_mult"]),
            price_mult=np.asarray(p["fitted_dials"]["valuation_mult"]),
            funded_beta=p["funded_price_gradient"]["beta"],
        )

    def bucket(self, days_since_prior: np.ndarray) -> np.ndarray:
        """Recency bucket per lead: NaN (first application) -> fresh."""
        d = np.asarray(days_since_prior, dtype=float)
        b = np.searchsorted(self.edges, np.nan_to_num(d, nan=np.inf), side="right")
        return b.astype(np.int8)


def funded_flags(price: np.ndarray, mean_rate: float, beta: float,
                 rng: np.random.Generator) -> np.ndarray:
    """Price-dependent funded draw among sold leads, mean preserved (C19).

    Logistic in beta * (log price - log median), with the intercept solved by
    bisection so the pool mean equals the artifact rate -- the C17d rate is
    kept as the level; the gradient is the amendment.
    """
    x = beta * (np.log(price) - np.log(np.median(price)))
    lo, hi = -20.0, 20.0
    for _ in range(60):
        c = (lo + hi) / 2
        if (1 / (1 + np.exp(-(c + x)))).mean() < mean_rate:
            lo = c
        else:
            hi = c
    p = 1 / (1 + np.exp(-((lo + hi) / 2 + x)))
    return rng.uniform(size=len(price)) < p
