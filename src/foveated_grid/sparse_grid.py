"""Concentric Multi-Ring Sparse Hash Grid Storage and Query Engine.

Module Owner: Manashri
Responsibilities:
    - Sparse hash-map storage for occupied multi-resolution cells
    - Scalar and vectorized batch point insertion with generic payload accumulation
    - Point-location queries without spurious cell allocation
    - Bounding-box spatial region queries over sparse cells
    - Accurate occupied cell counting and object-level memory estimation
    - Standardized handoff and conversion to GridCell and SemanticMap contracts
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from src.contracts import GridCell, SemanticMap
from src.foveated_grid.foveated_indexer import (
    CellKey,
    FoveatedGridIndexer,
)


@dataclass
class SparseCell:
    """Data container for a single occupied multi-resolution spatial cell.

    Attributes:
        key: Canonical discrete spatial identifier (level, i, j).
        center_x: Reconstructed continuous X center coordinate in map frame (meters).
        center_y: Reconstructed continuous Y center coordinate in map frame (meters).
        resolution: Physical cell edge width / height delta (meters).
        level_name: Descriptive name of the foveation band (e.g. 'near', 'mid_near').
        items: List of raw payloads/points inserted into this cell.
    """

    key: CellKey
    center_x: float
    center_y: float
    resolution: float
    level_name: str
    items: List[Any] = field(default_factory=list)

    @property
    def point_count(self) -> int:
        """Total number of point observations or payloads accumulated in this cell."""
        return len(self.items)

    def to_grid_cell(self, timestamp: float = 0.0) -> GridCell:
        """Convert this SparseCell into the standardized project GridCell contract.

        Extracts and aggregates elevation statistics (min, max, median), height variance
        roughness, occupancy probability, and majority semantic label distributions.

        Args:
            timestamp: Capture epoch timestamp in seconds.

        Returns:
            Validated GridCell contract dataclass instance.
        """
        z_vals: List[float] = []
        classes: List[int] = []
        confidences: List[float] = []

        for item in self.items:
            if isinstance(item, tuple):
                if len(item) == 3 and isinstance(item[1], (int, np.integer)):
                    z_vals.append(float(item[0]))
                    classes.append(int(item[1]))
                    confidences.append(float(item[2]))
                elif len(item) >= 3:
                    z_vals.append(float(item[2]))
            elif isinstance(item, dict):
                if "z" in item:
                    z_vals.append(float(item["z"]))
                if "class" in item or "semantic_class" in item:
                    cls_id = int(item.get("class", item.get("semantic_class", 0)))
                    classes.append(cls_id)
                if "conf" in item or "confidence" in item:
                    conf = float(item.get("conf", item.get("confidence", 1.0)))
                    confidences.append(conf)
            elif isinstance(item, list):
                if len(item) >= 3:
                    z_vals.append(float(item[2]))

        # Fast-path elevation and semantic aggregation
        num_z = len(z_vals)
        if num_z == 1:
            z0 = z_vals[0]
            elevation = z0
            min_z = z0
            max_z = z0
            roughness = 0.0
        elif num_z == 2:
            z0, z1 = z_vals[0], z_vals[1]
            min_z = min(z0, z1)
            max_z = max(z0, z1)
            elevation = 0.5 * (z0 + z1)
            diff = z0 - z1
            roughness = 0.25 * (diff * diff)
        elif num_z > 2:
            z_arr = np.array(z_vals, dtype=np.float32)
            elevation = float(np.median(z_arr))
            min_z = float(np.min(z_arr))
            max_z = float(np.max(z_arr))
            roughness = float(np.var(z_arr))
        else:
            elevation = 0.0
            min_z = 0.0
            max_z = 0.0
            roughness = 0.0

        # Semantic class aggregation
        num_cls = len(classes)
        if num_cls == 1:
            semantic_class = classes[0]
            confidence = confidences[0] if confidences else 1.0
            probs = None
        elif num_cls > 1:
            class_counts = np.bincount(classes, minlength=8)
            semantic_class = int(np.argmax(class_counts[:8]))
            confidence = float(np.mean(confidences)) if confidences else 1.0
            probs = class_counts[:8].astype(np.float32) / float(num_cls)
        else:
            semantic_class = 0  # Default DRIVABLE_GROUND
            confidence = 1.0
            probs = None

        return GridCell(
            resolution_level=self.level_name,
            cell_x=self.center_x,
            cell_y=self.center_y,
            elevation=elevation,
            min_z=min_z,
            max_z=max_z,
            semantic_class=semantic_class,
            confidence=confidence,
            occupancy=1.0,
            point_count=len(self.items),
            roughness=roughness,
            timestamp=timestamp,
            observation_count=1,
            uncertainty=0.0,
            semantic_probabilities=probs,
        )


@dataclass(frozen=True)
class BatchInsertResult:
    """Summary statistics returned by vectorized batch point insertion.

    Attributes:
        num_accepted: Number of points within the valid sensing boundary [0, max_radius).
        num_rejected: Number of out-of-bounds points discarded (r >= max_radius or invalid).
        num_cells_created: Count of brand-new sparse cells instantiated.
        num_cells_updated: Count of existing sparse cells that accumulated additional points.
        total_occupied_cells: Total count of occupied cells after insertion.
    """

    num_accepted: int
    num_rejected: int
    num_cells_created: int
    num_cells_updated: int
    total_occupied_cells: int


class SparseFoveatedGrid:
    """Concentric Multi-Ring Sparse Hash Grid Data Structure.

    Maintains a sparse hash table mapping discrete CellKey(level, i, j) to
    SparseCell instances. Guarantees zero allocation for unobserved terrain or
    empty concentric donut spaces.
    """

    def __init__(
        self,
        indexer: Optional[FoveatedGridIndexer] = None,
        config: Optional[Union[Dict[str, Any], Path, str]] = None,
    ) -> None:
        """Initialize sparse grid with default or custom indexer configuration.

        Args:
            indexer: Optional pre-configured FoveatedGridIndexer instance.
            config: Optional config dict or path to YAML config file.
        """
        self._indexer = indexer or FoveatedGridIndexer(config=config)
        self._cells: Dict[CellKey, SparseCell] = {}

    @property
    def indexer(self) -> FoveatedGridIndexer:
        """Underlying spatial coordinate indexer."""
        return self._indexer

    def insert(self, x: float, y: float, data: Any = None) -> Optional[CellKey]:
        """Insert a point observation or arbitrary payload into the grid at world (x, y).

        Behavior:
            1. Computes radial distance r = sqrt(x^2 + y^2).
            2. Identifies matching half-open foveation level [r_k, r_{k+1}).
            3. Maps (x, y) to discrete CellKey(level, i, j).
            4. If the cell does not exist in sparse storage, instantiates a new SparseCell.
            5. Appends the data item (or (x, y) coordinate tuple if data is None) to cell.items.

        Args:
            x: Forward Cartesian coordinate in meters (vehicle heading).
            y: Left Cartesian coordinate in meters (lateral axis).
            data: Optional arbitrary payload (e.g. (x, y, z), semantic tuple, dict, etc.).

        Returns:
            CellKey where the point was stored, or None if (x, y) is out of range [0, max_radius).
        """
        key = self._indexer.world_to_cell(x, y)
        if key is None:
            return None

        payload = data if data is not None else (x, y)

        if key not in self._cells:
            center_x, center_y = self._indexer.cell_to_world(key)
            lvl = self._indexer.get_level(key.level)
            cell = SparseCell(
                key=key,
                center_x=center_x,
                center_y=center_y,
                resolution=lvl.resolution,
                level_name=lvl.name,
                items=[payload],
            )
            self._cells[key] = cell
        else:
            self._cells[key].items.append(payload)

        return key

    def insert_batch(
        self,
        points: Union[np.ndarray, Any],
        payloads: Optional[Union[np.ndarray, List[Any]]] = None,
    ) -> BatchInsertResult:
        """Vectorized ingestion of continuous point clouds into the sparse multi-resolution grid.

        Accepts:
            - np.ndarray of shape (N, 2) or (N, >=2) where col 0 = X, col 1 = Y, optional col 2 = Z.
            - PointCloudFrame / SemanticPointCloud contract dataclasses.
            - Optional list or array of arbitrary per-point payloads of length N.

        Behavior:
            1. Vectorized computation of r = sqrt(x^2 + y^2) and boundary checking.
            2. Vectorized half-open ring assignment [r_k, r_{k+1}) and coordinate quantization.
            3. Grouping of points by packed 64-bit CellKey using fast NumPy sorting.
            4. Updates existing SparseCell instances or instantiates new ones preserving spatial correctness.

        Args:
            points: Array of points (N, 2+) or contract frame object.
            payloads: Optional list or array of custom per-point payload objects.

        Returns:
            BatchInsertResult detailing accepted, rejected, created, and updated cell counts.
        """
        if hasattr(points, "points"):
            pts = np.asarray(points.points, dtype=np.float64)
            if (
                payloads is None
                and hasattr(points, "semantic_class")
                and hasattr(points, "confidence")
            ):
                sem_classes = points.semantic_class
                confidences = points.confidence
                has_z = pts.shape[1] >= 3
                payloads = [
                    (
                        float(pts[i, 2]) if has_z else 0.0,
                        int(sem_classes[i]),
                        float(confidences[i]),
                    )
                    for i in range(len(pts))
                ]
        else:
            pts = np.asarray(points, dtype=np.float64)

        if pts.ndim != 2 or pts.shape[1] < 2:
            raise ValueError(f"points array must have shape (N, >=2), got {pts.shape}")

        n_total = len(pts)
        if n_total == 0:
            return BatchInsertResult(
                num_accepted=0,
                num_rejected=0,
                num_cells_created=0,
                num_cells_updated=0,
                total_occupied_cells=len(self._cells),
            )

        valid_mask, packed_keys = self._indexer.world_to_cell_batch(pts)
        num_rejected = int(np.count_nonzero(~valid_mask))
        num_accepted = int(np.count_nonzero(valid_mask))

        if num_accepted == 0:
            return BatchInsertResult(
                num_accepted=0,
                num_rejected=num_rejected,
                num_cells_created=0,
                num_cells_updated=0,
                total_occupied_cells=len(self._cells),
            )

        valid_indices = np.where(valid_mask)[0]
        valid_keys = packed_keys[valid_mask]

        # Group points by unique packed key using numpy sorting
        sort_idx = np.argsort(valid_keys)
        sorted_keys = valid_keys[sort_idx]
        sorted_pt_indices = valid_indices[sort_idx]

        unique_keys, split_indices = np.unique(sorted_keys, return_index=True)
        num_unique = len(unique_keys)
        n_valid = len(sorted_pt_indices)

        # Pre-reorder payloads in a single C-speed pass rather than per-slice comprehensions
        if payloads is not None:
            sorted_items = [payloads[idx] for idx in sorted_pt_indices]
        elif pts.shape[1] >= 3:
            sorted_items = [
                (float(pts[idx, 0]), float(pts[idx, 1]), float(pts[idx, 2]))
                for idx in sorted_pt_indices
            ]
        else:
            sorted_items = [(float(pts[idx, 0]), float(pts[idx, 1])) for idx in sorted_pt_indices]

        num_cells_created = 0
        num_cells_updated = 0

        for k_idx in range(num_unique):
            key_val = int(unique_keys[k_idx])
            start_i = int(split_indices[k_idx])
            end_i = int(split_indices[k_idx + 1]) if k_idx + 1 < num_unique else n_valid

            group_items = sorted_items[start_i:end_i]
            cell_key = CellKey.from_packed_uint64(key_val)

            if cell_key in self._cells:
                self._cells[cell_key].items.extend(group_items)
                num_cells_updated += 1
            else:
                cx, cy = self._indexer.cell_to_world(cell_key)
                lvl = self._indexer.get_level(cell_key.level)
                self._cells[cell_key] = SparseCell(
                    key=cell_key,
                    center_x=cx,
                    center_y=cy,
                    resolution=lvl.resolution,
                    level_name=lvl.name,
                    items=group_items,
                )
                num_cells_created += 1

        return BatchInsertResult(
            num_accepted=num_accepted,
            num_rejected=num_rejected,
            num_cells_created=num_cells_created,
            num_cells_updated=num_cells_updated,
            total_occupied_cells=len(self._cells),
        )

    def query(self, x: float, y: float) -> Optional[SparseCell]:
        """Look up the occupied SparseCell containing continuous world coordinates (x, y).

        Invariants:
            - Does NOT allocate or create a cell if the queried location is unoccupied.
            - Out-of-bounds coordinates return None without mutating internal storage.

        Args:
            x: Forward coordinate in meters.
            y: Left coordinate in meters.

        Returns:
            SparseCell if the cell is currently occupied, else None.
        """
        key = self._indexer.world_to_cell(x, y)
        if key is None:
            return None
        return self._cells.get(key)

    def query_cell(self, cell_key: Union[CellKey, Tuple[int, int, int]]) -> Optional[SparseCell]:
        """Look up occupied SparseCell directly by discrete CellKey.

        Args:
            cell_key: CellKey instance or (level, i, j) tuple.

        Returns:
            SparseCell if occupied, else None.
        """
        key = cell_key if isinstance(cell_key, CellKey) else CellKey(*cell_key)
        return self._cells.get(key)

    def query_region(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        use_cell_center: bool = True,
    ) -> List[SparseCell]:
        """Query all occupied cells within a 2D bounding box [min_x, max_x] x [min_y, max_y].

        Iterates strictly across currently occupied sparse cells (O(K), K = cell_count()).
        Does NOT iterate over empty or unallocated theoretical grid cells.

        Boundaries:
            Both X and Y intervals are inclusive: [min(min_x, max_x), max(min_x, max_x)]
            and [min(min_y, max_y), max(min_y, max_y)].

        Args:
            min_x: Lower X boundary in meters.
            max_x: Upper X boundary in meters.
            min_y: Lower Y boundary in meters.
            max_y: Upper Y boundary in meters.
            use_cell_center: If True (default), tests cell center coordinates (center_x, center_y).
                If False, tests whether the cell's bounding square intersects the region.

        Returns:
            List of matching occupied SparseCell instances.
        """
        x0, x1 = (min_x, max_x) if min_x <= max_x else (max_x, min_x)
        y0, y1 = (min_y, max_y) if min_y <= max_y else (max_y, min_y)

        matches: List[SparseCell] = []

        if use_cell_center:
            for cell in self._cells.values():
                if x0 <= cell.center_x <= x1 and y0 <= cell.center_y <= y1:
                    matches.append(cell)
        else:
            for cell in self._cells.values():
                half = cell.resolution / 2.0
                c_min_x = cell.center_x - half
                c_max_x = cell.center_x + half
                c_min_y = cell.center_y - half
                c_max_y = cell.center_y + half
                if c_max_x >= x0 and c_min_x <= x1 and c_max_y >= y0 and c_min_y <= y1:
                    matches.append(cell)

        return matches

    def cell_count(self) -> int:
        """Return the number of actually stored/occupied sparse cells.

        Guaranteed not to include empty or theoretical unallocated cells.
        """
        return len(self._cells)

    def iter_occupied_cells(self) -> Iterator[SparseCell]:
        """Iterate strictly over populated/occupied SparseCell instances."""
        return iter(self._cells.values())

    def to_grid_cells(self, timestamp: float = 0.0) -> List[GridCell]:
        """Convert all occupied sparse cells into a list of standardized GridCell instances."""
        return [cell.to_grid_cell(timestamp=timestamp) for cell in self._cells.values()]

    def to_semantic_map(
        self,
        sensor_pose: Optional[np.ndarray] = None,
        timestamp: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SemanticMap:
        """Package populated foveated grid into the standardized SemanticMap contract dataclass.

        Args:
            sensor_pose: 4x4 vehicle/sensor transformation matrix (defaults to Identity).
            timestamp: Capture epoch timestamp.
            metadata: Optional diagnostic dictionary.

        Returns:
            Validated SemanticMap contract instance.
        """
        pose = (
            np.asarray(sensor_pose, dtype=np.float64)
            if sensor_pose is not None
            else np.eye(4, dtype=np.float64)
        )

        cells_by_level: Dict[str, List[GridCell]] = {lvl.name: [] for lvl in self._indexer.levels}
        for cell in self._cells.values():
            grid_cell = cell.to_grid_cell(timestamp=timestamp)
            cells_by_level[cell.level_name].append(grid_cell)

        res_levels = {
            lvl.name: {
                "level_id": lvl.level_id,
                "min_range": lvl.min_range,
                "max_range": lvl.max_range,
                "resolution": lvl.resolution,
                "semantic_priority": lvl.semantic_priority,
            }
            for lvl in self._indexer.levels
        }

        meta = dict(metadata or {})
        meta.update(
            {
                "occupied_cells_count": len(self._cells),
            }
        )

        return SemanticMap(
            cells=cells_by_level,
            resolution_levels=res_levels,
            sensor_pose=pose,
            timestamp=timestamp,
            metadata=meta,
        )

    def clear(self) -> None:
        """Evict all stored cells and reset to empty state."""
        self._cells.clear()

    def get_cells(self) -> Dict[CellKey, SparseCell]:
        """Return a shallow copy of the active sparse cell mapping."""
        return dict(self._cells)

    def memory_usage_breakdown(self) -> Dict[str, int]:
        """Compute an accurate, object-level memory consumption breakdown in bytes.

        Included components:
            - dict_table_bytes: Python dictionary hash table structure overhead.
            - keys_bytes: Memory allocated for all CellKey tuples.
            - cells_bytes: Memory allocated for SparseCell dataclasses and strings.
            - items_containers_bytes: Memory allocated for items list buffers.
            - payloads_bytes: Memory allocated for stored payload objects.

        Returns:
            Dictionary detailing byte allocations per category and total_bytes.
        """
        dict_table_bytes = sys.getsizeof(self._cells)
        keys_bytes = 0
        cells_bytes = 0
        items_containers_bytes = 0
        payloads_bytes = 0

        for key, cell in self._cells.items():
            keys_bytes += sys.getsizeof(key)
            cells_bytes += sys.getsizeof(cell)
            items_containers_bytes += sys.getsizeof(cell.items)
            for item in cell.items:
                payloads_bytes += sys.getsizeof(item)

        total_bytes = (
            dict_table_bytes + keys_bytes + cells_bytes + items_containers_bytes + payloads_bytes
        )

        return {
            "dict_table_bytes": dict_table_bytes,
            "keys_bytes": keys_bytes,
            "cells_bytes": cells_bytes,
            "items_containers_bytes": items_containers_bytes,
            "payloads_bytes": payloads_bytes,
            "total_bytes": total_bytes,
        }

    def memory_usage(self) -> int:
        """Return total estimated memory footprint in bytes."""
        return self.memory_usage_breakdown()["total_bytes"]


def ingest_point_cloud(
    point_cloud: Union[np.ndarray, Any],
    grid: Optional[SparseFoveatedGrid] = None,
    payloads: Optional[Union[np.ndarray, List[Any]]] = None,
) -> Tuple[SparseFoveatedGrid, BatchInsertResult]:
    """Convenience pipeline handoff function to ingest point clouds into a SparseFoveatedGrid.

    Args:
        point_cloud: Point cloud array (N, 2+) or contract object (PointCloudFrame, SemanticPointCloud).
        grid: Optional existing SparseFoveatedGrid (instantiates new default grid if None).
        payloads: Optional per-point payload array or list.

    Returns:
        Tuple of (populated SparseFoveatedGrid, BatchInsertResult statistics).
    """
    target_grid = grid or SparseFoveatedGrid()
    result = target_grid.insert_batch(point_cloud, payloads=payloads)
    return target_grid, result
