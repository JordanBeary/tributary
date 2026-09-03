"""Phase 6 validation: re-run the engine at model 3's recommended reserve
schedule and measure the realized lift with a seed band (design Section 9,
Phase 6 exit: "simulated EPL lift quantified with uncertainty bands").

Model 3 (models/optimize_floors.py) estimated +2.02% revenue per lead by
replaying logged bids under the recommended schedule. That replay is exact
where the logged cascade reached and hot-deck imputed where it did not. This
script closes the loop by generating fresh worlds and running the waterfall
itself under both schedules, so the imputation is never used.

Method (D18, pending ratification):
  * For each seed, consumers and leads are generated at --scale (default 0.2,
    about 480k leads) into data/tmp/floor_validation/seed_<s>/ -- the stage
    functions in simulation/stages.py, with out_dir and private_dir redirected
    so data/generated and data/private are never touched.
  * The waterfall runs under the deployed schedule and under the recommended
    schedule with the same stage RNG (SeedSequence([seed, 3]), exactly as
    stages.run_waterfall) and the same C19 recency dials, so each seed is a
    paired comparison (common random numbers) and the per-seed lift is a
    paired difference. Deployed at seed 42 reproduces the pipeline's own
    auction outcomes at that scale.
  * Bid-shading stress test. Bids are invariant to reserves in this engine;
    real buyers may give some of a floor increase back. Shading level s means
    buyers at a tier whose floor rose by factor m > 1 lower their valuations by
    the share s of that increase: valuation multiplier 1 - s * (m - 1). Tiers
    whose floor was cut are unaffected. s = 0 is the engine as built; s = 1
    means buyers absorb the whole increase. Implemented as a shift of the
    landscape's per-tier log-location (mu_t + log(multiplier)) via
    dataclasses.replace -- no engine code path changes.
  * Reported per schedule and shading level: revenue per lead, sell-through,
    tier revenue mix; per-seed paired lift; mean, standard deviation, min and
    max across seeds; the replay's prediction alongside; the shading level at
    which the realized lift crosses zero (linear interpolation).

Outputs: models/out/m3_validation.json and models/out/m3_validation.html.
Usage: .venv/bin/python models/validate_floors.py [--scale 0.2] [--seeds 42,43,44,45,46]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import report
from models.common import N_TIERS, OUT_DIR, ROOT
from simulation import stages
from simulation.auction import AuctionLandscape, run_auctions
from simulation.config import SimConfig
from simulation.repeat_demand import RepeatDemand

WORKDIR = ROOT / "data" / "tmp" / "floor_validation"
# Shading grid: the four levels the plan asked for, plus three deeper points
# so the zero crossing (break-even shading) is bracketed rather than guessed.
SHADING = [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 1.00]


def lead_pool(seed: int, scale: float) -> pd.DataFrame:
    """Consumers + leads for one seed, generated once and cached under data/tmp."""
    wd = WORKDIR / f"seed_{seed}"
    cfg = SimConfig(seed=seed, scale=scale, out_dir=wd, private_dir=wd / "private")
    if not (wd / "leads.parquet").exists():
        cfg.ensure_dirs()
        stages.generate_consumers(cfg)
        stages.generate_leads(cfg)
    return pd.read_parquet(wd / "leads.parquet", columns=["q", "days_since_prior"])


def shaded_landscape(land: AuctionLandscape, mult: np.ndarray, s: float) -> AuctionLandscape:
    """Recommended schedule with buyers giving back share s of any floor increase."""
    give_back = 1.0 - s * np.maximum(mult - 1.0, 0.0)
    return dataclasses.replace(land, floors=land.floors * mult, mu=land.mu + np.log(give_back))


def run_world(leads: pd.DataFrame, land: AuctionLandscape, demand: RepeatDemand, seed: int) -> dict:
    """One waterfall pass with the pipeline's own RNG stream and recency dials."""
    bucket = demand.bucket(leads["days_since_prior"].to_numpy())
    rng = np.random.default_rng(np.random.SeedSequence([seed, 3]))
    r = run_auctions(leads["q"].to_numpy(), land, rng,
                     recency_odds=demand.odds_mult[bucket], recency_price=demand.price_mult[bucket])
    sold = r.sold_tier >= 0
    n = len(leads)
    tier_rev = [float(r.clearing_price[sold & (r.sold_tier == t)].sum()) / n for t in range(N_TIERS)]
    return dict(revenue_per_lead=float(r.clearing_price.sum() / n), sell_through=float(sold.mean()),
                tier_revenue_per_lead=tier_rev,
                tier_sell_through=[float((sold & (r.sold_tier == t)).mean()) for t in range(N_TIERS)])


