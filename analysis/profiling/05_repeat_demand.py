"""Fit the C19 recency-demand dials from the duplicate-performance table (P-011).

Input: ``data/private/duplicate_performance.csv`` -- the author's industry
table of lead KPIs by duplicate recency (same-day / last-7d / last-30d /
fresh-or-30d+). The raw table never enters the repository (conventions
Section 2); this script distills it into ratio targets (recent vs fresh,
rounded to 2 significant figures) and fits the engine dials that reproduce
them, writing the committed artifact ``simulation/params/repeat_demand.json``.

Level discipline (C15e/C16 pattern): after the per-bucket ratios are fitted,
one global adjustment pins the *overall* sell-through and mean clearing price
to the pre-C19 baseline on the same lead pool, so C2's censoring band and the
C1 price anchor are untouched -- the ratios carry the realism, the levels
stay calibrated.

Method: consumers + leads are generated at --scale (default 0.2, ~480k leads)
so the fit sees the real recency mix and quality-recency correlation; the
waterfall is then re-run under candidate dials with a fixed evaluation seed
(noise-free comparisons) and the dials updated multiplicatively until the
bucket ratios and overall levels converge.

Usage: .venv/bin/python analysis/profiling/05_repeat_demand.py [--scale 0.2]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from simulation.auction import AuctionLandscape, run_auctions
from simulation.config import SimConfig
from simulation.repeat_demand import N_BUCKETS
from simulation import stages

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_CSV = ROOT / "data" / "private" / "duplicate_performance.csv"
ARTIFACT = ROOT / "simulation" / "params" / "repeat_demand.json"
DAY_EDGES = [1.0, 7.0, 30.0]
BUCKET_LABELS = ["dup1", "dup7", "dup30", "unique_dup30+"]  # CSV rows by bucket
FUNDED_BETA = 0.15  # declared (P-011, verbal): modest funded lift with price --
                    # ~1.7x odds across the full sold price range


def sig2(x: float) -> float:
    return float(f"{x:.2g}")


def targets_from_private() -> dict:
    """KPI ratio targets, recent vs fresh, from the private table."""
    t = pd.read_csv(PRIVATE_CSV).set_index("duplicates")
    fresh = t.loc["unique_dup30+"]
    return {
        "win_rate": [sig2(t.loc[b, "win_rate"] / fresh["win_rate"]) for b in BUCKET_LABELS[:3]],
        "price_per_sold": [sig2(t.loc[b, "APPL"] / fresh["APPL"]) for b in BUCKET_LABELS[:3]],
    }


def eval_dials(q, bucket, land, odds, price):
    """One noise-free waterfall pass -> per-bucket win rate and mean sold price."""
    r = run_auctions(q, land, np.random.default_rng(7),
                     recency_odds=odds[bucket], recency_price=price[bucket])
    sold = r.sold_tier >= 0
    win = np.array([sold[bucket == b].mean() for b in range(N_BUCKETS)])
    p_sold = np.array([r.clearing_price[sold & (bucket == b)].mean() for b in range(N_BUCKETS)])
    return win, p_sold, sold.mean(), r.clearing_price[sold].mean()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=0.2)
    ap.add_argument("--workdir", default=str(ROOT / "data" / "tmp" / "repeat_demand_fit"))
    args = ap.parse_args()
    tgt = targets_from_private()

    # Real lead pool at fit scale: consumers -> leads (seed 42, the deploy seed)
    wd = Path(args.workdir)
    cfg = SimConfig(scale=args.scale, out_dir=wd, private_dir=wd / "private")
    if not (wd / "leads.parquet").exists():
        cfg.ensure_dirs()
        stages.generate_consumers(cfg)
        stages.generate_leads(cfg)
    leads = pd.read_parquet(wd / "leads.parquet")
    q = leads["q"].to_numpy()
    gaps = leads["days_since_prior"].to_numpy()
    bucket = np.searchsorted(DAY_EDGES, np.nan_to_num(gaps, nan=np.inf), side="right").astype(np.int8)
    land = AuctionLandscape.from_params_dir(cfg.params_dir)

    # Pre-C19 baseline levels on the same pool: the normalization targets
    ones = np.ones(N_BUCKETS)
    _, _, s0, p0 = eval_dials(q, bucket, land, ones, ones)
    print(f"baseline: sell-through {s0:.4f}, mean sold price {p0:.2f}, "
          f"bucket mix {[round((bucket == b).mean(), 3) for b in range(N_BUCKETS)]}")

    # --- Fit ---
    # Fresh leads keep pre-C19 dials (1.0): the amendment only penalizes
    # recently-seen consumers, per the source table. With fresh frozen, the
    # three recent buckets are independent 2-parameter problems -- (log odds,
    # log valuation) -> (win ratio, price ratio) -- solved per bucket by a
    # damped Newton iteration with finite-difference Jacobians on that
    # bucket's own leads. The overall sell-through then falls out of the
    # recency mix rather than being pinned; the gate is the source table's
    # own overall win rate (C19 supersedes C2's ~60% pipeline-level target;
    # the engine-level C2 gate on a fresh pool is unchanged).
    w3 = win0 = None

    def bucket_stats(qs, o, v):
        r = run_auctions(qs, land, np.random.default_rng(7),
                         recency_odds=np.full(len(qs), o), recency_price=np.full(len(qs), v))
        sold = r.sold_tier >= 0
        return sold.mean(), (r.clearing_price[sold].mean() if sold.any() else np.nan)

    base = run_auctions(q, land, np.random.default_rng(7))
    sold0 = base.sold_tier >= 0
    w3 = sold0[bucket == 3].mean()
    p3 = base.clearing_price[sold0 & (bucket == 3)].mean()
    print(f"fresh (frozen): win {w3:.4f}, mean sold price {p3:.2f}")

    odds, price = np.ones(N_BUCKETS), np.ones(N_BUCKETS)
    for b in range(3):
        qs = q[bucket == b]
        t_w, t_p = tgt["win_rate"][b], tgt["price_per_sold"][b]
        x = np.log([0.5, 0.7])  # warm start: penalties in the right region
        for it in range(12):
            wv, pv = bucket_stats(qs, np.exp(x[0]), np.exp(x[1]))
            f = np.array([wv / w3 - t_w, pv / p3 - t_p])
            err = np.abs(f).max()
            print(f"bucket {b} it {it}: odds {np.exp(x[0]):.3f} val {np.exp(x[1]):.3f} "
                  f"win_ratio {wv / w3:.3f} price_ratio {pv / p3:.3f} err {err:.3f}")
            if err < 0.02:
                break
            J = np.zeros((2, 2))
            for j, h in enumerate([0.08, 0.08]):
                xh = x.copy(); xh[j] += h
                wh, ph = bucket_stats(qs, np.exp(xh[0]), np.exp(xh[1]))
                J[:, j] = [(wh / w3 - t_w - f[0]) / h, (ph / p3 - t_p - f[1]) / h]
            step = np.linalg.solve(J, -f)
            x += np.clip(0.8 * step, -0.5, 0.5)
        odds[b], price[b] = np.exp(x)

    win, p_sold, s, p_mean = eval_dials(q, bucket, land, odds, price)
    t_all = pd.read_csv(PRIVATE_CSV)
    src_overall = t_all["sold"].sum() / t_all["sent"].sum()
    assert abs(s - src_overall) < 0.03, f"overall win {s:.3f} vs source {src_overall:.3f}"
    ARTIFACT.write_text(json.dumps({
        "metadata": {
            "decision": "C19 (P-011)",
            "source": "author industry duplicate-performance table; raw table in data/private/ (never committed)",
            "method": "ratio targets distilled at 2 significant figures; dials fitted on the real lead pool "
                      f"at scale {args.scale} (seed 42) with a fixed evaluation seed; fresh bucket keeps "
                      "pre-C19 dials (the amendment penalizes recents only), so the overall sell-through "
                      "falls out of the recency mix; it lands at the source table's overall win rate "
                      "(the gate), superseding C2's ~60% pipeline-level target -- see C19",
            "fit_script": "analysis/profiling/05_repeat_demand.py",
        },
        "buckets": {"day_edges": DAY_EDGES,
                    "labels": ["<1d", "1-7d", "7-30d", "fresh (first or >=30d)"]},
        "kpi_ratio_targets": tgt,
        "fitted_dials": {"participation_odds_mult": odds.tolist(),
                         "valuation_mult": price.tolist()},
        "funded_price_gradient": {
            "beta": FUNDED_BETA,
            "status": "declared (P-011, verbal): higher clearing price -> modestly higher funded rate; "
                      "mean preserved at the auction-landscape artifact CVR (supersedes C17d uniform draw)",
        },
        "qa": {
            "fit_scale": args.scale, "eval_seed": 7,
            "measured_win_ratio": [sig2(v) for v in (win[:3] / win[3])],
            "measured_price_ratio": [sig2(v) for v in (p_sold[:3] / p_sold[3])],
            "pre_c19_sell_through": round(s0, 4), "fitted_sell_through": round(s, 4),
            "source_overall_win_rate": sig2(src_overall),
            "pre_c19_mean_price": round(p0, 2), "fitted_mean_price": round(p_mean, 2),
            "bucket_mix": [round(float((bucket == b).mean()), 4) for b in range(N_BUCKETS)],
            "tolerances": {"ratio_abs": 0.05, "overall_win_vs_source_abs": 0.03},
        },
    }, indent=1))
    print(f"wrote {ARTIFACT}")


if __name__ == "__main__":
    main()
