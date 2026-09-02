"""Unit tests for LiDAR Point Cloud Preprocessing & Quality Pipeline.

Module: tests/preprocessing/test_preprocessing.py
Tests:
    - RangeFilter: boundaries, radial distance, negative coordinates, intensity slicing
    - OutlierFilter: isolated speckles, dense clusters, empty clouds
    - VoxelDownsampler: same voxel aggregation, different voxels, negative coordinates
    - GroundFilter: ground vs non-ground, threshold boundary, negative elevation
    - PreprocessingPipeline: end-to-end flow, statistics consistency, invariant enforcement
"""

import numpy as np
import pytest

from src.contracts import PointCloudFrame, PreprocessedPointCloud, PreprocessingStats
from src.preprocessing.filters import (
    GroundFilter,
    OutlierFilter,
    RangeFilter,
    VoxelDownsampler,
)
from src.preprocessing.pipeline import PreprocessingPipeline


# ==============================================================================
# 1. RangeFilter Tests
# ==============================================================================


def test_range_filter_nominal() -> None:
    """Verify points within [0.5, 100.0]m are preserved, while out-of-bounds are removed."""
    rf = RangeFilter(min_range=0.5, max_range=100.0)

    # (0.2, 0, 0) -> r=0.2 (too close)
    # (0.5, 0, 0) -> r=0.5 (exact min boundary)
    # (10.0, 0, 0) -> r=10.0 (inside)
    # (100.0, 0, 0) -> r=100.0 (exact max boundary)
    # (100.1, 0, 0) -> r=100.1 (too far)
    pts = np.array(
        [
            [0.2, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [100.0, 0.0, 0.0],
            [100.1, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    intensity = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)

    filtered_pts, filtered_int, mask = rf.filter(pts, intensity)

    assert len(filtered_pts) == 3
    assert filtered_int is not None and len(filtered_int) == 3
    assert np.allclose(filtered_pts[0], [0.5, 0.0, 0.0])
    assert np.allclose(filtered_pts[1], [10.0, 0.0, 0.0])
    assert np.allclose(filtered_pts[2], [100.0, 0.0, 0.0])
    assert np.allclose(filtered_int, [0.2, 0.3, 0.4])


def test_range_filter_negative_coordinates() -> None:
    """Verify radial filtering calculates Euclidean norm correctly in all quadrants."""
    rf = RangeFilter(min_range=1.0, max_range=50.0)

    pts = np.array(
        [
            [-3.0, -4.0, 0.0],  # r = 5.0 (inside)
            [0.0, -0.5, 0.0],   # r = 0.5 (too close)
            [-40.0, -40.0, 0.0],  # r = 56.56 (too far)
            [0.0, 0.0, -2.0],   # r = 2.0 (inside)
        ],
        dtype=np.float32,
    )

    filtered_pts, _, mask = rf.filter(pts)
    assert len(filtered_pts) == 2
    assert np.allclose(filtered_pts[0], [-3.0, -4.0, 0.0])
    assert np.allclose(filtered_pts[1], [0.0, 0.0, -2.0])


def test_range_filter_empty() -> None:
    """Verify empty point array returns empty array gracefully."""
    rf = RangeFilter()
    empty_pts = np.empty((0, 3), dtype=np.float32)
    filtered_pts, filtered_int, mask = rf.filter(empty_pts)
    assert len(filtered_pts) == 0
    assert len(mask) == 0
    assert filtered_int is None


# ==============================================================================
# 2. OutlierFilter Tests
# ==============================================================================


def test_outlier_filter_isolated_points() -> None:
    """Verify isolated noise points are filtered while clusters are preserved."""
    of = OutlierFilter(enabled=True, radius=1.0, min_neighbors=3)

    # 4 points tightly clustered around (5, 5, 0)
    cluster = np.array(
        [
            [5.0, 5.0, 0.0],
            [5.1, 5.0, 0.0],
            [5.0, 5.1, 0.0],
            [5.1, 5.1, 0.0],
        ],
        dtype=np.float32,
    )

    # 2 isolated speckles far away
    isolated = np.array(
        [
            [50.0, -50.0, 10.0],
            [-30.0, 40.0, -5.0],
        ],
        dtype=np.float32,
    )

    pts = np.vstack([cluster, isolated])
    filtered_pts, _, mask = of.filter(pts)

    assert len(filtered_pts) == 4
    assert np.allclose(filtered_pts, cluster)


def test_outlier_filter_empty_and_disabled() -> None:
    """Verify empty inputs and disabled state."""
    of = OutlierFilter(enabled=False)
    pts = np.array([[100.0, 100.0, 100.0]], dtype=np.float32)
    filtered_pts, _, mask = of.filter(pts)
    assert len(filtered_pts) == 1

    of_enabled = OutlierFilter(enabled=True)
    empty_pts = np.empty((0, 3), dtype=np.float32)
    empty_filtered, _, _ = of_enabled.filter(empty_pts)
    assert len(empty_filtered) == 0


# ==============================================================================
# 3. VoxelDownsampler Tests
# ==============================================================================


def test_voxel_downsampler_same_voxel() -> None:
    """Verify multiple points falling inside the same 5cm voxel are decimated to 1 point."""
    vd = VoxelDownsampler(enabled=True, voxel_size=0.05)

    # 3 points inside voxel [0, 0, 0] to [0.05, 0.05, 0.05]
    pts = np.array(
        [
            [0.01, 0.01, 0.01],
            [0.02, 0.02, 0.02],
            [0.03, 0.03, 0.03],
            [1.00, 1.00, 1.00],  # Different voxel
            [1.02, 1.00, 1.00],  # Same voxel as above
            [-2.01, -2.01, -2.01],  # Negative voxel
        ],
        dtype=np.float32,
    )

    downsampled, _, indices = vd.filter(pts)
    # Total unique voxels: 3
    assert len(downsampled) == 3


def test_voxel_downsampler_empty() -> None:
    """Verify empty input handling."""
    vd = VoxelDownsampler(enabled=True, voxel_size=0.10)
    empty = np.empty((0, 3), dtype=np.float32)
    out, _, _ = vd.filter(empty)
    assert len(out) == 0


# ==============================================================================
# 4. GroundFilter Tests
# ==============================================================================


def test_ground_filter_classification() -> None:
    """Verify ground surface points vs elevated obstacles are accurately classified."""
    gf = GroundFilter(enabled=True, height_threshold=0.20, min_ground_z=-0.50)

    pts = np.array(
        [
            [5.0, 0.0, 0.0],    # Road ground (Z=0.0) -> Ground
            [5.0, -1.0, 0.15],  # Curb top (Z=0.15) -> Ground (below 0.20)
            [5.0, 1.0, -0.08],  # Pothole bottom (Z=-0.08) -> Ground
            [10.0, 0.0, 0.80],  # Vehicle hood (Z=0.80) -> Non-Ground
            [8.0, 2.0, 1.50],   # Pedestrian head (Z=1.50) -> Non-Ground
            [12.0, -3.0, 4.0],  # Overhead sign (Z=4.0) -> Non-Ground
        ],
        dtype=np.float32,
    )

    ground_pts, non_ground_pts, mask = gf.filter(pts)

    assert len(ground_pts) == 3
    assert len(non_ground_pts) == 3
    assert len(ground_pts) + len(non_ground_pts) == len(pts)
    assert np.all(ground_pts[:, 2] <= 0.20)
    assert np.all(non_ground_pts[:, 2] > 0.20)


# ==============================================================================
# 5. PreprocessingPipeline Integration Tests
# ==============================================================================


def test_preprocessing_pipeline_full_execution() -> None:
    """Verify complete end-to-end preprocessing pipeline execution and statistics."""
    pipeline = PreprocessingPipeline()

    # Generate synthetic mixed frame
    rng = np.random.default_rng(123)
    n_pts = 1000
    r = rng.uniform(0.1, 110.0, size=n_pts)
    theta = rng.uniform(0, 2 * np.pi, size=n_pts)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    z = rng.uniform(-0.1, 2.5, size=n_pts)

    raw_points = np.column_stack([x, y, z]).astype(np.float32)
    frame = PointCloudFrame(
        points=raw_points,
        timestamp=100.0,
        frame_id="test_001",
    )

    result = pipeline.process(frame)

    assert isinstance(result, PreprocessedPointCloud)
    assert isinstance(result.stats, PreprocessingStats)

    # Invariant checks
    assert result.stats.raw_points == 1000
    assert len(result.points) <= 1000
    assert result.stats.ground_points + result.stats.non_ground_points == len(result.points)
    assert len(result.ground_points) == result.stats.ground_points
    assert len(result.non_ground_points) == result.stats.non_ground_points
    assert result.stats.processing_time_ms > 0.0
    assert 0.0 <= result.stats.reduction_percentage <= 100.0


def test_preprocessing_pipeline_nan_inf_handling() -> None:
    """Verify non-finite values (NaN / Inf) are sanitized without throwing exceptions."""
    pipeline = PreprocessingPipeline()

    pts_with_nan = np.array(
        [
            [10.0, 2.0, 0.0],
            [np.nan, 2.0, 0.0],
            [5.0, np.inf, 0.0],
            [-5.0, -2.0, -np.inf],
            [15.0, -1.0, 0.5],
        ],
        dtype=np.float32,
    )

    result = pipeline.process(pts_with_nan)

    assert len(result.points) == 2
    assert np.all(np.isfinite(result.points))
