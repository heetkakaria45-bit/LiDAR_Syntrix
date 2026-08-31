"""
Semantic 2.5D Mapping and Traversability Interfaces.
Module Owner: Heet (src/mapping/)

Responsibility:
    - 2.5D Spatial representation (XY position + Z elevation + semantics + traversability).
    - Statistical elevation estimation (min_z, max_z, mean_z).
    - Local surface roughness and height discontinuity computation.
    - Geometric traversability evaluation (slope, step height, roughness, semantic cost).
    - Temporal map updating and cell observation tracking.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np

from src.common.config import SystemConfig, load_config
from src.common.interfaces import ISemantic25DMapper, ITemporalMapUpdater, ITraversabilityAnalyzer
from src.common.types import (
    GridCell,
    SemanticClass,
    SemanticPointCloud,
    SemanticMap,
    TraversabilityScore,
)


class Semantic25DMapper(ISemantic25DMapper):
    """
    Core Semantic 2.5D Mapper scaffold.
    To be fully implemented by Heet in Phase F.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()
        self._map = SemanticMap(
            resolution_levels=self.config.foveation.levels,
            timestamp=0.0,
            frame_id=0,
        )

    def update_map(self, semantic_cloud: SemanticPointCloud) -> SemanticMap:
        """Elevation & semantic cell aggregation scheduled for Phase F."""
        if not isinstance(semantic_cloud, SemanticPointCloud):
            raise TypeError(f"Expected SemanticPointCloud, got {type(semantic_cloud)}")
        self._map.timestamp = semantic_cloud.timestamp
        self._map.frame_id = semantic_cloud.frame_id
        self._map.sensor_pose = semantic_cloud.sensor_pose
        return self._map

    def get_map(self) -> SemanticMap:
        return self._map

    def reset(self) -> None:
        self._map = SemanticMap(
            resolution_levels=self.config.foveation.levels,
            timestamp=0.0,
            frame_id=0,
        )


class TraversabilityAnalyzer(ITraversabilityAnalyzer):
    """
    Traversability analyzer scaffold.
    To be fully implemented by Heet in Phase F.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def evaluate_cell(self, cell: GridCell) -> TraversabilityScore:
        is_ground = SemanticClass.is_ground(cell.semantic_class)
        is_trav = is_ground and (cell.roughness <= self.config.mapping.roughness_threshold_m)
        return TraversabilityScore(
            is_traversable=is_trav,
            cost=0.0 if is_trav else 1.0,
            slope_rad=0.0,
            step_height_m=cell.height_span,
            roughness_m=cell.roughness,
            semantic_penalty=0.0 if is_ground else 1.0,
        )

    def evaluate_map(self, semantic_map: SemanticMap) -> Dict[Tuple[int, int, int], TraversabilityScore]:
        return {key: self.evaluate_cell(cell) for key, cell in semantic_map.cells.items()}


class TemporalMapUpdater(ITemporalMapUpdater):
    """
    Temporal map integration scaffold.
    To be fully implemented by Heet in Phase F.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def integrate_frame(self, current_map: SemanticMap, new_cloud: SemanticPointCloud) -> SemanticMap:
        current_map.timestamp = new_cloud.timestamp
        current_map.frame_id = new_cloud.frame_id
        return current_map
