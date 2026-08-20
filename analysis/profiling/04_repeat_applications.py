"""Fit the repeat-application distribution from the private source table.

Usage:
    .venv/bin/python analysis/profiling/04_repeat_applications.py

Source: a leads-per-contact histogram over one year of a real personal-loan
lead marketplace, provided by the author from industry experience (P-010).
The raw table lives in git-ignored data/private/repeat_apps_source.csv and is
never committed (conventions Section 2); this script distills it into
simulation/params/repeat_applications.json -- a fitted two-parameter form
plus QA targets rounded to two significant figures, which is what the
simulator and its tests consume (A1).

Model: discrete power law with exponential cutoff on k = 1..cap,
P(k) proportional to k^(-alpha) * exp(-k/lam). Buckets are fitted by
minimizing chi-square distance between bucket masses.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "data" / "private" / "repeat_apps_source.csv"
OUT = REPO_ROOT / "simulation" / "params" / "repeat_applications.json"
CAP = 150  # 100+ bucket is real (brokers/heavy shoppers); cap the support


def bucket_bounds(label: str) -> tuple[int, int]:
    if "-" in label:
        lo, hi = label.split("-")
        return int(lo), int(hi)
    if label.endswith("+"):
        return int(label[:-1]), CAP
    return int(label), int(label)


def pmf(alpha: float, lam: float) -> np.ndarray:
    k = np.arange(1, CAP + 1, dtype=float)
    w = k ** (-alpha) * np.exp(-k / lam)
    return w / w.sum()


def main() -> None:
    src = pd.read_csv(SOURCE, dtype={"leads_per_contact": str})
    src["share"] = src["contacts"] / src["contacts"].sum()
    bounds = [bucket_bounds(s) for s in src["leads_per_contact"]]

    def bucket_masses(p: np.ndarray) -> np.ndarray:
        return np.array([p[lo - 1:hi].sum() for lo, hi in bounds])

    def loss(theta: np.ndarray) -> float:
        p = pmf(theta[0], np.exp(theta[1]))
        m = bucket_masses(p)
        return float(((m - src["share"]) ** 2 / np.maximum(m, 1e-12)).sum())

    fit = minimize(loss, x0=np.array([1.2, np.log(20.0)]), method="Nelder-Mead",
                   options={"xatol": 1e-6, "fatol": 1e-12, "maxiter": 4000})
    alpha, lam = float(fit.x[0]), float(np.exp(fit.x[1]))
    p = pmf(alpha, lam)
    mean = float((np.arange(1, CAP + 1) * p).sum())
    m = bucket_masses(p)

    print(f"alpha={alpha:.4f} lam={lam:.2f} mean={mean:.3f} loss={fit.fun:.6f}")
    for (lo, hi), fitted, obs in zip(bounds, m, src["share"]):
        print(f"  k={lo:>3}-{hi:<3} fitted={fitted:.4f} source={obs:.4f}")

    # QA targets rounded to 2 s.f.: what the tests gate on. The raw table
    # stays private; these rounded shares are the declared assumption.
    artifact = {
        "provenance": ("Declared assumption informed by the author's industry "
                       "experience in personal-loan lead marketplaces (P-010); "
                       "fitted from a private source table not committed to "
                       "the repository (conventions Section 2). Fit: discrete "
                       "power law with exponential cutoff, chi-square on "
                       "bucket masses."),
        "model": "P(k) ~ k^-alpha * exp(-k/lam), k = 1..cap",
        "alpha": round(alpha, 4),
        "lam": round(lam, 3),
        "cap": CAP,
        "qa_targets_2sf": {
            "p1": round(float(m[0]), 2),
            "p2": round(float(m[1]), 2),
            "p3": round(float(m[2]), 2),
            "mass_le_10": round(float(m[:10].sum()), 2),
            "mean": round(mean, 1),
        },
    }
    OUT.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
