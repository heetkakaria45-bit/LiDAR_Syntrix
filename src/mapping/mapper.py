"""2.5D Semantic Elevation Mapper and Orchestration Engine.

Module Owner: Heet (Member 4)
Responsibilities:
    - Ingest SemanticPointCloud and spatial cell assignments
    - Orchestrate cell aggregation across all active foveation levels
    - Construct the composite SemanticMap according to CONTRACTS.md
    - Maintain diagnostic metadata and stage profiling telemetry
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Protocol, Tuple
import numpy as np

from src.contracts import GridCell, SemanticMap, SemanticPointCloud
from src.mapping.aggregation import aggregate_cell
from src.mapping.config import MappingConfig


class SpatialIndexerProtocol(Protocol):
    """Structural protocol for spatial indexers produced by src/foveated_grid/ (Manashri).

    Any spatial indexer or mock must provide point assignments mapping
    point cloud indices to (level_name, cell_idx_x, cell_idx_y, center_x, center_y).
    """

    def assign_points(
        self, points: np.ndarray
    ) -> Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]:
        """Assign points to discrete spatial grid cells.

        Returns:
            Dict mapping:
                resolution_level (str) ->
                    (grid_x, grid_y) ->
                        (center_x, center_y, point_indices_array)
        """
        ...


class SimpleFoveatedGridAdapter:
    """Standard spatial assignment adapter complying with the multi-ring foveation geometry.

    Used when Manashri's full spatial grid module is still in development, or as a
    reference implementation for unit testing and independent module execution.
    """

    def __init__(self, config: Optional[MappingConfig] = None) -> None:
        self.config = config or MappingConfig()
        # Default ring boundaries:
        # near: 0-10m (5cm), mid_near: 10-25m (10cm), mid: 25-50m (25cm), far: 50-100m (50cm)
        self.rings = [
            ("near", 0.0, 10.0, self.config.foveation_resolutions.get("near", 0.05)),
            ("mid_near", 10.0, 25.0, self.config.foveation_resolutions.get("mid_near", 0.10)),
            ("mid", 25.0, 50.0, self.config.foveation_resolutions.get("mid", 0.25)),
            ("far", 50.0, 100.0, self.config.foveation_resolutions.get("far", 0.50)),
        ]

    def assign_points(
        self, points: np.ndarray
    ) -> Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]:
        """Assign (N, 3) points to foveation levels and discrete 2D grid cells."""
        n_points = points.shape[0]
        if n_points == 0:
            return {ring[0]: {} for ring in self.rings}

        x = points[:, 0]
        y = points[:, 1]
        dist = np.hypot(x, y)

        grid_assignments: Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]] = {
            ring[0]: {} for ring in self.rings
        }

        # Track assigned mask to handle half-open boundary intervals [r_min, r_max)
        assigned = np.zeros(n_points, dtype=bool)

        for ring_name, r_min, r_max, res in self.rings:
            if ring_name == self.rings[-1][0]:
                mask = (~assigned) & (dist >= r_min) & (dist <= r_max)
            else:
                mask = (~assigned) & (dist >= r_min) & (dist < r_max)

            assigned |= mask
            indices = np.nonzero(mask)[0]
            if indices.size == 0:
                continue

            px = x[indices]
            py = y[indices]

            # Compute discrete cell indices centered on (gx * res, gy * res)
            gx = np.floor(px / res).astype(np.int32)
            gy = np.floor(py / res).astype(np.int32)

            # Group indices by (gx, gy) efficiently via vectorized sorting & splitting
            keys = np.stack([gx, gy], axis=1)
            unique_keys, inverse_idx, counts = np.unique(
                keys, axis=0, return_inverse=True, return_counts=True
            )

            order = np.argsort(inverse_idx, kind="stable")
            sorted_indices = indices[order]
            splits = np.split(sorted_indices, np.cumsum(counts)[:-1])

            half_res = res / 2.0
            for (cx_idx, cy_idx), cell_point_indices in zip(unique_keys, splits):
                # Center coordinates in continuous space (half-cell offset)
                center_x = float(cx_idx * res + half_res)
                center_y = float(cy_idx * res + half_res)
                grid_assignments[ring_name][(int(cx_idx), int(cy_idx))] = (
                    center_x,
                    center_y,
                    cell_point_indices,
                )

        return grid_assignments


class SemanticElevationMapper:
    """Main 2.5D Semantic Elevation Mapping Engine.

    Aggregates point cloud observations into a foveated SemanticMap.
    """

    def __init__(
        self,
        config: Optional[MappingConfig] = None,
        grid_indexer: Optional[Any] = None,
    ) -> None:
        self.config = config or MappingConfig()
        self.grid_indexer = grid_indexer or SimpleFoveatedGridAdapter(self.config)
        self.latest_telemetry: Dict[str, float] = {}

    def map_point_cloud(
        self,
        cloud: SemanticPointCloud,
        sensor_pose: Optional[np.ndarray] = None,
        spatial_assignments: Optional[
            Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]
        ] = None,
    ) -> SemanticMap:
        """Transform a SemanticPointCloud into an aggregated 2.5D SemanticMap.

        Integration Contract:
            When `spatial_assignments` is passed (e.g. from Manashri's `src/foveated_grid/`),
            internal grid indexing is completely bypassed with zero duplicate work.
            The mapper directly iterates over `spatial_assignments` preserving ring levels,
            grid keys, continuous cell centers, and point indices.

        Args:
            cloud: Ingested SemanticPointCloud containing points, classes, and confidences.
            sensor_pose: Optional 4x4 sensor pose transformation matrix. Defaults to Identity.
            spatial_assignments: Optional precomputed spatial assignments from src/foveated_grid/.
                                 If None, uses fallback self.grid_indexer.assign_points.

        Returns:
            SemanticMap containing populated GridCell instances.
        """
        t0 = time.perf_counter()

        if sensor_pose is None:
            sensor_pose = np.eye(4, dtype=np.float64)

        points = cloud.points
        classes = cloud.semantic_class
        confidences = cloud.confidence
        timestamp = cloud.timestamp

        # 1. Spatial indexing stage (only if not supplied externally)
        t_index_start = time.perf_counter()
        if spatial_assignments is None:
            spatial_assignments = self.grid_indexer.assign_points(points)
        t_index = (time.perf_counter() - t_index_start) * 1000.0

        # 2. Cell aggregation stage
        t_agg_start = time.perf_counter()
        cells_by_level: Dict[str, Dict[Tuple[int, int], GridCell]] = {}
        total_cells = 0
        min_pts = self.config.min_points_per_cell
        strategy = self.config.elevation_strategy
        ref_points = self.config.occupancy_ref_points

        for level_name, cell_dict in spatial_assignments.items():
            level_map: Dict[Tuple[int, int], GridCell] = {}
            for (gx, gy), (cx, cy, pt_indices) in cell_dict.items():
                if pt_indices.size < min_pts:
                    continue

                cell_z = points[pt_indices, 2]
                cell_cls = classes[pt_indices]
                cell_conf = confidences[pt_indices]

                cell = aggregate_cell(
                    resolution_level=level_name,
                    cell_x=cx,
                    cell_y=cy,
                    points_z=cell_z,
                    classes=cell_cls,
                    confidences=cell_conf,
                    timestamp=timestamp,
                    strategy=strategy,
                    ref_points=ref_points,
                )

                if cell is not None:
                    level_map[(gx, gy)] = cell
                    total_cells += 1

            cells_by_level[level_name] = level_map

        t_agg = (time.perf_counter() - t_agg_start) * 1000.0
        total_time_ms = (time.perf_counter() - t0) * 1000.0

        self.latest_telemetry = {
            "indexing_time_ms": t_index,
            "aggregation_time_ms": t_agg,
            "total_mapping_time_ms": total_time_ms,
            "num_points": float(points.shape[0]),
            "num_cells": float(total_cells),
        }

        metadata = {
            "num_points": points.shape[0],
            "num_cells": total_cells,
            "frame_id": cloud.frame_id,
            "telemetry": self.latest_telemetry,
        }

        return SemanticMap(
            cells=cells_by_level,
            resolution_levels=self.config.foveation_resolutions,
            sensor_pose=sensor_pose,
            timestamp=timestamp,
            metadata=metadata,
        )
