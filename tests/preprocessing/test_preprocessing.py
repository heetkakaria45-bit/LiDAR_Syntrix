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
