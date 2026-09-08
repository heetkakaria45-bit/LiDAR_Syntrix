"""Foveated Spatial Indexing & Multi-Ring Spatial Grid Architecture.

Module Owner: Manashri (src/foveated_grid/)
Responsibilities:
    - Multi-ring hierarchical data structure
    - Spatial indexing and deterministic coordinate conversion
    - High-speed point-to-cell assignment
    - Half-open ring boundary handling [r_k, r_{k+1})
    - Memory-efficient spatial hash / multi-grid indexing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class FoveationRing:
    """Configuration for a single concentric foveation ring."""

    level_id: int
    name: str
    min_range: float
    max_range: float
    resolution: float
    semantic_priority: float = 1.0


DEFAULT_RINGS = [
    FoveationRing(level_id=0, name="near", min_range=0.0, max_range=10.0, resolution=0.05, semantic_priority=1.0),
    FoveationRing(level_id=1, name="mid_near", min_range=10.0, max_range=25.0, resolution=0.10, semantic_priority=0.8),
    FoveationRing(level_id=2, name="mid", min_range=25.0, max_range=50.0, resolution=0.20, semantic_priority=0.5),
    FoveationRing(level_id=3, name="far", min_range=50.0, max_range=100.0, resolution=0.50, semantic_priority=0.2),
]


class FoveatedGridIndexer:
    """Deterministic Multi-Ring Foveated Spatial Indexer."""

    def __init__(self, rings: Optional[List[FoveationRing]] = None, max_radius: float = 100.0):
        self.rings = rings if rings is not None else DEFAULT_RINGS
        self.max_radius = max_radius
        self._rings_by_id = {r.level_id: r for r in self.rings}

    def get_ring_for_distance(self, distance: float) -> Optional[FoveationRing]:
        """Find the foveation ring for a given distance using half-open intervals [min, max)."""
        if distance < 0 or distance > self.max_radius:
            return None
        for ring in self.rings:
            if ring.min_range <= distance < ring.max_range:
                return ring
        # Boundary case for max_radius
        if distance == self.max_radius:
            return self.rings[-1]
        return None

    def world_to_cell(self, x: float, y: float) -> Optional[Tuple[int, int, int, float, float]]:
        """Map 2D Cartesian world coordinates (meters) to grid cell indices and center.

        Returns:
            Tuple of (level_id, cell_ix, cell_iy, center_x, center_y) or None if out of bounds.
        """
        distance = float(np.hypot(x, y))
        ring = self.get_ring_for_distance(distance)
        if ring is None:
            return None

        res = ring.resolution
        cell_ix = int(np.floor(x / res))
        cell_iy = int(np.floor(y / res))
        center_x = (cell_ix + 0.5) * res
        center_y = (cell_iy + 0.5) * res

        return ring.level_id, cell_ix, cell_iy, center_x, center_y

    def cell_to_world(self, level_id: int, cell_ix: int, cell_iy: int) -> Tuple[float, float, float]:
        """Map grid cell indices back to world Cartesian coordinates and cell resolution.

        Returns:
            Tuple of (center_x, center_y, resolution).
        """
        ring = self._rings_by_id.get(level_id)
        if ring is None:
            raise ValueError(f"Unknown ring level_id: {level_id}")
        res = ring.resolution
        center_x = (cell_ix + 0.5) * res
        center_y = (cell_iy + 0.5) * res
        return center_x, center_y, res

    def bin_points(
        self, points: np.ndarray
    ) -> Dict[Tuple[int, int, int], List[int]]:
        """Vectorized / fast binning of (N, 3) points into multi-resolution cells.

        Returns:
            Dictionary mapping (level_id, cell_ix, cell_iy) -> list of point indices.
        """
        if points.shape[0] == 0:
            return {}

        x = points[:, 0]
        y = points[:, 1]
        distances = np.hypot(x, y)

        cell_bins: Dict[Tuple[int, int, int], List[int]] = {}

        for ring in self.rings:
            # Mask points falling into this ring's distance interval
            if ring.level_id == self.rings[-1].level_id:
                mask = (distances >= ring.min_range) & (distances <= ring.max_range)
            else:
                mask = (distances >= ring.min_range) & (distances < ring.max_range)

            indices = np.nonzero(mask)[0]
            if indices.size == 0:
                continue

            res = ring.resolution
            ixs = np.floor(x[indices] / res).astype(np.int32)
            iys = np.floor(y[indices] / res).astype(np.int32)

            for p_idx, c_ix, c_iy in zip(indices, ixs, iys):
                key = (ring.level_id, int(c_ix), int(c_iy))
                if key not in cell_bins:
                    cell_bins[key] = []
                cell_bins[key].append(int(p_idx))

        return cell_bins

    def assign_points(
        self, points: np.ndarray
    ) -> Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]:
        """Assign (N, 3) points to foveation levels and discrete 2D grid cells.

        Returns:
            Dict mapping ring_name (str) -> (grid_x, grid_y) -> (center_x, center_y, point_indices_array)
        """
        n_points = points.shape[0]
        grid_assignments: Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]] = {
            ring.name: {} for ring in self.rings
        }
        if n_points == 0:
            return grid_assignments

        x = points[:, 0]
        y = points[:, 1]
        dist = np.hypot(x, y)
        assigned = np.zeros(n_points, dtype=bool)

        for ring in self.rings:
            if ring.level_id == self.rings[-1].level_id:
                mask = (~assigned) & (dist >= ring.min_range) & (dist <= ring.max_range)
            else:
                mask = (~assigned) & (dist >= ring.min_range) & (dist < ring.max_range)

            assigned |= mask
            indices = np.nonzero(mask)[0]
            if indices.size == 0:
                continue

            res = ring.resolution
            px = x[indices]
            py = y[indices]

            gx = np.floor(px / res).astype(np.int32)
            gy = np.floor(py / res).astype(np.int32)

            keys = np.stack([gx, gy], axis=1)
            unique_keys, inverse_idx, counts = np.unique(
                keys, axis=0, return_inverse=True, return_counts=True
            )

            order = np.argsort(inverse_idx, kind="stable")
            sorted_indices = indices[order]
            splits = np.split(sorted_indices, np.cumsum(counts)[:-1])

            half_res = res / 2.0
            for (cx_idx, cy_idx), cell_point_indices in zip(unique_keys, splits):
                center_x = float(cx_idx * res + half_res)
                center_y = float(cy_idx * res + half_res)
                grid_assignments[ring.name][(int(cx_idx), int(cy_idx))] = (
                    center_x,
                    center_y,
                    cell_point_indices,
                )

        return grid_assignments

    def compute_adaptive_resolution(
        self,
        base_resolution: float,
        semantic_priority: float = 0.0,
        uncertainty: float = 0.0,
        w_sem: float = 0.5,
        w_unc: float = 0.3,
    ) -> float:
        """Compute target adaptive resolution given distance base, semantic importance and uncertainty.

        Refinement formula:
            res_target = res_base * (1.0 - w_sem * priority) * (1.0 - w_unc * uncertainty)
        """
        sem_factor = np.clip(1.0 - (w_sem * semantic_priority), 0.2, 1.0)
        unc_factor = np.clip(1.0 - (w_unc * uncertainty), 0.5, 1.0)
        refined_res = base_resolution * float(sem_factor * unc_factor)
        # Bounded by finest resolution (5 cm) and base resolution
        return float(np.clip(refined_res, 0.05, base_resolution))

    def compute_navigation_importance(
        self,
        x: float,
        y: float,
        semantic_class: int = 0,
        is_hazard: bool = False,
        is_non_traversable: bool = False,
        uncertainty: float = 0.0,
        importance_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, float], bool]:
        """Compute navigation-aware spatial importance for a given Cartesian coordinate."""
        cfg = importance_config or {}
        w_dist = float(cfg.get("distance_weight", 0.25))
        w_sem = float(cfg.get("semantic_weight", 0.35))
        w_haz = float(cfg.get("hazard_weight", 0.25))
        w_risk = float(cfg.get("risk_weight", 0.15))
        threshold = float(cfg.get("refinement_threshold", 0.60))
        corridor_width = float(cfg.get("corridor_width", 3.6))
        corridor_max_dist = float(cfg.get("corridor_max_dist", 50.0))

        semantic_weights = {
            0: 0.10, 1: 0.40, 2: 0.90, 3: 1.00,
            4: 1.00, 5: 0.60, 6: 0.80, 7: 0.75,
        }
        s_sem = float(semantic_weights.get(semantic_class, 0.50))
        r = float(np.hypot(x, y))

        in_corridor = (x > 0.0) and (abs(y) <= (corridor_width / 2.0))
        if in_corridor:
            s_dist = max(0.0, 1.0 - (r / corridor_max_dist))
        else:
            s_dist = 0.30 * max(0.0, 1.0 - (r / self.max_radius))

        s_haz = 1.0 if is_hazard else 0.0
        s_risk = 1.0 if is_non_traversable else (0.5 if uncertainty > 0.6 else 0.0)

        total_score = float(
            np.clip(
                w_dist * s_dist + w_sem * s_sem + w_haz * s_haz + w_risk * s_risk,
                0.0,
                1.0,
            )
        )
        requires_refinement = bool(total_score >= threshold and r >= 10.0 and r < self.max_radius)

        component_scores = {
            "distance_score": float(s_dist),
            "semantic_score": float(s_sem),
            "hazard_score": float(s_haz),
            "risk_score": float(s_risk),
            "total_score": float(total_score),
        }
        return total_score, component_scores, requires_refinement

    def refine_local_patch(
        self,
        points: np.ndarray,
        center_x: float,
        center_y: float,
        radius: float = 2.5,
        target_resolution: float = 0.10,
    ) -> Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]:
        """Extract and refine only the localized region surrounding a critical obstacle/hazard."""
        if points.shape[0] == 0:
            return {}

        px = points[:, 0]
        py = points[:, 1]
        dist_to_center = np.hypot(px - center_x, py - center_y)

        patch_mask = dist_to_center <= radius
        patch_indices = np.nonzero(patch_mask)[0]
        if patch_indices.size == 0:
            return {}

        res = target_resolution
        gx = np.floor(px[patch_indices] / res).astype(np.int32)
        gy = np.floor(py[patch_indices] / res).astype(np.int32)

        keys = np.stack([gx, gy], axis=1)
        unique_keys, inverse_idx, counts = np.unique(
            keys, axis=0, return_inverse=True, return_counts=True
        )

        order = np.argsort(inverse_idx, kind="stable")
        sorted_indices = patch_indices[order]
        splits = np.split(sorted_indices, np.cumsum(counts)[:-1])

        half_res = res / 2.0
        refined_cells: Dict[Tuple[int, int], Tuple[float, float, np.ndarray]] = {}
        for (cx_idx, cy_idx), cell_pt_indices in zip(unique_keys, splits):
            cx = float(cx_idx * res + half_res)
            cy = float(cy_idx * res + half_res)
            refined_cells[(int(cx_idx), int(cy_idx))] = (cx, cy, cell_pt_indices)

        return refined_cells

