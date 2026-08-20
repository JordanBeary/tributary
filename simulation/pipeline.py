from __future__ import annotations

import logging
import time

from simulation import stages
from simulation.config import SimConfig

log = logging.getLogger("simulation")

# Ordered pipeline (design.md §3.2). Each stage reads its inputs from
# cfg.out_dir and writes its outputs there, so stages can be re-run singly.
STAGES = {
    "consumers": stages.generate_consumers,
    "leads": stages.generate_leads,
    "waterfall": stages.run_waterfall,
    "marketing": stages.generate_marketing,
    "fracture": stages.fracture_into_silos,
}


def run_pipeline(cfg: SimConfig, only: str | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg.ensure_dirs()
    to_run = {only: STAGES[only]} if only else STAGES
    log.info(
        "scale=%s seed=%s -> %s persons; stages: %s",
        cfg.scale, cfg.seed, f"{cfg.n_persons:,}", ", ".join(to_run),
    )
    for name, fn in to_run.items():
        t0 = time.perf_counter()
        fn(cfg)
        log.info("stage %s done in %.1fs", name, time.perf_counter() - t0)
