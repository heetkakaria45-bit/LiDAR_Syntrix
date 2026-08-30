"""Test synthetic scene generator for contract compliance and determinism."""

import numpy as np
import pytest

from src.contracts import PointCloudFrame, SemanticPointCloud, SyntheticSceneConfig
from src.preprocessing.synthetic import generate_synthetic_scene


@pytest.mark.parametrize(
    "scene_type", ["flat_road", "curb", "pothole", "slope", "overhang", "urban"]
)
def test_synthetic_scenes_generate_valid_contracts(scene_type: str) -> None:
    """Ensure all synthetic scene types produce valid PointCloudFrame and SemanticPointCloud."""
    cfg = SyntheticSceneConfig(scene_type=scene_type, num_points=1000, seed=10)
    frame, semantic_cloud = generate_synthetic_scene(cfg)

    # Validate PointCloudFrame
    assert isinstance(frame, PointCloudFrame)
    assert frame.points.ndim == 2 and frame.points.shape[1] == 3
    assert frame.points.shape[0] == 1000
    assert frame.intensity is not None and frame.intensity.shape == (1000,)
    assert not np.isnan(frame.points).any()
    assert not np.isinf(frame.points).any()

    # Validate SemanticPointCloud
    assert isinstance(semantic_cloud, SemanticPointCloud)
    assert semantic_cloud.points.shape == frame.points.shape
    assert semantic_cloud.semantic_class.shape == (1000,)
    assert semantic_cloud.confidence.shape == (1000,)
    assert (semantic_cloud.confidence >= 0.0).all() and (
        semantic_cloud.confidence <= 1.0
    ).all()


def test_synthetic_generator_is_deterministic() -> None:
    """Ensure that identically seeded configurations produce identical point clouds."""
    cfg1 = SyntheticSceneConfig(scene_type="curb", num_points=500, seed=42)
    cfg2 = SyntheticSceneConfig(scene_type="curb", num_points=500, seed=42)

    frame1, sem1 = generate_synthetic_scene(cfg1)
    frame2, sem2 = generate_synthetic_scene(cfg2)

    np.testing.assert_allclose(frame1.points, frame2.points)
    np.testing.assert_array_equal(sem1.semantic_class, sem2.semantic_class)


def test_curb_scene_geometry() -> None:
    """Ensure curb scene creates elevated sidewalk points at y > half_w."""
    cfg = SyntheticSceneConfig(
        scene_type="curb",
        road_width=8.0,
        curb_height=0.20,
        noise_std=0.0,
        num_points=1000,
        seed=1,
    )
    frame, sem = generate_synthetic_scene(cfg)

    pts = frame.points
    classes = sem.semantic_class

    # Road points (y <= 4.0) should have z ~ 0 and class 0 (DRIVABLE_GROUND)
    road_mask = pts[:, 1] <= 4.0
    if np.any(road_mask):
        np.testing.assert_allclose(pts[road_mask, 2], 0.0, atol=1e-5)
        assert (classes[road_mask] == 0).all()

    # Sidewalk points (y > 4.0) should have z ~ 0.20 and class 1 (NON_DRIVABLE_TERRAIN)
    sidewalk_mask = pts[:, 1] > 4.0
    if np.any(sidewalk_mask):
        np.testing.assert_allclose(pts[sidewalk_mask, 2], 0.20, atol=1e-5)
        assert (classes[sidewalk_mask] == 1).all()
