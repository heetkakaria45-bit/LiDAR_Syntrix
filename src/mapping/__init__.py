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
from src.mapping.hazards import (
    CurbCandidate,
    HazardConfig,
    OverhangCell,
    PotholeCandidate,
    detect_curb_candidates,
    detect_map_hazards,
    detect_overhang_cells,
    detect_pothole_candidates,
)
from src.mapping.mapper import SemanticElevationMapper, SimpleFoveatedGridAdapter
from src.mapping.terrain import (
    TerrainAttributes,
    TraversabilityState,
    analyze_cell_terrain,
    analyze_map_terrain,
    compute_local_slope_and_step,
    compute_point_density,
    compute_traversability_score,
)

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
    "TraversabilityState",
    "TerrainAttributes",
    "compute_point_density",
    "compute_local_slope_and_step",
    "compute_traversability_score",
    "analyze_cell_terrain",
    "analyze_map_terrain",
    "CurbCandidate",
    "PotholeCandidate",
    "OverhangCell",
    "detect_curb_candidates",
    "detect_pothole_candidates",
    "detect_overhang_cells",
    "detect_map_hazards",
]
