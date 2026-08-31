"""Comprehensive Unit Tests for LiDAR Preprocessing Module.

Module Owner: Amulya (Member 2)

Tests:
    1. NaN removal
    2. Infinite-value removal
    3. Invalid point handling (shapes, non-numeric)
    4. Range filtering (Euclidean distance, negative coordinates)
    5. Exact range boundaries (min_range, max_range, below, at, above)
    6. Coordinate transformations (rotation + translation)
    7. Empty input handling (graceful N=0 handling)
    8. Voxel downsampling (deterministic centroid calculation)
    9. Intensity alignment across all filtering operations
    10. Synthetic scene generation (all scene types including wall)
    11. Synthetic deterministic output (seeded repeatability)
    12. PointCloudFrame contract compliance
    13. Actual execution performance telemetry
    14. Outlier removal (statistical and radius filtering)
"""

import numpy as np
import pytest

from src.contracts import PointCloudFrame, SyntheticSceneConfig
from src.preprocessing import (
    LiDARPreprocessor,
    PreprocessingConfig,
    PreprocessingMetrics,
    filter_by_range,
    generate_synthetic_scene,
    preprocess_frame,
    remove_outliers_radius,
    remove_outliers_statistical,
    transform_coordinates,
    validate_and_sanitize_points,
    voxel_downsample,
)


def test_nan_removal() -> None:
    """Ensure NaN values in X, Y, Z or intensity are detected and removed cleanly."""
    pts = np.array(
        [
            [1.0, 2.0, 3.0],
            [np.nan, 2.0, 3.0],
            [4.0, np.nan, 6.0],
            [7.0, 8.0, np.nan],
            [10.0, 11.0, 12.0],
        ],
        dtype=np.float32,
    )
    intensity = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)

    san_pts, san_int = validate_and_sanitize_points(pts, intensity)

    assert san_pts.shape == (2, 3)
    assert san_int is not None
    assert san_int.shape == (2,)
    np.testing.assert_allclose(san_pts[0], [1.0, 2.0, 3.0])
    np.testing.assert_allclose(san_pts[1], [10.0, 11.0, 12.0])
    np.testing.assert_allclose(san_int, [0.1, 0.5])
    assert not np.isnan(san_pts).any()
    assert not np.isnan(san_int).any()


def test_infinite_value_removal() -> None:
    """Ensure positive and negative Inf values are removed."""
    pts = np.array(
        [
            [1.0, 1.0, 1.0],
            [np.inf, 2.0, 2.0],
            [3.0, -np.inf, 3.0],
            [4.0, 4.0, 4.0],
        ],
        dtype=np.float32,
    )
    intensity = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

    san_pts, san_int = validate_and_sanitize_points(pts, intensity)

    assert san_pts.shape == (2, 3)
    assert san_int is not None and san_int.shape == (2,)
    np.testing.assert_allclose(san_pts[0], [1.0, 1.0, 1.0])
    np.testing.assert_allclose(san_pts[1], [4.0, 4.0, 4.0])
    np.testing.assert_allclose(san_int, [0.1, 0.4])
    assert not np.isinf(san_pts).any()


def test_invalid_point_handling() -> None:
    """Verify that malformed inputs raise clear ValueErrors."""
    # 1D array instead of 2D
    with pytest.raises(ValueError, match="points array must have shape"):
        validate_and_sanitize_points(np.array([1.0, 2.0, 3.0]))

    # (N, 4) instead of (N, 3)
    with pytest.raises(ValueError, match="points array must have shape"):
        validate_and_sanitize_points(np.ones((10, 4)))

    # Intensity length mismatch
    with pytest.raises(ValueError, match="intensity array must have shape"):
        validate_and_sanitize_points(np.ones((10, 3)), intensity=np.ones((5,)))


