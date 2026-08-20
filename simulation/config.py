from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BASE_PERSONS = 639_000  # 100%-scale persons: 2.4M lead target / 3.756 fitted
                        # mean apps per person (C18, repeat_applications.json)


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

    # Pathology dials (docs/calibration_spec.md §4; drift dials are C18/D8)
    orphan_rate: float = 0.05
    marketing_only_rate: float = 0.10
    # Identity-drift hazard per return gap, by channel intent tier: messy
    # low-intent channels ship messier data (human directive, P-010).
    drift_hazard: dict = field(default_factory=lambda: {
        "high": 0.10, "mid": 0.18, "low": 0.30})
    # Per-drift-event mutation probabilities (>= 1 enforced per event)
    mutation_probs: dict = field(default_factory=lambda: {
        "new_phone": 0.45, "new_email": 0.40, "name_form": 0.35,
        "moved_zip": 0.18})

    @property
    def n_persons(self) -> int:
        return max(1, int(BASE_PERSONS * self.scale))

    def ensure_dirs(self) -> None:
        for d in (self.out_dir, self.private_dir):
            d.mkdir(parents=True, exist_ok=True)
