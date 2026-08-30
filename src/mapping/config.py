"""Configuration dataclasses for 2.5D Semantic Elevation Mapping.

Ingests mapping parameters from `configs/default_config.yaml` or provides safe,
robust defaults according to the SIH 2026 system blueprint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


@dataclass
class TraversabilityConfig:
    """Thresholds and parameters governing traversability assessment."""

    max_drivable_slope_deg: float = 15.0  # 15 degrees max slope for drivable ground
    roughness_threshold: float = 0.05  # Height std-dev (m) threshold
    discontinuity_threshold: float = 0.10  # Maximum step height (m) for drivable ground
    unknown_occupancy_min: float = 0.20  # Minimum occupancy before assuming known state


@dataclass
class HazardConfig:
    """Thresholds governing geometric curb, pothole, and overhang detection."""

    curb_min_step: float = 0.08  # 8 cm minimum step for curb candidate
    curb_max_step: float = 0.25  # 25 cm maximum step for curb candidate
    pothole_min_depth: float = 0.05  # 5 cm depression depth for pothole candidate
    overhang_min_clearance: float = 2.2  # 2.2 m vertical clearance for overhead structure


@dataclass
class MappingConfig:
    """Global configuration for 2.5D elevation and semantic mapping."""

    occupancy_threshold: float = 0.50
    min_points_per_cell: int = 1
    occupancy_ref_points: float = 3.0  # Points count for saturating occupancy
    elevation_strategy: str = "median"  # 'median', 'mean', or 'lowest'
    traversability: TraversabilityConfig = field(default_factory=TraversabilityConfig)
    hazards: HazardConfig = field(default_factory=HazardConfig)
    foveation_resolutions: Dict[str, float] = field(
        default_factory=lambda: {
            "near": 0.05,
            "mid_near": 0.10,
            "mid": 0.25,
            "far": 0.50,
        }
    )

    @classmethod
    def from_yaml(cls, path: Optional[str | Path] = None) -> MappingConfig:
        """Load MappingConfig from configs/default_config.yaml."""
        if path is None:
            # Default to repo configs/default_config.yaml
            path = Path(__file__).resolve().parent.parent.parent / "configs" / "default_config.yaml"

        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        mapping_data = data.get("mapping", {})
        trav_data = mapping_data.get("traversability", {})
        hazards_data = mapping_data.get("hazards", {})

        # Ingest foveation resolutions if defined
        foveation_levels = data.get("foveation_levels", {})
        resolutions = {}
        for _, lvl_info in foveation_levels.items():
            name = lvl_info.get("name")
            res = lvl_info.get("resolution")
            if name and res:
                resolutions[name] = float(res)

        if not resolutions:
            resolutions = {
                "near": 0.05,
                "mid_near": 0.10,
                "mid": 0.25,
                "far": 0.50,
            }

        return cls(
            occupancy_threshold=float(mapping_data.get("occupancy_threshold", 0.50)),
            min_points_per_cell=int(mapping_data.get("min_points_per_cell", 1)),
            occupancy_ref_points=3.0,
            elevation_strategy="median",
            traversability=TraversabilityConfig(
                max_drivable_slope_deg=float(trav_data.get("max_drivable_slope_deg", 15.0)),
                roughness_threshold=float(trav_data.get("roughness_threshold", 0.05)),
                discontinuity_threshold=0.10,
                unknown_occupancy_min=0.20,
            ),
            hazards=HazardConfig(
                curb_min_step=float(hazards_data.get("curb_min_step", 0.08)),
                curb_max_step=float(hazards_data.get("curb_max_step", 0.25)),
                pothole_min_depth=float(hazards_data.get("pothole_min_depth", 0.05)),
                overhang_min_clearance=float(hazards_data.get("overhang_min_clearance", 2.2)),
            ),
            foveation_resolutions=resolutions,
        )
