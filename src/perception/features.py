"""
Vectorized Geometric & Statistical Feature Extraction for 3D LiDAR Point Clouds.
Module Owner: Vedant (src/perception/)

Extracts discriminative point-wise and local column geometric features:
- Ground surface profile & height above ground (dz)
- Cylindrical and spherical coordinates (range, elevation angle, azimuth)
- Column height extent, point density, and vertical variance
- Intensity features
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np


class PointCloudFeatureExtractor:
    """
    Vectorized feature extractor designed for real-time inference.
    Processes tens of thousands of points in milliseconds.
    """

    def __init__(
        self,
        grid_resolution_m: float = 0.5,
        min_range_m: float = 0.5,
        max_range_m: float = 100.0,
    ) -> None:
        self.grid_res = grid_resolution_m
        self.min_range = min_range_m
        self.max_range = max_range_m

    def extract_features(
        self,
        points: np.ndarray,
        intensity: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Extracts an (N, D) feature matrix from (N, 3) point coordinates.

        Feature columns (D=10):
            0: x (m)
            1: y (m)
            2: z (m)
            3: r_xy (horizontal range in m)
            4: elevation_angle (rad)
            5: azimuth_angle (rad)
            6: height_above_ground dz (m)
            7: column_height_span (m)
            8: column_point_count (normalized)
            9: normalized_intensity [0, 1]
        """
        N = points.shape[0]
        if N == 0:
            return np.zeros((0, 10), dtype=np.float32)

        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2]

        # 1. Range and angular coordinates
        r_xy = np.sqrt(x * x + y * y)
        r_3d = np.sqrt(x * x + y * y + z * z)
        eps = 1e-6
        safe_r3d = np.maximum(r_3d, eps)
        elevation_angle = np.arcsin(np.clip(z / safe_r3d, -1.0, 1.0))
        azimuth_angle = np.arctan2(y, x)

        # 2. Robust ground surface height estimation
        # Estimate reference ground baseline from the lower quantile of the scene
        if N >= 10:
            scene_ground_ref = float(np.percentile(z, 5))
        elif N > 0:
            scene_ground_ref = float(np.min(z))
        else:
            scene_ground_ref = 0.0

        # Discretize (x, y) into regular spatial columns
        ix = np.floor(x / self.grid_res).astype(np.int32)
        iy = np.floor(y / self.grid_res).astype(np.int32)

        # Create unique column keys using 64-bit integer hashing
        col_keys = (ix.astype(np.int64) << 32) ^ (iy.astype(np.int64) & 0xFFFFFFFF)
        unique_keys, inverse_indices = np.unique(col_keys, return_inverse=True)

        # Vectorized column-level aggregations
        num_cols = len(unique_keys)
        col_min_z = np.full(num_cols, 1e6, dtype=np.float32)
        col_max_z = np.full(num_cols, -1e6, dtype=np.float32)
        col_counts = np.bincount(inverse_indices, minlength=num_cols).astype(np.float32)

        # Min and Max reduction per column
        np.minimum.at(col_min_z, inverse_indices, z)
        np.maximum.at(col_max_z, inverse_indices, z)

        # For columns where points are elevated (e.g. pole top, sign), anchor to scene_ground_ref
        col_ground = np.where(col_min_z > scene_ground_ref + 0.6, scene_ground_ref, col_min_z)
        est_ground_z = col_ground[inverse_indices]
        height_above_ground = z - est_ground_z

        # Vertical column span (accounting for elevated ground difference)
        raw_span = (col_max_z - col_min_z)[inverse_indices]
        column_span = np.maximum(raw_span, height_above_ground)
        column_density = np.clip(col_counts[inverse_indices] / 50.0, 0.0, 1.0)

        # 3. Intensity handling
        if intensity is not None and intensity.shape[0] == N:
            norm_intensity = np.clip(intensity / 255.0, 0.0, 1.0).astype(np.float32)
        else:
            norm_intensity = np.zeros(N, dtype=np.float32)

        # Stack into (N, 10) feature array
        features = np.column_stack([
            x,
            y,
            z,
            r_xy,
            elevation_angle,
            azimuth_angle,
            height_above_ground,
            column_span,
            column_density,
            norm_intensity,
        ]).astype(np.float32)

        return features
