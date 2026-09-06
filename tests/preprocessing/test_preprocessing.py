"""Unit tests for Preprocessing module."""

import numpy as np
from src.contracts import SyntheticSceneConfig
from src.preprocessing.synthetic import generate_synthetic_scene


def test_synthetic_scene_generation_flat_road() -> None:
    """Ensure flat road synthetic scene complies with PointCloudFrame contract."""
    config = SyntheticSceneConfig(scene_type="flat_road", num_points=1000, seed=123)
    frame, sem_cloud = generate_synthetic_scene(config)

    assert frame.points.shape[0] >= 500
    assert frame.points.shape[1] == 3
    assert np.all(np.isfinite(frame.points))
    assert sem_cloud.semantic_class.shape[0] == frame.points.shape[0]
    assert np.all(sem_cloud.confidence >= 0.0) and np.all(sem_cloud.confidence <= 1.0)


def test_synthetic_scenes_all_types() -> None:
    """Ensure all synthetic scene types generate without exceptions."""
    scene_types = ["flat_road", "curb", "pothole", "slope", "overhang", "urban"]
    for st in scene_types:
        config = SyntheticSceneConfig(scene_type=st, num_points=500, seed=42)
        frame, sem = generate_synthetic_scene(config)
        assert frame.points.ndim == 2
        assert frame.points.shape[1] == 3
        assert sem.semantic_class.ndim == 1


def test_validate_and_sanitize_points() -> None:
    """Ensure invalid, NaN, infinite and out-of-range points are properly filtered."""
    from src.preprocessing.filters import validate_and_sanitize_points

    raw_points = np.array([
        [10.0, 5.0, 0.0],       # Valid point
        [np.nan, 2.0, 0.0],     # NaN coordinate
        [5.0, np.inf, 0.0],     # Infinite coordinate
        [0.1, 0.1, 0.0],       # Below min_range (0.5m)
        [200.0, 0.0, 0.0],     # Beyond max_range (120m)
        [15.0, -2.0, -15.0],   # Below z_min (-10m)
        [20.0, 3.0, 25.0],     # Above z_max (+20m)
        [8.0, -1.0, 0.5],      # Valid point
    ], dtype=np.float32)

    raw_intensity = np.array([0.5, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.9], dtype=np.float32)
    raw_classes = np.array([0, 1, 2, 0, 1, 6, 6, 2], dtype=np.int32)

    pts, intensity, classes, mask = validate_and_sanitize_points(
        points=raw_points,
        intensity=raw_intensity,
        classes=raw_classes,
        min_range=0.5,
        max_range=120.0,
        z_min=-10.0,
        z_max=20.0,
    )

    assert pts.shape[0] == 2
    assert intensity is not None and intensity.shape[0] == 2
    assert classes is not None and classes.shape[0] == 2
    assert np.all(np.isfinite(pts))
    assert pts[0, 0] == 10.0 and pts[0, 1] == 5.0
    assert pts[1, 0] == 8.0 and pts[1, 1] == -1.0
    assert intensity[0] == 0.5 and intensity[1] == 0.9
    assert classes[0] == 0 and classes[1] == 2
    assert np.sum(mask) == 2
