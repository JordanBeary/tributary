from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BASE_CONSUMERS = 1_500_000  # 100%-scale consumer count (design.md §3.2)


@dataclass
class SimConfig:
    seed: int = 42
    scale: float = 1.0  # 0.01 = 1% dev runs; 1.0 = full deploy
    months: int = 12  # application window
    # Window epoch: submissions span [window_start, window_start + months).
    # Fixed date so timestamps are reproducible; silo timezone pathologies
    # are applied at the fracture stage, so pipeline timestamps are UTC-naive.
    window_start: str = "2025-07-01"
    out_dir: Path = Path("data/generated")
    params_dir: Path = Path("simulation/params")
    # The crosswalk is the hidden ground truth: local only, git-ignored,
    # never uploaded to any silo (design.md §2.4).
    private_dir: Path = Path("data/private")

    # Pathology dials (docs/calibration_spec.md §4)
    duplicate_rate: float = 0.08
    orphan_rate: float = 0.05
    marketing_only_rate: float = 0.10

    @property
    def n_consumers(self) -> int:
        return max(1, int(BASE_CONSUMERS * self.scale))

    def ensure_dirs(self) -> None:
        for d in (self.out_dir, self.private_dir):
            d.mkdir(parents=True, exist_ok=True)
