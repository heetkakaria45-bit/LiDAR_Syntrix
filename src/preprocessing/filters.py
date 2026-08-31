"""Spatial Filtering and Normalization Utilities for LiDAR Point Clouds.

Module Owner: Amulya (Preprocessing)

Implements pure NumPy, deterministic algorithms for:
    - Validation and invalid point removal (NaN, Inf, non-finite values)
    - Euclidean range filtering with exact boundary handling
    - Voxel grid downsampling with centroid aggregation
    - Optional outlier removal (density-based and statistical)
    - Rigid body coordinate transformations into standard ego frame (X=forward, Y=left, Z=up)
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np


def validate_and_sanitize_points(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Validate point cloud arrays and remove non-finite (NaN, Inf) values.

    Args:
        points: Array of shape (N, 3) representing 3D coordinates.
        intensity: Optional array of shape (N,) representing intensity values.

    Returns:
        sanitized_points: (M, 3) float32 array with all finite points.
        sanitized_intensity: Optional (M,) float32 array aligned with sanitized_points.

    Raises:
        ValueError: If points is not 2D with shape (N, 3), or if intensity length
                    does not match points length.
        TypeError: If inputs cannot be converted to numeric NumPy arrays.
    """
    if not isinstance(points, np.ndarray):
        points = np.asarray(points, dtype=np.float32)

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points array must have shape (N, 3), got {points.shape}")

    # Handle empty input gracefully
    if points.shape[0] == 0:
        empty_pts = np.zeros((0, 3), dtype=np.float32)
        empty_int = np.zeros((0,), dtype=np.float32) if intensity is not None else None
        return empty_pts, empty_int

    # Mask for finite point coordinates (no NaN, +Inf, -Inf)
    finite_mask = np.all(np.isfinite(points), axis=1)

    if intensity is not None:
        if not isinstance(intensity, np.ndarray):
            intensity = np.asarray(intensity, dtype=np.float32)
        if intensity.ndim != 1 or intensity.shape[0] != points.shape[0]:
            raise ValueError(
                f"intensity array must have shape (N,), got {intensity.shape} "
                f"for points of length {points.shape[0]}"
            )
        # Intensity must also be finite
        finite_mask &= np.isfinite(intensity)
        sanitized_intensity = intensity[finite_mask].astype(np.float32, copy=False)
    else:
        sanitized_intensity = None

    sanitized_points = points[finite_mask].astype(np.float32, copy=False)
    return sanitized_points, sanitized_intensity