def summarize(values: list[float]) -> dict:
    a = np.asarray(values)
    return dict(mean=float(a.mean()), sd=float(a.std(ddof=1)) if len(a) > 1 else 0.0,
                min=float(a.min()), max=float(a.max()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=0.2)
    ap.add_argument("--seeds", type=str, default="42,43,44,45,46")
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",")]

    m3 = json.loads((OUT_DIR / "m3_metrics.json").read_text())
    mult = np.asarray(m3["recommended_multipliers"], dtype=float)
    land = AuctionLandscape.from_params_dir(ROOT / "simulation" / "params")
    assert np.allclose(land.floors, m3["deployed_floors"]), "artifact floors differ from model 3's deployed schedule"
    demand = RepeatDemand.from_params_dir(ROOT / "simulation" / "params")

    t0 = time.perf_counter()
    per_seed = []
    for seed in seeds:
        leads = lead_pool(seed, args.scale)
        deployed = run_world(leads, land, demand, seed)
        rec = {s: run_world(leads, shaded_landscape(land, mult, s), demand, seed) for s in SHADING}
        per_seed.append(dict(seed=seed, n_leads=len(leads), deployed=deployed,
                             recommended={str(s): rec[s] for s in SHADING},
                             lift={str(s): rec[s]["revenue_per_lead"] / deployed["revenue_per_lead"] - 1
                                   for s in SHADING}))
        print(f"seed {seed}: n={len(leads):,} deployed ${deployed['revenue_per_lead']:.2f}/lead "
              f"st {deployed['sell_through']:.3f}; lift s=0 {per_seed[-1]['lift']['0.0']:+.2%}, "
              f"s=0.2 {per_seed[-1]['lift']['0.2']:+.2%}, s=1 {per_seed[-1]['lift']['1.0']:+.2%} "
              f"[{time.perf_counter() - t0:.0f}s]")

    # Bands across seeds, per shading level
    band = {str(s): summarize([p["lift"][str(s)] for p in per_seed]) for s in SHADING}
    levels = dict(
        deployed=summarize([p["deployed"]["revenue_per_lead"] for p in per_seed]),
        recommended={str(s): summarize([p["recommended"][str(s)]["revenue_per_lead"] for p in per_seed])
                     for s in SHADING},
        sell_through_deployed=summarize([p["deployed"]["sell_through"] for p in per_seed]),
        sell_through_recommended={str(s): summarize([p["recommended"][str(s)]["sell_through"] for p in per_seed])
                                  for s in SHADING},
    )
    # Break-even shading: where the mean realized lift crosses zero
    xs, ys = np.asarray(SHADING), np.asarray([band[str(s)]["mean"] for s in SHADING])
    breakeven = None
    for i in range(len(xs) - 1):
        if ys[i] > 0 >= ys[i + 1]:
            breakeven = float(xs[i] + (xs[i + 1] - xs[i]) * ys[i] / (ys[i] - ys[i + 1]))
            break
    tier_mix = dict(
        deployed=np.mean([p["deployed"]["tier_revenue_per_lead"] for p in per_seed], axis=0).tolist(),
        recommended=np.mean([p["recommended"]["0.0"]["tier_revenue_per_lead"] for p in per_seed], axis=0).tolist(),
    )

    metrics = dict(
        method="D18: fresh worlds per seed, paired waterfall runs under deployed vs recommended "
               "schedules with common random numbers; bid-shading stress test s in SHADING",
        scale=args.scale, seeds=seeds, shading_grid=SHADING,
        replay_prediction=dict(lift=m3["expected_lift"]["mean"], ci95=m3["expected_lift"]["ci95"],
                               sell_through_recommended=m3["sell_through"]["recommended"]),
        realized_lift_by_shading=band, levels=levels, breakeven_shading=breakeven,
        tier_revenue_per_lead_mean=tier_mix, per_seed=per_seed,
        recommended_multipliers=mult.tolist(), runtime_seconds=round(time.perf_counter() - t0, 1),
    )
    report.write_metrics(OUT_DIR / "m3_validation.json", metrics)
    build_report(metrics)
    b0 = band["0.0"]
    print(f"realized lift at s=0: {b0['mean']:+.2%} (sd {b0['sd']:.2%}, range {b0['min']:+.2%}..{b0['max']:+.2%}) "
          f"vs replay {m3['expected_lift']['mean']:+.2%}; break-even shading "
          f"{'none in grid' if breakeven is None else f'{breakeven:.2f}'}")


