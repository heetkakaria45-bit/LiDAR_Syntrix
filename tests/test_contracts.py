"""Test contract schema validation and data integrity invariants."""

import numpy as np
import pytest

from src.contracts import (
    DatasetLabelMap,
    GridCell,
    PointCloudFrame,
    SemanticMap,
    SemanticPointCloud,
    SyntheticSceneConfig,
)


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
    assert cell.observation_count == 1
    assert cell.velocity is None
    assert cell.uncertainty == 0.0


def test_grid_cell_extended_attributes() -> None:
    """Ensure GridCell supports velocity, uncertainty, and semantic probability vectors."""
    probs = np.array([0.8, 0.1, 0.05, 0.02, 0.01, 0.01, 0.005, 0.005], dtype=np.float32)
    cell = GridCell(
        resolution_level="level_1",
        cell_x=12.0,
        cell_y=4.0,
        elevation=0.5,
        min_z=0.1,
        max_z=1.8,
        semantic_class=2,
        confidence=0.80,
        occupancy=1.0,
        point_count=120,
        roughness=0.02,
        timestamp=105.0,
        velocity=(12.5, 0.0, 0.0),
        observation_count=5,
        uncertainty=0.15,
        semantic_probabilities=probs,
    )

    assert cell.velocity == (12.5, 0.0, 0.0)
    assert cell.observation_count == 5
    assert cell.uncertainty == 0.15
    assert cell.semantic_probabilities.shape == (8,)


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


def test_dataset_label_map() -> None:
    """Ensure DatasetLabelMap correctly translates external class IDs into project IDs."""
    mapping_dict = {
        9: 0,  # road -> DRIVABLE_GROUND
        1: 2,  # car -> VEHICLE
        6: 3,  # person -> PEDESTRIAN
    }
    mapper = DatasetLabelMap(mapping_dict=mapping_dict, default_unmapped_class=7)

    raw_labels = np.array([9, 9, 1, 6, 99], dtype=np.int32)
    project_labels = mapper.map_labels(raw_labels)

    expected = np.array([0, 0, 2, 3, 7], dtype=np.int32)
    np.testing.assert_array_equal(project_labels, expected)


def test_synthetic_scene_config() -> None:
    """Ensure SyntheticSceneConfig initializes with sensible defaults."""
    cfg = SyntheticSceneConfig(scene_type="curb", curb_height=0.18, seed=123)
    assert cfg.scene_type == "curb"
    assert cfg.curb_height == 0.18
    assert cfg.seed == 123
