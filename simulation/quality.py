"""The fitted acceptance model (lendingclub_marginals.json), shared across stages.

Moved verbatim from leads.py (C18). leads.py consumes it per application;
consumers.py consumes it once per person as the channel-assignment quality
proxy (acquisition channels moved to person grain so identity drift can
depend on them, while preserving C16's channel-quality correlation).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


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
