"""2.5D Semantic Mapping & Traversability Analysis Module.

Module Owner: Heet (Member 4)
Responsibilities:
    - Elevation aggregation (mean, median, min_z, max_z)
    - Semantic label fusion per cell
    - Cell occupancy and point count maintenance
    - Terrain traversability analysis (slope, roughness, step height)
    - Curb and pothole hazard detection
    - Overhang and vertical obstacle representation
"""

from src.mapping.aggregation import (
    aggregate_cell,
    aggregate_semantics,
    compute_elevation_bounds,
    compute_occupancy,
    compute_roughness,
)
from src.mapping.config import HazardConfig, MappingConfig, TraversabilityConfig
from src.mapping.mapper import SemanticElevationMapper, SimpleFoveatedGridAdapter

__all__ = [
    "MappingConfig",
    "TraversabilityConfig",
    "HazardConfig",
    "compute_elevation_bounds",
    "compute_roughness",
    "aggregate_semantics",
    "compute_occupancy",
    "aggregate_cell",
    "SemanticElevationMapper",
    "SimpleFoveatedGridAdapter",
]
