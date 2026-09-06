"""Unit tests for Perception module."""

import numpy as np
from src.contracts import PointCloudFrame
from src.perception import BaseSemanticSegmenter, MockSemanticSegmenter


def test_mock_semantic_segmenter() -> None:
    """Ensure MockSemanticSegmenter produces valid SemanticPointCloud instances."""
    points = np.array([
        [2.0, 1.0, 0.0],   # Ground point
        [5.0, -2.0, 1.2],  # Low obstacle
        [15.0, 0.0, 4.0],  # Tall building
    ], dtype=np.float32)

    frame = PointCloudFrame(points=points, timestamp=100.0, frame_id="lidar")
    segmenter = MockSemanticSegmenter(default_confidence=0.9)
    sem_cloud = segmenter.infer(frame)

    assert sem_cloud.points.shape == (3, 3)
    assert sem_cloud.semantic_class.shape == (3,)
    assert sem_cloud.confidence.shape == (3,)
    assert sem_cloud.semantic_class[0] == 0  # DRIVABLE_GROUND
    assert sem_cloud.semantic_class[1] == 2  # VEHICLE / Obstacle
    assert sem_cloud.semantic_class[2] == 6  # WALL_BUILDING
    assert np.all(sem_cloud.confidence == 0.9)


def test_mock_semantic_segmenter_empty_frame() -> None:
    """Ensure segmenter handles empty frames without crashing."""
    points = np.zeros((0, 3), dtype=np.float32)
    frame = PointCloudFrame(points=points, timestamp=100.0, frame_id="lidar")
    segmenter = MockSemanticSegmenter()
    sem_cloud = segmenter.infer(frame)

    assert sem_cloud.points.shape == (0, 3)
    assert sem_cloud.semantic_class.shape == (0,)
    assert sem_cloud.confidence.shape == (0,)
