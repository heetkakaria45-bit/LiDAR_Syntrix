"""LiDAR Point Cloud Validation, Sanitization, and Filtering Utilities.

Module Owner: Amulya (src/preprocessing/)
Responsibilities:
    - Ingest raw point clouds and remove NaNs, Infs, and invalid points
    - Range and bounding-box spatial filtering [r_min, r_max], [z_min, z_max]
    - Calibrate and normalize reflection intensity
    - Ensure strict conformance to PointCloudFrame contract
"""

from typing import Optional, Tuple
import numpy as np


def validate_and_sanitize_points(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    classes: Optional[np.ndarray] = None,
    min_range: float = 0.5,
    max_range: float = 120.0,
    z_min: float = -10.0,
    z_max: float = 20.0,
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], np.ndarray]:
    """Validate, clean, and sanitize a raw 3D point cloud.

    Filters:
        1. Non-finite coordinates (NaNs, +Inf, -Inf)
        2. Radial distance bounds: min_range <= sqrt(x^2 + y^2) <= max_range
        3. Elevation bounds: z_min <= z <= z_max

    Args:
        points: (N, 3) raw point array of float32.
        intensity: Optional (N,) raw intensity array.
        classes: Optional (N,) raw class label array.
        min_range: Minimum radial distance in meters from sensor origin.
        max_range: Maximum radial distance in meters from sensor origin.
        z_min: Minimum allowable Z height in meters.
        z_max: Maximum allowable Z height in meters.

    Returns:
        Tuple of:
            - sanitized_points: (M, 3) cleaned np.ndarray of float32
            - sanitized_intensity: (M,) cleaned intensity array, or None
            - sanitized_classes: (M,) cleaned class array, or None
            - valid_mask: (N,) boolean mask of retained points
    """
    if not isinstance(points, np.ndarray):
        points = np.asarray(points, dtype=np.float32)

    n_points = points.shape[0]
    if n_points == 0 or points.ndim != 2 or points.shape[1] != 3:
        empty_pts = np.zeros((0, 3), dtype=np.float32)
        empty_mask = np.zeros((n_points,), dtype=bool)
        return (
            empty_pts,
            np.zeros((0,), dtype=np.float32) if intensity is not None else None,
            np.zeros((0,), dtype=np.int32) if classes is not None else None,
            empty_mask,
        )

    # 1. Finite check
    finite_mask = np.isfinite(points).all(axis=1)

    # 2. Distance and Z bounds check
    xy_dist = np.hypot(points[:, 0], points[:, 1])
    range_mask = (xy_dist >= min_range) & (xy_dist <= max_range)
    z_mask = (points[:, 2] >= z_min) & (points[:, 2] <= z_max)

    valid_mask = finite_mask & range_mask & z_mask

    sanitized_points = points[valid_mask].astype(np.float32)

    sanitized_intensity = None
    if intensity is not None:
        if not isinstance(intensity, np.ndarray):
            intensity = np.asarray(intensity, dtype=np.float32)
        if intensity.shape[0] == n_points:
            sanitized_intensity = intensity[valid_mask].astype(np.float32)

    sanitized_classes = None
    if classes is not None:
        if not isinstance(classes, np.ndarray):
            classes = np.asarray(classes, dtype=np.int32)
        if classes.shape[0] == n_points:
            sanitized_classes = classes[valid_mask].astype(np.int32)

    return sanitized_points, sanitized_intensity, sanitized_classes, valid_mask
