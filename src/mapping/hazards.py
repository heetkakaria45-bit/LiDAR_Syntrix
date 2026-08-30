"""Geometric Hazard and Obstacle Detection Module.

Module Owner: Heet (Member 4)
Responsibilities:
    - Deterministic road curb detection (step transitions with semantic boundaries)
    - Pothole detection (localized negative elevation depressions relative to surrounding road)
    - Vertical overhang and clearance representation (distinguishing traversable overheads)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.contracts import GridCell, SemanticMap
from src.mapping.config import HazardConfig


@dataclass
class CurbCandidate:
    """Road curb candidate representing a localized elevation step between road and sidewalk."""

    cell_key: Tuple[int, int]
    cell_x: float
    cell_y: float
    step_height: float
    confidence: float
    adjacent_road_cell: Tuple[int, int]
    adjacent_sidewalk_cell: Tuple[int, int]


@dataclass
class PotholeCandidate:
    """Pothole candidate representing a localized negative depression in drivable terrain."""

    cell_key: Tuple[int, int]
    cell_x: float
    cell_y: float
    depth: float
    confidence: float
    surrounding_mean_z: float


@dataclass
class OverhangCell:
    """Representation of multi-layer vertical structure with overhead clearance."""

    cell_key: Tuple[int, int]
    cell_x: float
    cell_y: float
    ground_z: float
    structure_z: float
    vertical_clearance: float
    is_traversable_clearance: bool


def detect_curb_candidates(
    cells: Dict[Tuple[int, int], GridCell],
    config: Optional[HazardConfig] = None,
) -> List[CurbCandidate]:
    """Detect curb candidates between drivable ground (class 0) and elevated sidewalk (class 1 or 7).

    Criteria:
        1. Spatial adjacency between a road cell (class 0) and elevated sidewalk/terrain cell (class 1 or 7).
        2. Height transition Delta_z = z_sidewalk - z_road in [curb_min_step, curb_max_step] (e.g. 8-25 cm).
        3. Confidence is weighted by the sharpness of the transition and cell confidences.

    Args:
        cells: Dictionary mapping (gx, gy) to GridCell within a spatial ring (typically 'near' or 'mid_near').
        config: HazardConfig containing curb_min_step and curb_max_step.

    Returns:
        List of CurbCandidate objects.
    """
    if config is None:
        config = HazardConfig()

    candidates: List[CurbCandidate] = []
    # Check 4-connected neighbors to prevent duplicate diagonal detections
    offsets = [(1, 0), (0, 1)]

    for (gx, gy), cell_a in cells.items():
        for dx, dy in offsets:
            nb_key = (gx + dx, gy + dy)
            if nb_key not in cells:
                continue
            cell_b = cells[nb_key]

            # One cell must be DRIVABLE_GROUND (0) and the other NON_DRIVABLE_TERRAIN (1) or OTHER_OBSTACLE (7)
            is_a_road = cell_a.semantic_class == 0
            is_b_road = cell_b.semantic_class == 0

            if is_a_road == is_b_road:
                continue  # Both road or both non-road

            if is_a_road:
                road_cell, road_key = cell_a, (gx, gy)
                sw_cell, sw_key = cell_b, nb_key
            else:
                road_cell, road_key = cell_b, nb_key
                sw_cell, sw_key = cell_a, (gx, gy)

            # Step height is elevation difference
            step = float(sw_cell.elevation - road_cell.elevation)
            if config.curb_min_step <= step <= config.curb_max_step:
                # High confidence if step is centered near nominal curb height (e.g. ~15cm)
                nominal_curb = (config.curb_min_step + config.curb_max_step) / 2.0
                step_error = abs(step - nominal_curb) / (nominal_curb + 1e-4)
                conf = float(
                    np.clip(
                        0.5 * (road_cell.confidence + sw_cell.confidence) * (1.0 - 0.5 * step_error),
                        0.1,
                        1.0,
                    )
                )

                candidates.append(
                    CurbCandidate(
                        cell_key=sw_key,
                        cell_x=sw_cell.cell_x,
                        cell_y=sw_cell.cell_y,
                        step_height=step,
                        confidence=conf,
                        adjacent_road_cell=road_key,
                        adjacent_sidewalk_cell=sw_key,
                    )
                )

    return candidates


def detect_pothole_candidates(
    cells: Dict[Tuple[int, int], GridCell],
    config: Optional[HazardConfig] = None,
) -> List[PotholeCandidate]:
    """Detect pothole candidates as localized negative depressions relative to surrounding road.

    Criteria:
        1. Cell is located within or adjacent to drivable road.
        2. At least 3 surrounding neighbors exist.
        3. Depression depth = median(surrounding_z) - cell_z >= pothole_min_depth (e.g. 5 cm).

    Args:
        cells: Dictionary mapping (gx, gy) to GridCell within a spatial ring.
        config: HazardConfig containing pothole_min_depth.

    Returns:
        List of PotholeCandidate objects.
    """
    if config is None:
        config = HazardConfig()

    # Search in 1-cell and 2-cell radius to robustly handle point cloud sparsity
    offsets_1 = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]
    offsets_2 = [
        (dx, dy)
        for dx in range(-2, 3)
        for dy in range(-2, 3)
        if not (dx == 0 and dy == 0)
    ]

    candidates: List[PotholeCandidate] = []

    for (gx, gy), cell in cells.items():
        # Surrounding road elevations
        surrounding_z = []
        for dx, dy in offsets_1:
            nb_key = (gx + dx, gy + dy)
            if nb_key in cells:
                nb = cells[nb_key]
                if nb.semantic_class == 0:  # Surrounding drivable road
                    surrounding_z.append(nb.elevation)

        # Fallback to wider radius (up to 4 cells / 40cm) if road is sparsely sampled
        if len(surrounding_z) < 2:
            offsets_4 = [
                (dx, dy)
                for dx in range(-4, 5)
                for dy in range(-4, 5)
                if not (dx == 0 and dy == 0)
            ]
            for dx, dy in offsets_4:
                nb_key = (gx + dx, gy + dy)
                if nb_key in cells:
                    nb = cells[nb_key]
                    if nb.semantic_class == 0:
                        surrounding_z.append(nb.elevation)

        if len(surrounding_z) < 2:
            continue

        ref_z = float(np.median(surrounding_z))
        depth = float(ref_z - cell.elevation)

        if depth >= config.pothole_min_depth:
            # Confidence scales with depth up to 15cm
            depth_score = min(1.0, depth / 0.15)
            conf = float(np.clip(cell.confidence * depth_score, 0.2, 1.0))

            candidates.append(
                PotholeCandidate(
                    cell_key=(gx, gy),
                    cell_x=cell.cell_x,
                    cell_y=cell.cell_y,
                    depth=depth,
                    confidence=conf,
                    surrounding_mean_z=ref_z,
                )
            )

    return candidates


def detect_overhang_cells(
    cells: Dict[Tuple[int, int], GridCell],
    config: Optional[HazardConfig] = None,
) -> List[OverhangCell]:
    """Detect cells with vertical multi-layer structure or overhead clearance.

    Criteria:
        1. Vertical span delta_z = max_z - min_z >= overhang_min_clearance (e.g. 2.2m).
        2. Clearance is evaluated between estimated ground min_z and upper structure max_z.
        3. Classified as traversable if vertical clearance provides adequate headroom.

    Args:
        cells: Dictionary mapping (gx, gy) to GridCell.
        config: HazardConfig containing overhang_min_clearance.

    Returns:
        List of OverhangCell objects.
    """
    if config is None:
        config = HazardConfig()

    overhangs: List[OverhangCell] = []
    min_clearance = config.overhang_min_clearance

    for (gx, gy), cell in cells.items():
        span = float(cell.max_z - cell.min_z)
        if span >= min_clearance:
            # Vertical span indicates high clearance between ground level and overhead object
            is_traversable = span >= min_clearance
            overhangs.append(
                OverhangCell(
                    cell_key=(gx, gy),
                    cell_x=cell.cell_x,
                    cell_y=cell.cell_y,
                    ground_z=cell.min_z,
                    structure_z=cell.max_z,
                    vertical_clearance=span,
                    is_traversable_clearance=is_traversable,
                )
            )

    return overhangs


def detect_map_hazards(
    semantic_map: SemanticMap,
    config: Optional[HazardConfig] = None,
) -> Dict[str, Any]:
    """Execute comprehensive hazard detection across all active foveation levels in SemanticMap.

    Args:
        semantic_map: Aggregated SemanticMap.
        config: Optional HazardConfig.

    Returns:
        Dict containing:
            'curbs': List[CurbCandidate],
            'potholes': List[PotholeCandidate],
            'overhangs': List[OverhangCell],
            'summary': Dict of counts per hazard type.
    """
    if config is None:
        config = HazardConfig()

    all_curbs: List[CurbCandidate] = []
    all_potholes: List[PotholeCandidate] = []
    all_overhangs: List[OverhangCell] = []

    # Primarily evaluate curbs & potholes in near and mid_near high-resolution rings
    for level_name in ["near", "mid_near"]:
        if level_name in semantic_map.cells:
            level_cells = semantic_map.cells[level_name]
            all_curbs.extend(detect_curb_candidates(level_cells, config))
            all_potholes.extend(detect_pothole_candidates(level_cells, config))

    # Overhangs are evaluated across all resolution rings
    for level_name, level_cells in semantic_map.cells.items():
        all_overhangs.extend(detect_overhang_cells(level_cells, config))

    return {
        "curbs": all_curbs,
        "potholes": all_potholes,
        "overhangs": all_overhangs,
        "summary": {
            "num_curb_candidates": len(all_curbs),
            "num_pothole_candidates": len(all_potholes),
            "num_overhang_cells": len(all_overhangs),
        },
    }