def test_range_filtering_euclidean_and_negative_coords() -> None:
    """Ensure Euclidean distance filtering is calculated correctly and handles negative coords."""
    pts = np.array(
        [
            [0.0, 0.0, 0.0],       # r = 0.0 (too close)
            [0.2, 0.2, 0.1],       # r ~ 0.3 (too close)
            [-5.0, 0.0, 0.0],      # r = 5.0 (valid negative X)
            [0.0, -10.0, 0.0],     # r = 10.0 (valid negative Y)
            [0.0, 0.0, -2.0],      # r = 2.0 (valid negative Z)
            [30.0, 40.0, 0.0],     # r = 50.0 (valid)
            [80.0, 80.0, 0.0],     # r ~ 113.1 (beyond max 100m)
        ],
        dtype=np.float32,
    )
    intensity = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32)

    filtered_pts, filtered_int = filter_by_range(
        pts, intensity, min_range=0.5, max_range=100.0
    )

    # Retained points: index 2 (-5, 0, 0), 3 (0, -10, 0), 4 (0, 0, -2), 5 (30, 40, 0)
    assert filtered_pts.shape == (4, 3)
    assert filtered_int is not None and filtered_int.shape == (4,)
    np.testing.assert_allclose(filtered_pts[0], [-5.0, 0.0, 0.0])
    np.testing.assert_allclose(filtered_pts[1], [0.0, -10.0, 0.0])
    np.testing.assert_allclose(filtered_pts[2], [0.0, 0.0, -2.0])
    np.testing.assert_allclose(filtered_pts[3], [30.0, 40.0, 0.0])
    np.testing.assert_allclose(filtered_int, [0.2, 0.3, 0.4, 0.5])


def test_exact_range_boundaries() -> None:
    """Test behavior at exact boundary values: exactly on, slightly below, and slightly above."""
    pts = np.array(
        [
            [0.499, 0.0, 0.0],     # r = 0.499 (< min_range 0.5) -> drop
            [0.500, 0.0, 0.0],     # r = 0.500 (== min_range 0.5) -> keep
            [0.501, 0.0, 0.0],     # r = 0.501 (> min_range 0.5) -> keep
            [99.99, 0.0, 0.0],     # r = 99.99 (< max_range 100) -> keep
            [100.00, 0.0, 0.0],    # r = 100.0 (== max_range 100) -> keep
            [100.01, 0.0, 0.0],    # r = 100.01 (> max_range 100) -> drop
        ],
        dtype=np.float32,
    )
    filtered_pts, _ = filter_by_range(pts, min_range=0.5, max_range=100.0)

    assert filtered_pts.shape[0] == 4
    np.testing.assert_allclose(filtered_pts[:, 0], [0.500, 0.501, 99.99, 100.00], atol=1e-4)


