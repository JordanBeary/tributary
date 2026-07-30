"""CLX marketplace simulator.

Pipeline (design.md §3.2):
    generate_consumers -> generate_leads -> run_waterfall
        -> generate_marketing -> fracture_into_silos

All stages are seeded and scale with SimConfig.scale. Fitted distribution
parameters are read from simulation/params/*.json (produced by the profiling
notebooks per docs/calibration_spec.md) — the raw public datasets are never
read at simulation time.
"""

from simulation.config import SimConfig

__all__ = ["SimConfig"]
