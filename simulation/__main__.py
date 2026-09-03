"""Run the marketplace simulation pipeline.

Usage:
    python -m simulation --scale 0.01 --seed 42
    python -m simulation --stage consumers          # run a single stage
    python -m simulation --scale 0.2 --floor-multipliers 1.2,0.7,0.45,0.3,0.2,0.2
"""

from __future__ import annotations

import argparse
from pathlib import Path

from simulation.config import SimConfig
from simulation.pipeline import STAGES, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulation", description=__doc__)
    parser.add_argument("--scale", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--out-dir", type=Path, default=Path("data/generated"))
    parser.add_argument(
        "--floor-multipliers", type=str, default=None,
        help="Six comma-separated per-tier multipliers on the calibrated reserve "
             "floors, tier 1 first (Phase 6 validation, D18); omit for the "
             "deployed schedule",
    )
    parser.add_argument(
        "--stage",
        choices=list(STAGES),
        default=None,
        help="Run a single stage (expects upstream stage outputs to exist)",
    )
    args = parser.parse_args()

    # Optional reserve-schedule override; None keeps the deployed floors
    floors = (tuple(float(x) for x in args.floor_multipliers.split(","))
              if args.floor_multipliers else None)
    cfg = SimConfig(
        seed=args.seed, scale=args.scale, months=args.months, out_dir=args.out_dir,
        floor_multipliers=floors,
    )
    run_pipeline(cfg, only=args.stage)


if __name__ == "__main__":
    main()
