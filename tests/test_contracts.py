"""Test contract schema validation and data integrity invariants."""

import numpy as np
import pytest

from src.contracts import GridCell, PointCloudFrame, SemanticMap, SemanticPointCloud


def test_point_cloud_frame_valid() -> None:
    """Ensure PointCloudFrame accepts valid (N, 3) points and optional intensity."""
    points = np.array([[1.0, 2.0, 0.5], [3.0, 4.0, -0.2]], dtype=np.float32)
    intensity = np.array([0.8, 0.4], dtype=np.float32)

    frame = PointCloudFrame(
        points=points,
        intensity=intensity,
        timestamp=1700000000.0,
        frame_id="lidar_top",
    )

    assert frame.points.shape == (2, 3)
    assert frame.intensity.shape == (2,)
    assert frame.timestamp == 1700000000.0
    assert frame.frame_id == "lidar_top"
    assert frame.sensor_pose.shape == (4, 4)


def test_point_cloud_frame_invalid_shape() -> None:
    """Ensure PointCloudFrame rejects malformed points or mismatched intensity."""
    bad_points = np.array([1.0, 2.0, 3.0], dtype=np.float32)  # 1D instead of (N, 3)
    with pytest.raises(ValueError, match=r"points array must have shape \(N, 3\)"):
        PointCloudFrame(points=bad_points, timestamp=0.0, frame_id="lidar")

    points = np.zeros((5, 3), dtype=np.float32)
    mismatched_intensity = np.zeros((3,), dtype=np.float32)
    with pytest.raises(ValueError, match=r"intensity array must have shape \(N,\)"):
        PointCloudFrame(
            points=points,
            intensity=mismatched_intensity,
            timestamp=0.0,
            frame_id="lidar",
        )


def test_semantic_point_cloud_valid() -> None:
    """Ensure SemanticPointCloud verifies matching lengths across arrays."""
    n = 100
    points = np.zeros((n, 3), dtype=np.float32)
    semantic_class = np.zeros((n,), dtype=np.int32)
    confidence = np.ones((n,), dtype=np.float32)

    cloud = SemanticPointCloud(
        points=points,
        semantic_class=semantic_class,
        confidence=confidence,
        timestamp=1.0,
        frame_id="base_link",
    )

    assert cloud.points.shape == (n, 3)
    assert cloud.semantic_class.shape == (n,)
    assert cloud.confidence.shape == (n,)


def test_semantic_point_cloud_mismatched_length() -> None:
    """Ensure SemanticPointCloud rejects mismatched class or confidence dimensions."""
    points = np.zeros((10, 3), dtype=np.float32)
    semantic_class = np.zeros((8,), dtype=np.int32)  # length 8 != 10
    confidence = np.zeros((10,), dtype=np.float32)

    with pytest.raises(ValueError, match=r"semantic_class shape"):
        SemanticPointCloud(
            points=points,
            semantic_class=semantic_class,
            confidence=confidence,
            timestamp=0.0,
            frame_id="lidar",
        )


def test_grid_cell_creation() -> None:
    """Ensure GridCell holds all standard 2.5D geometric and semantic attributes."""
    cell = GridCell(
        resolution_level="near",
        cell_x=2.5,
        cell_y=-1.0,
        elevation=0.12,
        min_z=0.05,
        max_z=0.20,
        semantic_class=0,
        confidence=0.95,
        occupancy=0.99,
        point_count=42,
        roughness=0.015,
        timestamp=100.5,
    )

    assert cell.resolution_level == "near"
    assert cell.cell_x == 2.5
    assert cell.elevation == 0.12
    assert cell.semantic_class == 0
    assert cell.occupancy == 0.99
    assert cell.point_count == 42


def test_semantic_map_creation() -> None:
    """Ensure SemanticMap container can be instantiated with metadata and pose."""
    pose = np.eye(4, dtype=np.float64)
    sem_map = SemanticMap(
        cells={},
        resolution_levels={"near": 0.05, "mid": 0.25},
        sensor_pose=pose,
        timestamp=200.0,
        metadata={"num_cells": 0},
    )

    assert isinstance(sem_map.cells, dict)
    assert sem_map.sensor_pose.shape == (4, 4)
    assert sem_map.timestamp == 200.0
