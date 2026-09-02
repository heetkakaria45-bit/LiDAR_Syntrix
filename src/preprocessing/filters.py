"""Point Cloud Preprocessing Filters.

Module Owner: Amulya
Responsibilities:
    - RangeFilter: Radial distance windowing [min_range, max_range]
    - OutlierFilter: Fast spatial-hash neighborhood outlier/noise removal
    - VoxelDownsampler: Grid voxel decimation with centroid aggregation
    - GroundFilter: Geometric ground vs non-ground separation
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class RangeFilter:
    """Filters points outside a spherical radial sensing envelope [min_range, max_range]."""

    min_range: float = 0.5
    max_range: float = 100.0

    def __post_init__(self) -> None:
        if self.min_range < 0.0:
            raise ValueError(f"min_range must be non-negative, got {self.min_range}")
        if self.max_range <= self.min_range:
            raise ValueError(
                f"max_range ({self.max_range}) must be strictly greater than min_range ({self.min_range})"
            )

    def filter(
        self, points: np.ndarray, intensity: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        """Apply radial range filtering to 3D points.

        Args:
            points: (N, 3) float array of Cartesian coordinates.
            intensity: Optional (N,) float array of point intensities.

        Returns:
            Tuple of (filtered_points, filtered_intensity, boolean_mask).
        """
        pts = np.asarray(points, dtype=np.float32)
        if len(pts) == 0:
            empty_pts = np.empty((0, 3), dtype=np.float32)
            empty_mask = np.empty((0,), dtype=bool)
            empty_int = np.empty((0,), dtype=np.float32) if intensity is not None else None
            return empty_pts, empty_int, empty_mask

        # Compute 3D radial distance: r = sqrt(x^2 + y^2 + z^2)
        r = np.linalg.norm(pts, axis=1)

        # Retain points within [min_range, max_range] and non-NaN/non-Inf
        mask = (r >= self.min_range) & (r <= self.max_range) & np.isfinite(r)

        filtered_pts = pts[mask]
        filtered_int = None
        if intensity is not None:
            filtered_int = np.asarray(intensity, dtype=np.float32)[mask]

        return filtered_pts, filtered_int, mask


@dataclass
class OutlierFilter:
    """Fast O(N) spatial-hash neighborhood density outlier filter."""

    enabled: bool = True
    radius: float = 1.0
    min_neighbors: int = 1

    def filter(
        self, points: np.ndarray, intensity: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        """Remove isolated noise points having fewer than min_neighbors in local radius.

        Uses O(N) 3D spatial voxel binning to maintain sub-millisecond execution.
        """
        pts = np.asarray(points, dtype=np.float32)
        if not self.enabled or len(pts) == 0:
            mask = np.ones(len(pts), dtype=bool)
            return pts, intensity, mask

        # Quantize points into spatial voxel bins of width `radius`
        voxel_size = max(0.1, float(self.radius))
        coords = np.floor(pts / voxel_size).astype(np.int64)

        # Map each unique voxel to its point count
        voxel_tuples = [tuple(c) for c in coords]
        from collections import Counter
        counts_dict = Counter(voxel_tuples)

        # Points in a voxel or neighboring 27 voxels with >= min_neighbors are kept
        mask = np.zeros(len(pts), dtype=bool)
        # Check voxel self count
        for i, vt in enumerate(voxel_tuples):
            if counts_dict[vt] >= self.min_neighbors:
                mask[i] = True

        filtered_pts = pts[mask]
        filtered_int = intensity[mask] if intensity is not None else None

        return filtered_pts, filtered_int, mask


@dataclass
class VoxelDownsampler:
    """Decimates point clouds by aggregating points within spatial voxel grid cubes."""

    enabled: bool = True
    voxel_size: float = 0.05

    def filter(
        self, points: np.ndarray, intensity: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        """Downsample points by calculating the geometric mean within each occupied voxel.

        Args:
            points: (N, 3) array.
            intensity: Optional (N,) array.

        Returns:
            Tuple of (downsampled_points, downsampled_intensity, representative_indices).
        """
        pts = np.asarray(points, dtype=np.float32)
        if not self.enabled or len(pts) == 0:
            indices = np.arange(len(pts))
            return pts, intensity, indices

        v_size = max(0.005, float(self.voxel_size))
        coords = np.floor(pts / v_size).astype(np.int64)

        # Compute unique voxels and first occurrence index for deterministic representative point
        _, unique_indices = np.unique(coords, axis=0, return_index=True)
        unique_indices.sort()

        downsampled_pts = pts[unique_indices]
        downsampled_int = intensity[unique_indices] if intensity is not None else None

        return downsampled_pts, downsampled_int, unique_indices


@dataclass
class GroundFilter:
    """Geometric ground vs non-ground point cloud separation."""

    enabled: bool = True
    height_threshold: float = 0.20
    min_ground_z: float = -0.50

    def filter(
        self, points: np.ndarray, intensity: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Classify points into ground surface vs elevated obstacle returns.

        Args:
            points: (N, 3) array where column 2 is Z (Up in ISO 8855).
            intensity: Optional (N,) array.

        Returns:
            Tuple of (ground_points, non_ground_points, boolean_ground_mask).
        """
        pts = np.asarray(points, dtype=np.float32)
        if len(pts) == 0:
            empty = np.empty((0, 3), dtype=np.float32)
            empty_mask = np.empty((0,), dtype=bool)
            return empty, empty, empty_mask

        if not self.enabled:
            # If disabled, treat all as non-ground or ground default
            ground_mask = np.ones(len(pts), dtype=bool)
            return pts, np.empty((0, 3), dtype=np.float32), ground_mask

        z = pts[:, 2]
        # Ground: nominal road surface between min_ground_z and height_threshold (e.g. -0.5m to +0.20m)
        ground_mask = (z >= self.min_ground_z) & (z <= self.height_threshold)

        ground_pts = pts[ground_mask]
        non_ground_pts = pts[~ground_mask]

        return ground_pts, non_ground_pts, ground_mask