def test_coordinate_transformations() -> None:
    """Test rigid 4x4 transformation [R | t] from sensor to vehicle base frame."""
    # Rotate 90 degrees around Z axis: (x, y, z) -> (-y, x, z), plus translation (1, 2, 3)
    c, s = 0.0, 1.0  # cos(pi/2), sin(pi/2)
    t_mat = np.array(
        [
            [c, -s, 0.0, 1.0],
            [s,  c, 0.0, 2.0],
            [0.0, 0.0, 1.0, 3.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    pts = np.array(
        [
            [2.0, 0.0, 0.0],  # expected: (-0 + 1, 2 + 2, 0 + 3) = (1.0, 4.0, 3.0)
            [0.0, 3.0, 1.0],  # expected: (-3 + 1, 0 + 2, 1 + 3) = (-2.0, 2.0, 4.0)
        ],
        dtype=np.float32,
    )

    transformed = transform_coordinates(pts, t_mat)
    assert transformed.shape == (2, 3)
    assert transformed.dtype == np.float32
    np.testing.assert_allclose(transformed[0], [1.0, 4.0, 3.0], atol=1e-5)
    np.testing.assert_allclose(transformed[1], [-2.0, 2.0, 4.0], atol=1e-5)


def test_empty_input() -> None:
    """Ensure empty point cloud inputs are handled gracefully without raising exceptions."""
    empty_pts = np.zeros((0, 3), dtype=np.float32)
    empty_int = np.zeros((0,), dtype=np.float32)

    # Test sanitization
    s_pts, s_int = validate_and_sanitize_points(empty_pts, empty_int)
    assert s_pts.shape == (0, 3)
    assert s_int is not None and s_int.shape == (0,)

    # Test range filtering
    r_pts, r_int = filter_by_range(empty_pts, empty_int)
    assert r_pts.shape == (0, 3)

    # Test voxel downsampling
    v_pts, v_int = voxel_downsample(empty_pts, empty_int)
    assert v_pts.shape == (0, 3)

    # Test full pipeline with empty frame
    empty_frame = PointCloudFrame(
        points=empty_pts,
        intensity=empty_int,
        timestamp=1.0,
        frame_id="lidar_top",
    )
    preprocessor = LiDARPreprocessor()
    proc_frame, metrics = preprocessor.preprocess(empty_frame)

    assert proc_frame.points.shape == (0, 3)
    assert metrics.input_points == 0
    assert metrics.output_points == 0
    assert metrics.reduction_ratio == 0.0


def test_voxel_downsampling_centroid() -> None:
    """Ensure points falling into the same voxel are merged into their arithmetic centroid."""
    # 4 points in a 0.1m voxel [0.0, 0.1) x [0.0, 0.1) x [0.0, 0.1)
    pts = np.array(
        [
            [0.01, 0.01, 0.01],
            [0.03, 0.03, 0.03],
            [0.05, 0.05, 0.05],
            [0.07, 0.07, 0.07],
            # 1 point in a separate voxel [1.0, 1.1)
            [1.05, 1.05, 1.05],
        ],
        dtype=np.float32,
    )
    intensity = np.array([0.1, 0.2, 0.3, 0.4, 0.9], dtype=np.float32)

    down_pts, down_int = voxel_downsample(pts, intensity, leaf_size=0.1)

    assert down_pts.shape == (2, 3)
    assert down_int is not None and down_int.shape == (2,)

    # Centroid of first 4 points: mean([0.01, 0.03, 0.05, 0.07]) = 0.04
    np.testing.assert_allclose(down_pts[0], [0.04, 0.04, 0.04], atol=1e-5)
    # Mean intensity of first 4 points: (0.1 + 0.2 + 0.3 + 0.4) / 4 = 0.25
    np.testing.assert_allclose(down_int[0], 0.25, atol=1e-5)

    # Second voxel centroid
    np.testing.assert_allclose(down_pts[1], [1.05, 1.05, 1.05], atol=1e-5)
    np.testing.assert_allclose(down_int[1], 0.9, atol=1e-5)


def test_intensity_alignment_across_pipeline() -> None:
    """Ensure intensity stays perfectly aligned with points after every stage."""
    rng = np.random.default_rng(123)
    n = 2000
    pts = rng.uniform(-50.0, 50.0, (n, 3)).astype(np.float32)
    # Insert some NaNs and Infs
    pts[10:15, 0] = np.nan
    pts[30:35, 1] = np.inf
    # Correlate intensity with coordinate so alignment can be verified: intensity = norm(pts) / 100
    norm = np.linalg.norm(pts, axis=1)
    intensity = (norm / 100.0).astype(np.float32)

    frame = PointCloudFrame(points=pts, intensity=intensity, timestamp=0.0, frame_id="lidar")

    cfg = PreprocessingConfig(
        min_range=2.0,
        max_range=40.0,
        voxel_downsample_enabled=True,
        voxel_leaf_size=0.5,
    )
    preprocessor = LiDARPreprocessor(config=cfg)
    proc_frame, metrics = preprocessor.preprocess(frame)

    assert proc_frame.intensity is not None
    assert proc_frame.points.shape[0] == proc_frame.intensity.shape[0]
    assert proc_frame.points.shape[0] == metrics.output_points
    assert metrics.output_points < metrics.input_points
    assert not np.isnan(proc_frame.points).any()
    assert not np.isnan(proc_frame.intensity).any()


@pytest.mark.parametrize(
    "scene_type", ["flat_road", "curb", "pothole", "slope", "overhang", "wall", "urban"]
)
def test_synthetic_scene_generation(scene_type: str) -> None:
    """Ensure all synthetic scene types generate compliant PointCloudFrame and SemanticPointCloud."""
    cfg = SyntheticSceneConfig(scene_type=scene_type, num_points=800, seed=42)
    frame, sem_cloud = generate_synthetic_scene(cfg)

    assert isinstance(frame, PointCloudFrame)
    assert frame.points.shape[0] == 800
    assert frame.intensity is not None and frame.intensity.shape == (800,)
    assert not np.isnan(frame.points).any()
    assert sem_cloud.points.shape == frame.points.shape
    assert sem_cloud.semantic_class.shape == (800,)


def test_synthetic_deterministic_output() -> None:
    """Ensure same seed produces byte-for-byte identical point clouds and intensities."""
    cfg1 = SyntheticSceneConfig(scene_type="urban", num_points=1200, seed=999)
    cfg2 = SyntheticSceneConfig(scene_type="urban", num_points=1200, seed=999)

    frame1, _ = generate_synthetic_scene(cfg1)
    frame2, _ = generate_synthetic_scene(cfg2)

    np.testing.assert_array_equal(frame1.points, frame2.points)
    np.testing.assert_array_equal(frame1.intensity, frame2.intensity)


def test_point_cloud_frame_contract_compliance() -> None:
    """Ensure preprocessing output strictly adheres to CONTRACTS.md specification."""
    cfg = SyntheticSceneConfig(scene_type="curb", num_points=500, seed=1)
    raw_frame, _ = generate_synthetic_scene(cfg)

    processed_frame = preprocess_frame(raw_frame)

    assert isinstance(processed_frame, PointCloudFrame)
    assert processed_frame.points.dtype == np.float32
    assert processed_frame.points.ndim == 2
    assert processed_frame.points.shape[1] == 3
    assert processed_frame.intensity is not None
    assert processed_frame.intensity.dtype == np.float32
    assert processed_frame.intensity.shape == (processed_frame.points.shape[0],)
    assert isinstance(processed_frame.timestamp, float)
    assert isinstance(processed_frame.frame_id, str)
    assert processed_frame.sensor_pose.shape == (4, 4)


def test_performance_metrics() -> None:
    """Verify actual measured telemetry: input/output counts, reduction ratio, positive latency."""
    cfg = SyntheticSceneConfig(scene_type="urban", num_points=5000, seed=7)
    raw_frame, _ = generate_synthetic_scene(cfg)

    prep_cfg = PreprocessingConfig(
        min_range=1.0,
        max_range=30.0,
        voxel_downsample_enabled=True,
        voxel_leaf_size=0.2,
    )
    preprocessor = LiDARPreprocessor(prep_cfg)
    _, metrics = preprocessor.preprocess(raw_frame)

    assert isinstance(metrics, PreprocessingMetrics)
    assert metrics.input_points == 5000
    assert metrics.output_points < 5000
    assert metrics.latency_ms > 0.0
    assert 0.0 < metrics.reduction_ratio < 1.0
    assert np.isclose(metrics.reduction_ratio + metrics.downsample_ratio, 1.0)


def test_outlier_removal_statistical_and_radius() -> None:
    """Test optional statistical and radius outlier filters."""
    # Create cluster of 50 tightly packed points and 3 distant outlier points
    rng = np.random.default_rng(42)
    cluster = rng.normal(loc=[5.0, 5.0, 0.0], scale=0.1, size=(50, 3)).astype(np.float32)
    outliers = np.array([[50.0, 50.0, 50.0], [-40.0, 30.0, 10.0], [20.0, -30.0, 5.0]], dtype=np.float32)
    pts = np.vstack([cluster, outliers])

    # Statistical outlier removal
    sor_pts, _ = remove_outliers_statistical(pts, nb_neighbors=10, std_ratio=1.5)
    assert sor_pts.shape[0] < pts.shape[0]
    # Check that far outlier [50, 50, 50] is removed
    assert not np.any(np.all(np.isclose(sor_pts, [50.0, 50.0, 50.0]), axis=1))

    # Radius outlier removal
    ror_pts, _ = remove_outliers_radius(pts, radius=0.5, min_neighbors=5)
    assert ror_pts.shape[0] == 50  # Only the cluster points have >= 5 neighbors within 0.5m
