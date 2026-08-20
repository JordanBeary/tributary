"""Lead generation engine — the production implementation of design.md Section 3.2 stage 2.

Application counts are drawn per *person* in the consumer stage (heavy-tailed,
C18/P-010, superseding the C14 1-3 mix) and allocated to identity-variant
records there; this stage submits each record's n_apps applications, ordered
in time per person so variant_seq follows submission order. First applications
request the consumer's copula-drawn amount; repeat applications re-request
with an upward-biased seeded multiplier — the ratified domain picture (P-007)
is that small-loan borrowers return for more. All lead amounts snap to $25
increments, as real application forms do.

The lead quality score q — the waterfall's conditioning input — comes from the
acceptance model fitted in ``lendingclub_marginals.json``: the standardized
linear score, consumed as its within-cohort percentile rank (C11), which makes
q uniform on (0,1) by construction. Generated consumers always carry observed
employment tenure, so the model's missingness indicator is identically zero
here (the n/a bucket is excluded at the consumer stage by the notebook's own
construction).

Timestamps are UTC-naive and daytime-skewed; per person, application times
are sorted so ``app_seq`` increases with ``submitted_at`` across variants.
Silo timezone pathologies are a fracture-stage concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json
import numpy as np
import pandas as pd
from scipy import stats

from simulation.consumers import _uuid4
from simulation.quality import QualityModel  # re-export for stage wiring

# Repeat applications re-request more on average: exp(N(0.15, 0.30)) has a
# median multiplier of ~1.16 with realistic spread (declared assumption, C14)
REPEAT_LOG_MEAN, REPEAT_LOG_SD = 0.15, 0.30
AMOUNT_STEP, AMOUNT_MIN, AMOUNT_MAX = 25.0, 500.0, 40_000.0

# Submission time of day: daytime-skewed normal in seconds (declared assumption)
TOD_MEAN_S, TOD_SD_S = 14 * 3600.0, 4.5 * 3600.0


def _snap(amount: np.ndarray) -> np.ndarray:
    return np.clip(np.round(amount / AMOUNT_STEP) * AMOUNT_STEP,
                   AMOUNT_MIN, AMOUNT_MAX)


def build_leads(consumers: pd.DataFrame, qm: QualityModel, months: int,
                window_start: str, rng: np.random.Generator) -> pd.DataFrame:
    """The full lead table: 1-3 applications per consumer record, quality-scored.

    Rows come out sorted by submitted_at — the natural event ordering, which the
    fracture stage's sequential CRM lead_id will follow.
    """
    # Records ordered person-contiguous with variants in sequence, so each
    # person's earlier-variant applications get the earlier timestamps.
    order = np.lexsort((consumers["variant_seq"].to_numpy(),
                        consumers["consumer_key"].to_numpy()))
    consumers = consumers.iloc[order].reset_index(drop=True)
    n_apps = consumers["n_apps"].to_numpy()
    rec = np.repeat(np.arange(len(consumers)), n_apps)
    n = len(rec)

    # Person id per app (variants of one person are contiguous after the sort)
    person = consumers["consumer_key"].to_numpy()[rec]
    person_change = np.r_[True, person[1:] != person[:-1]]
    person_id = np.cumsum(person_change) - 1

    # Submission times: uniform day in the window + daytime-skewed time of day,
    # then sorted within each *person* so app_seq follows real order across
    # that person's identity variants
    n_days = int(months * 365.25 / 12)
    t = rng.integers(0, n_days, size=n) * 86_400.0 \
        + np.clip(rng.normal(TOD_MEAN_S, TOD_SD_S, size=n), 0, 86_399)
    t = t[np.lexsort((t, person_id))]
    p_starts = np.flatnonzero(person_change)
    p_counts = np.diff(np.r_[p_starts, n])
    app_seq = np.arange(n) - np.repeat(p_starts, p_counts) + 1
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