def build_report(metrics: dict) -> None:
    band, sh = metrics["realized_lift_by_shading"], metrics["shading_grid"]
    pred = metrics["replay_prediction"]

    # Realized lift vs shading, with the across-seed range as a band
    f1 = go.Figure()
    f1.add_scatter(x=sh + sh[::-1], y=[band[str(s)]["max"] * 100 for s in sh] + [band[str(s)]["min"] * 100 for s in sh[::-1]],
                   fill="toself", fillcolor="rgba(42,120,214,0.15)", line=dict(width=0), name="seed range", hoverinfo="skip")
    f1.add_scatter(x=sh, y=[band[str(s)]["mean"] * 100 for s in sh], mode="lines+markers", name="realized lift (mean of seeds)",
                   line=dict(color=report.CAT[0], width=2), marker=dict(size=8),
                   hovertemplate="shading %{x:.2f}: %{y:+.2f}%<extra></extra>")
    f1.add_hline(y=pred["lift"] * 100, line_dash="dot", line_color=report.CAT[1],
                 annotation_text=f"replay prediction {pred['lift']:+.2%}", annotation_font_color=report.INK2)
    f1.add_hline(y=0, line_color=report.INK2, line_width=1)
    report.apply_layout(f1, title="Realized revenue lift per lead vs buyer bid shading",
                        xaxis_title="shading s: share of the tier-1 floor increase buyers give back",
                        yaxis_title="lift vs deployed schedule (%)")

    # Per-seed paired lift at s = 0
    f2 = go.Figure()
    f2.add_bar(x=[str(p["seed"]) for p in metrics["per_seed"]], y=[p["lift"]["0.0"] * 100 for p in metrics["per_seed"]],
               marker_color=report.CAT[0], hovertemplate="seed %{x}: %{y:+.2f}%<extra></extra>")
    f2.add_hline(y=pred["lift"] * 100, line_dash="dot", line_color=report.CAT[1])
    report.apply_layout(f2, title="Paired lift by seed (no shading), against the replay prediction",
                        xaxis_title="seed", yaxis_title="lift (%)", showlegend=False)

    # Where the revenue moves: tier revenue per lead, deployed vs recommended
    tm = metrics["tier_revenue_per_lead_mean"]
    f3 = go.Figure()
    f3.add_bar(name="deployed", x=[f"tier {t}" for t in range(1, 7)], y=tm["deployed"], marker_color=report.NEUTRAL,
               hovertemplate="%{x}: $%{y:.2f}/lead<extra>deployed</extra>")
    f3.add_bar(name="recommended", x=[f"tier {t}" for t in range(1, 7)], y=tm["recommended"],
               marker_color=[report.TIER_RAMP[t] for t in range(1, 7)],
               hovertemplate="%{x}: $%{y:.2f}/lead<extra>recommended</extra>")
    report.apply_layout(f3, title="Revenue per lead by selling tier (mean of seeds)",
                        yaxis_title="$ per lead offered", barmode="group",
                        yaxis=dict(type="log", gridcolor=report.GRID))

    b0 = band["0.0"]
    be = metrics["breakeven_shading"]
    tiles = [
        report.tile(f"{b0['mean']:+.2%}", f"realized lift, no shading (replay predicted {pred['lift']:+.2%})"),
        report.tile(f"{b0['min']:+.2%} .. {b0['max']:+.2%}", f"range across {len(metrics['seeds'])} seeds (sd {b0['sd']:.2%})"),
        report.tile("none in grid" if be is None else f"s = {be:.2f}", "shading at which the lift reaches zero"),
        report.tile(f"{metrics['levels']['sell_through_recommended']['0.0']['mean']:.1%}",
                    f"sell-through at the recommended schedule (deployed {metrics['levels']['sell_through_deployed']['mean']:.1%})"),
    ]
    panels = [
        report.panel("Engine-loop validation", "Fresh worlds per seed; the waterfall itself runs under both schedules "
                     "with common random numbers, so no hot-deck imputation is involved. The band is the spread of "
                     "the paired lift across seeds.", report.fig_html(f2)),
        report.panel("Stress test: buyers shade against the higher tier-1 floor", "s is the share of the floor "
                     "increase that buyers take back from their valuations at the raised tier; s = 0 is the engine "
                     "as built (bids invariant to reserves), s = 1 means the increase is fully absorbed.",
                     report.fig_html(f1)),
        report.panel("Where the lift comes from", "Tier 1 carries the revenue; the recommended schedule trades a "
                     "stiffer tier-1 reserve for far cheaper deep tiers.", report.fig_html(f3)),
    ]
    report.write_page(
        OUT_DIR / "m3_validation.html", "Model 3 — Phase 6 validation",
        f"Engine re-run at scale {metrics['scale']} for seeds {metrics['seeds']}: deployed vs recommended reserve "
        f"schedule, paired by seed, with a bid-shading stress test. Method record: D18 (pending).",
        tiles, panels,
        "Phase 6, design Section 9 exit. Rebuild: .venv/bin/python models/validate_floors.py")


if __name__ == "__main__":
    main()
