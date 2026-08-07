"""Lead generation engine — the production implementation of design.md Section 3.2 stage 2.

Each consumer record submits 1-3 loan applications over the configured window.
The application-count mix is C14 (P(1)=0.55, P(2)=0.30, P(3)=0.15, mean exactly
1.60), so full scale yields the design's 2.4M leads from 1.5M consumer records.
First applications request the consumer's copula-drawn amount; repeat
applications re-request with an upward-biased seeded multiplier — the ratified
domain picture (P-007) is that small-loan borrowers return for more. All lead
amounts snap to $25 increments, as real application forms do.

The lead quality score q — the waterfall's conditioning input — comes from the
acceptance model fitted in ``lendingclub_marginals.json``: the standardized
linear score, consumed as its within-cohort percentile rank (C11), which makes
q uniform on (0,1) by construction. Generated consumers always carry observed
employment tenure, so the model's missingness indicator is identically zero
here (the n/a bucket is excluded at the consumer stage by the notebook's own
construction).

Timestamps are UTC-naive and daytime-skewed; per consumer, application times
are sorted so ``app_seq`` increases with ``submitted_at``. Silo timezone
pathologies are a fracture-stage concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json
import numpy as np
import pandas as pd
from scipy import stats

from simulation.consumers import _uuid4

# C14: applications per consumer record; mean 1.60 meets Section 3.3 exactly
APP_COUNTS = np.array([1, 2, 3])
APP_PROBS = np.array([0.55, 0.30, 0.15])

# Repeat applications re-request more on average: exp(N(0.15, 0.30)) has a
# median multiplier of ~1.16 with realistic spread (declared assumption, C14)
REPEAT_LOG_MEAN, REPEAT_LOG_SD = 0.15, 0.30
AMOUNT_STEP, AMOUNT_MIN, AMOUNT_MAX = 25.0, 500.0, 40_000.0

# Submission time of day: daytime-skewed normal in seconds (declared assumption)
TOD_MEAN_S, TOD_SD_S = 14 * 3600.0, 4.5 * 3600.0


@dataclass(frozen=True)
class QualityModel:
    """The fitted acceptance model, loaded verbatim from the artifact."""

    mean: np.ndarray
    std: np.ndarray
    coef: np.ndarray
    intercept: float

    @classmethod
    def from_params_dir(cls, params_dir: Path | str) -> "QualityModel":
        p = json.loads(
            (Path(params_dir) / "lendingclub_marginals.json").read_text()
        )["quality_score"]
        assert p["features"] == ["log_amnt", "dti", "emp_years_f", "emp_missing"]
        return cls(mean=np.asarray(p["standardize_mean"]),
                   std=np.asarray(p["standardize_std"]),
                   coef=np.asarray(p["coef"]),
                   intercept=float(p["intercept"]))

    def score(self, loan_amnt: np.ndarray, dti: np.ndarray,
              emp_years: np.ndarray) -> np.ndarray:
        """Raw linear acceptance score; emp_missing is 0 for generated consumers."""
        x = np.column_stack([np.log1p(loan_amnt), dti, emp_years,
                             np.zeros(len(loan_amnt))])
        return (x - self.mean) / self.std @ self.coef + self.intercept


def _snap(amount: np.ndarray) -> np.ndarray:
    return np.clip(np.round(amount / AMOUNT_STEP) * AMOUNT_STEP,
                   AMOUNT_MIN, AMOUNT_MAX)


def build_leads(consumers: pd.DataFrame, qm: QualityModel, months: int,
                window_start: str, rng: np.random.Generator) -> pd.DataFrame:
    """The full lead table: 1-3 applications per consumer record, quality-scored.

    Rows come out sorted by submitted_at — the natural event ordering, which the
    fracture stage's sequential CRM lead_id will follow.
    """
    n_apps = rng.choice(APP_COUNTS, size=len(consumers), p=APP_PROBS)
    rec = np.repeat(np.arange(len(consumers)), n_apps)  # contiguous per record
    n = len(rec)

    # Submission times: uniform day in the window + daytime-skewed time of day,
    # then sorted within each consumer record so app_seq follows real order
    n_days = int(months * 365.25 / 12)
    t = rng.integers(0, n_days, size=n) * 86_400.0 \
        + np.clip(rng.normal(TOD_MEAN_S, TOD_SD_S, size=n), 0, 86_399)
    t = t[np.lexsort((t, rec))]
    starts = np.r_[0, np.cumsum(n_apps)[:-1]]
    app_seq = np.arange(n) - np.repeat(starts, n_apps) + 1
    submitted_at = pd.Timestamp(window_start) + pd.to_timedelta(t, unit="s")

    # Application amount: the consumer's copula anchor on first application,
    # upward-biased re-request on repeats; all snapped to form increments
    anchor = consumers["loan_amnt"].to_numpy()[rec]
    mult = np.exp(rng.normal(REPEAT_LOG_MEAN, REPEAT_LOG_SD, size=n))
    loan_amnt = _snap(np.where(app_seq == 1, anchor, anchor * mult))

    # Consumer-level features carried onto each application
    carried = consumers.iloc[rec][
        ["consumer_record_id", "purpose", "dti", "annual_inc", "fico_mid",
         "fico_band", "emp_length", "emp_years", "addr_state"]
    ].reset_index(drop=True)

    # Quality: fitted acceptance score -> within-cohort percentile rank (C11)
    z = qm.score(loan_amnt, carried["dti"].to_numpy(),
                 carried["emp_years"].to_numpy())
    q = stats.rankdata(z) / (n + 1)

    leads = pd.concat([
        pd.DataFrame({"lead_uuid": _uuid4(n, rng), "app_seq": app_seq,
                      "submitted_at": submitted_at, "loan_amnt": loan_amnt,
                      "q": q}),
        carried,
    ], axis=1)
    return leads.sort_values("submitted_at", kind="stable").reset_index(drop=True)