def filter_by_range(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    min_range: float = 0.5,
    max_range: float = 100.0,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Filter points based on Euclidean 3D distance from the sensor origin.

    Calculates radial distance r = sqrt(x^2 + y^2 + z^2).
    Points satisfying min_range <= r <= max_range are retained.

    Deterministic behavior:
        - Points with r < min_range (including zero-distance origin noise) are removed.
        - Exact boundary points (r == min_range or r == max_range) are retained.
        - Negative coordinates with valid Euclidean distance (e.g. x = -5, y = 0, z = 0 -> r = 5)
          are correctly retained. Coordinate sign is never confused with radial distance.
        - Points beyond max_range are removed.

    Args:
        points: (N, 3) array of point coordinates.
        intensity: Optional (N,) array of intensity values.
        min_range: Minimum Euclidean distance in meters (inclusive).
        max_range: Maximum Euclidean distance in meters (inclusive).

    Returns:
        filtered_points: (M, 3) float32 array.
        filtered_intensity: Optional (M,) float32 array.

    Raises:
        ValueError: If min_range < 0 or min_range > max_range.
    """
    if min_range < 0.0:
        raise ValueError(f"min_range must be non-negative, got {min_range}")
    if min_range > max_range:
        raise ValueError(
            f"min_range ({min_range}) cannot be greater than max_range ({max_range})"
        )

    if points.shape[0] == 0:
        empty_pts = np.zeros((0, 3), dtype=np.float32)
        empty_int = np.zeros((0,), dtype=np.float32) if intensity is not None else None
        return empty_pts, empty_int

    # Calculate squared Euclidean distance to avoid unnecessary square root where appropriate,
    # but compute exact r for numerical precision on boundary comparisons.
    r_sq = np.sum(points.astype(np.float64) ** 2, axis=1)
    r = np.sqrt(r_sq)

    # Use tolerance for exact boundary comparisons to mitigate floating point inaccuracies
    tol = 1e-6
    mask = (r >= (min_range - tol)) & (r <= (max_range + tol))

    filtered_points = points[mask].astype(np.float32, copy=False)
    filtered_intensity = (
        intensity[mask].astype(np.float32, copy=False) if intensity is not None else None
    )

    return filtered_points, filtered_intensity


def voxel_downsample(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    leaf_size: float = 0.05,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Deterministic voxel grid downsampling using pure NumPy.

    Partitions space into uniform 3D cubic voxels of size `leaf_size`.
    All points falling inside the same voxel are merged into their arithmetic
    centroid (mean XYZ coordinate) and mean intensity.

    Args:
        points: (N, 3) array of point coordinates.
        intensity: Optional (N,) array of intensity values.
        leaf_size: Voxel edge length in meters. Must be > 0.

    Returns:
        downsampled_points: (K, 3) float32 array of voxel centroids.
        downsampled_intensity: Optional (K,) float32 array of average intensities.

    Raises:
        ValueError: If leaf_size <= 0.
    """
    if leaf_size <= 0.0:
        raise ValueError(f"leaf_size must be positive, got {leaf_size}")

    if points.shape[0] == 0:
        empty_pts = np.zeros((0, 3), dtype=np.float32)
        empty_int = np.zeros((0,), dtype=np.float32) if intensity is not None else None
        return empty_pts, empty_int

    # Discretize coordinates into 3D integer voxel coordinates
    voxel_coords = np.floor(points / leaf_size).astype(np.int64)

    # Group points by unique voxel coordinates using np.unique
    _, inverse_indices, counts = np.unique(
        voxel_coords, axis=0, return_inverse=True, return_counts=True
    )
    num_voxels = counts.shape[0]

    # Accumulate point coordinates per voxel
    sum_points = np.zeros((num_voxels, 3), dtype=np.float64)
    np.add.at(sum_points, inverse_indices, points.astype(np.float64))
    centroid_points = (sum_points / counts[:, None]).astype(np.float32)

    # Accumulate intensity per voxel if provided
    if intensity is not None:
        sum_intensity = np.zeros((num_voxels,), dtype=np.float64)
        np.add.at(sum_intensity, inverse_indices, intensity.astype(np.float64))
        centroid_intensity = (sum_intensity / counts).astype(np.float32)
    else:
        centroid_intensity = None

    return centroid_points, centroid_intensity


def remove_outliers_statistical(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
    max_eval_points: int = 50000,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Optional statistical outlier removal (SOR).

    For each point, calculates average distance to its k-nearest neighbors.
    Points with mean neighbor distance > global_mean + std_ratio * global_std
    are rejected as outliers.

    To maintain real-time performance on a hackathon budget without requiring
    heavy dependencies (e.g. Open3D/Torch/C++), this implementation uses:
    - Fast spatial voxel-grid neighbor querying for high-throughput filtering, or
    - Direct chunked k-NN for moderate point cloud sizes.

    Args:
        points: (N, 3) array of point coordinates.
        intensity: Optional (N,) array of intensity values.
        nb_neighbors: Number of neighbors to analyze per point (k).
        std_ratio: Standard deviation multiplier threshold.
        max_eval_points: Maximum points to evaluate with full k-NN before fallback
                         to fast spatial density filtering.

    Returns:
        inlier_points: (M, 3) float32 array.
        inlier_intensity: Optional (M,) float32 array.
    """
    n_pts = points.shape[0]
    if n_pts <= nb_neighbors or nb_neighbors <= 0:
        return points.copy(), (intensity.copy() if intensity is not None else None)

    # If point count is within chunked k-NN limit, perform exact k-NN distance analysis
    if n_pts <= max_eval_points:
        # Evaluate k-NN distances in memory-safe chunks
        k = nb_neighbors
        mean_dists = np.zeros(n_pts, dtype=np.float32)
        chunk_size = 2000

        for i in range(0, n_pts, chunk_size):
            chunk = points[i : i + chunk_size]
            # Compute squared distances between chunk and all points: (chunk_size, N)
            diff = chunk[:, None, :] - points[None, :, :]
            dists_sq = np.sum(diff**2, axis=-1)
            # Find k smallest distances per point (skip self at index 0)
            # np.partition is O(N) per query point
            part_idx = np.argpartition(dists_sq, kth=k, axis=1)[:, : k + 1]
            k_dists = np.take_along_axis(dists_sq, part_idx, axis=1)
            k_dists.sort(axis=1)
            # Take mean of k nearest non-zero neighbors
            mean_dists[i : i + chunk_size] = np.mean(np.sqrt(k_dists[:, 1 : k + 1]), axis=1)

        global_mean = float(np.mean(mean_dists))
        global_std = float(np.std(mean_dists))
        threshold = global_mean + std_ratio * global_std
        inlier_mask = mean_dists <= threshold
    else:
        # For very large point clouds, use fast spatial cell density filtering
        # Points in isolated sparse voxels are considered statistical outliers
        voxel_size = 0.5  # 50 cm voxel bins
        coords = np.floor(points / voxel_size).astype(np.int64)
        _, inverse_idx, counts = np.unique(coords, axis=0, return_inverse=True, return_counts=True)
        point_density = counts[inverse_idx]
        mean_dens = float(np.mean(point_density))
        std_dens = float(np.std(point_density))
        # Keep points whose local voxel density is not excessively low
        threshold = max(2, int(mean_dens - std_ratio * std_dens))
        inlier_mask = point_density >= threshold

    inlier_points = points[inlier_mask].astype(np.float32, copy=False)
    inlier_intensity = (
        intensity[inlier_mask].astype(np.float32, copy=False) if intensity is not None else None
    )

    return inlier_points, inlier_intensity


def remove_outliers_radius(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    radius: float = 0.5,
    min_neighbors: int = 5,
    chunk_size: int = 2000,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Optional radius outlier removal (ROR).

    Removes points that have fewer than `min_neighbors` within a Euclidean sphere
    of radius `radius`.

    Args:
        points: (N, 3) point array.
        intensity: Optional (N,) intensity array.
        radius: Sphere search radius in meters.
        min_neighbors: Minimum number of neighbor points required (excluding self).
        chunk_size: Processing batch size for memory-safe vectorized evaluation.

    Returns:
        inlier_points: (M, 3) float32 array.
        inlier_intensity: Optional (M,) float32 array.
    """
    n_pts = points.shape[0]
    if n_pts <= min_neighbors:
        return points.copy(), (intensity.copy() if intensity is not None else None)

    r_sq = radius * radius
    inlier_mask = np.zeros(n_pts, dtype=bool)

    for i in range(0, n_pts, chunk_size):
        chunk = points[i : i + chunk_size]
        diff = chunk[:, None, :] - points[None, :, :]
        dists_sq = np.sum(diff**2, axis=-1)
        # Count points within radius (subtract 1 to exclude self at distance 0)
        neighbor_counts = np.sum(dists_sq <= r_sq, axis=1) - 1
        inlier_mask[i : i + chunk_size] = neighbor_counts >= min_neighbors

    inlier_points = points[inlier_mask].astype(np.float32, copy=False)
    inlier_intensity = (
        intensity[inlier_mask].astype(np.float32, copy=False) if intensity is not None else None
    )
    return inlier_points, inlier_intensity


def transform_coordinates(
    points: np.ndarray,
    transform_matrix: np.ndarray,
) -> np.ndarray:
    """Apply a 4x4 rigid body transformation matrix [R | t] to 3D points.

    Formula:
        p_base = R * p_sensor + t

    Args:
        points: (N, 3) array of coordinates in sensor frame.
        transform_matrix: (4, 4) transformation matrix [R | t].

    Returns:
        transformed_points: (N, 3) float32 array in target base frame.

    Raises:
        ValueError: If transform_matrix is not of shape (4, 4).
    """
    if not isinstance(transform_matrix, np.ndarray):
        transform_matrix = np.asarray(transform_matrix, dtype=np.float64)

    if transform_matrix.shape != (4, 4):
        raise ValueError(
            f"transform_matrix must have shape (4, 4), got {transform_matrix.shape}"
        )

    if points.shape[0] == 0:
        return np.zeros((0, 3), dtype=np.float32)

    # Extract rotation R (3, 3) and translation t (3,)
    rotation = transform_matrix[:3, :3].astype(np.float64)
    translation = transform_matrix[:3, 3].astype(np.float64)

    # p' = (R @ p.T).T + t = p @ R.T + t
    pts_f64 = points.astype(np.float64)
    transformed = pts_f64 @ rotation.T + translation

    return transformed.astype(np.float32)
