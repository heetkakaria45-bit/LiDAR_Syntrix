"""Terrain and Traversability Analysis Module for 2.5D Semantic Maps.

Module Owner: Heet (Member 4)
Responsibilities:
    - Estimate local terrain slope (gradient via neighboring cells)
    - Compute local elevation discontinuity (step height)
    - Compute spatial point density (points/m^2)
    - Evaluate deterministic and explainable traversability:
        - Categorical: DRIVABLE, NON_DRIVABLE, UNKNOWN
        - Continuous score: [0.0, 1.0]
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.contracts import GridCell, SemanticMap
from src.mapping.config import TraversabilityConfig


class TraversabilityState(str, Enum):
    """Categorical traversability status for autonomous path planning."""

    DRIVABLE = "DRIVABLE"
    NON_DRIVABLE = "NON_DRIVABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class TerrainAttributes:
    """Computed terrain and traversability metrics for a single grid cell."""

    slope_rad: float  # Slope inclination in radians (NaN if unknown)
    slope_deg: float  # Slope inclination in degrees (NaN if unknown)
    roughness: float  # Surface roughness in meters
    max_elevation_step: float  # Maximum elevation discontinuity to neighbors (m)
    point_density: float  # Points per square meter (pts/m^2)
    traversability_state: TraversabilityState
    traversability_score: float  # Continuous score in [0.0, 1.0]


# Non-drivable project semantic classes:
# 1: NON_DRIVABLE_TERRAIN, 2: VEHICLE, 3: PEDESTRIAN, 4: CYCLIST,
# 5: POLE, 6: WALL_BUILDING, 7: OTHER_OBSTACLE
# Class 0: DRIVABLE_GROUND is the only natively traversable surface.
OBSTACLE_SEMANTIC_CLASSES = {1, 2, 3, 4, 5, 6, 7}


def compute_point_density(point_count: int, cell_resolution: float) -> float:
    """Calculate point density in points per square meter.

    Args:
        point_count: Number of points within the cell.
        cell_resolution: Linear cell width/height in meters (e.g. 0.05m).

    Returns:
        Point density (pts/m^2).
    """
    if cell_resolution <= 0.0:
        return 0.0
    cell_area = cell_resolution * cell_resolution
    return float(point_count) / cell_area


def compute_local_slope_and_step(
    cell: GridCell,
    neighbors: List[GridCell],
    cell_resolution: float,
) -> Tuple[float, float, float]:
    """Estimate terrain slope and maximum elevation discontinuity from local neighbors.

    Formulation:
        For cells with neighbors, fit a local planar gradient:
            dz(x, y) = a * (x - x0) + b * (y - y0)
        Using exact 2x2 normal equations for least-squares regression over the neighborhood:
            gradient vector = (a, b)
            slope = arctan(sqrt(a^2 + b^2))
        Also compute the maximum absolute vertical step:
            max_step = max(|z_neighbor - z_cell|)

    Args:
        cell: The central GridCell.
        neighbors: List of adjacent GridCell instances (up to 8 neighbors).
        cell_resolution: Resolution of the grid level in meters.

    Returns:
        (slope_rad, slope_deg, max_elevation_step).
        If fewer than 2 valid neighbors exist, slope is (float('nan'), float('nan')).
    """
    if not neighbors:
        return float("nan"), float("nan"), 0.0

    n_nb = len(neighbors)
    cx, cy, cz = cell.cell_x, cell.cell_y, cell.elevation
    max_step = 0.0

    if n_nb < 2:
        for nb in neighbors:
            step = abs(nb.elevation - cz)
            if step > max_step:
                max_step = step
        return float("nan"), float("nan"), float(max_step)

    # Accumulate 2x2 normal equations: [ [sum dx^2, sum dx*dy], [sum dx*dy, sum dy^2] ]
    s_xx = 0.0
    s_yy = 0.0
    s_xy = 0.0
    s_xz = 0.0
    s_yz = 0.0

    for nb in neighbors:
        dx = nb.cell_x - cx
        dy = nb.cell_y - cy
        dz = nb.elevation - cz
        step = abs(dz)
        if step > max_step:
            max_step = step
        s_xx += dx * dx
        s_yy += dy * dy
        s_xy += dx * dy
        s_xz += dx * dz
        s_yz += dy * dz

    det = s_xx * s_yy - s_xy * s_xy
    if det > 1e-12:
        dz_dx = (s_yy * s_xz - s_xy * s_yz) / det
        dz_dy = (s_xx * s_yz - s_xy * s_xz) / det
        grad_norm = math.hypot(dz_dx, dz_dy)
        slope_rad = math.atan(grad_norm)
        slope_deg = math.degrees(slope_rad)
    else:
        slope_rad = float("nan")
        slope_deg = float("nan")

    return slope_rad, slope_deg, float(max_step)


def compute_traversability_score(
    cell: GridCell,
    slope_deg: float,
    roughness: float,
    max_step: float,
    config: Optional[TraversabilityConfig] = None,
) -> Tuple[TraversabilityState, float]:
    """Calculate categorical traversability and continuous [0, 1] traversability score.

    Continuous Score Formulation:
        Base semantic multiplier:
            w_sem = 1.0 for DRIVABLE_GROUND (class 0)
            w_sem = 0.15 for NON_DRIVABLE_TERRAIN (class 1)
            w_sem = 0.0 for physical obstacles (classes 2..7)
        Geometric penalties:
            slope_cost = slope_deg / max_slope
            rough_cost = roughness / roughness_thresh
            step_cost = max_step / step_thresh
            geom_factor = max(0.0, 1.0 - (0.40*slope_cost + 0.30*rough_cost + 0.30*step_cost))

        score = w_sem * (cell.confidence) * geom_factor

    Categorical Classification:
        - If occupancy < unknown_occupancy_min: UNKNOWN
        - If semantic_class != 0: NON_DRIVABLE
        - If slope_deg > max_drivable_slope_deg: NON_DRIVABLE
        - If roughness > roughness_threshold: NON_DRIVABLE
        - If max_step > discontinuity_threshold: NON_DRIVABLE
        - Else: DRIVABLE

    Args:
        cell: The GridCell to evaluate.
        slope_deg: Slope in degrees (can be NaN if unknown).
        roughness: Height variation in meters.
        max_step: Maximum elevation difference to adjacent neighbors.
        config: TraversabilityConfig containing thresholds.

    Returns:
        (traversability_state, continuous_traversability_score)
    """
    if config is None:
        config = TraversabilityConfig()

    # 1. Check for unknown/unobserved state
    if cell.point_count == 0 or cell.occupancy < config.unknown_occupancy_min:
        return TraversabilityState.UNKNOWN, 0.0

    # 2. Semantic Weighting
    c = cell.semantic_class
    if c == 0:  # DRIVABLE_GROUND
        w_sem = 1.0
    elif c == 1:  # NON_DRIVABLE_TERRAIN (grass, gravel, mud)
        w_sem = 0.15
    elif c in (3, 4):  # PEDESTRIAN, CYCLIST (Vulnerable Road Users)
        w_sem = 0.0
    else:  # VEHICLE, POLE, WALL_BUILDING, OTHER_OBSTACLE
        w_sem = 0.0

    # 3. Geometric Factors
    max_slope = max(config.max_drivable_slope_deg, 1e-3)
    rough_thresh = max(config.roughness_threshold, 1e-3)
    step_thresh = max(config.discontinuity_threshold, 1e-3)

    if math.isnan(slope_deg):
        slope_cost = 0.0
        slope_exceeded = False
    else:
        slope_cost = slope_deg / max_slope
        slope_exceeded = slope_deg > config.max_drivable_slope_deg

    rough_cost = roughness / rough_thresh
    roughness_exceeded = roughness > config.roughness_threshold

    step_cost = max_step / step_thresh
    step_exceeded = max_step > config.discontinuity_threshold

    # Continuous penalty weighted blend: 40% slope, 30% roughness, 30% step
    geom_penalty = min(1.0, 0.40 * slope_cost + 0.30 * rough_cost + 0.30 * step_cost)
    geom_factor = max(0.0, 1.0 - geom_penalty)
    score = w_sem * float(cell.confidence) * geom_factor

    # 4. Categorical Decision & Score Clamping
    if c != 0 or slope_exceeded or roughness_exceeded or step_exceeded:
        state = TraversabilityState.NON_DRIVABLE
        if c in (2, 3, 4, 5, 6, 7) or slope_exceeded or roughness_exceeded or step_exceeded:
            score = 0.0
        else:
            # NON_DRIVABLE_TERRAIN (c=1) retains small residual score <= 0.15
            score = min(score, 0.15)
    else:
        state = TraversabilityState.DRIVABLE

    score = float(min(1.0, max(0.0, score)))
    return state, score


def analyze_cell_terrain(
    cell: GridCell,
    neighbors: List[GridCell],
    cell_resolution: float,
    config: Optional[TraversabilityConfig] = None,
) -> TerrainAttributes:
    """Analyze terrain geometry and traversability for an individual cell."""
    slope_rad, slope_deg, max_step = compute_local_slope_and_step(
        cell=cell,
        neighbors=neighbors,
        cell_resolution=cell_resolution,
    )
    density = compute_point_density(cell.point_count, cell_resolution)
    state, score = compute_traversability_score(
        cell=cell,
        slope_deg=slope_deg,
        roughness=cell.roughness,
        max_step=max_step,
        config=config,
    )

    return TerrainAttributes(
        slope_rad=slope_rad,
        slope_deg=slope_deg,
        roughness=cell.roughness,
        max_elevation_step=max_step,
        point_density=density,
        traversability_state=state,
        traversability_score=score,
    )


def analyze_map_terrain(
    semantic_map: SemanticMap,
    config: Optional[TraversabilityConfig] = None,
) -> Dict[str, Dict[Tuple[int, int], TerrainAttributes]]:
    """Analyze terrain and traversability for all cells across all foveation levels in SemanticMap.

    Args:
        semantic_map: Aggregated SemanticMap from SemanticElevationMapper.
        config: Optional TraversabilityConfig.

    Returns:
        Dict mapping level_name -> (gx, gy) -> TerrainAttributes.
    """
    if config is None:
        config = TraversabilityConfig()

    result: Dict[str, Dict[Tuple[int, int], TerrainAttributes]] = {}

    # 8-connected neighbor relative offsets
    neighbor_offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    for level_name, level_cells in semantic_map.cells.items():
        result[level_name] = {}
        resolution = float(semantic_map.resolution_levels.get(level_name, 0.10))

        for (gx, gy), cell in level_cells.items():
            # Find existing 8-connected neighbors in the same resolution level
            neighbors = [
                level_cells[nb_key]
                for dx, dy in neighbor_offsets
                if (nb_key := (gx + dx, gy + dy)) in level_cells
            ]

            attrs = analyze_cell_terrain(
                cell=cell,
                neighbors=neighbors,
                cell_resolution=resolution,
                config=config,
            )
            result[level_name][(gx, gy)] = attrs

    return result
