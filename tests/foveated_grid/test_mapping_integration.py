"""Integration tests for Foveated Spatial Grid handoff to 2.5D Semantic Mapping Pipeline.

Module: tests/foveated_grid/test_mapping_integration.py
Tests:
    - PointCloudFrame -> SparseFoveatedGrid -> GridCell conversion
    - SemanticPointCloud -> SparseFoveatedGrid -> SemanticMap conversion
    - Occupied-cell iteration fidelity and non-mutation
    - Multi-resolution level preservation across bands
    - End-to-end synthetic geometric scene mapping handoff
"""

import numpy as np
import pytest

from src.contracts import (
    GridCell,
    PointCloudFrame,
    SemanticMap,
    SemanticPointCloud,
    SyntheticSceneConfig,
)
from src.foveated_grid import (
    BatchInsertResult,
    SparseCell,
    SparseFoveatedGrid,
    ingest_point_cloud,
)
from src.preprocessing.synthetic import generate_synthetic_scene


def test_point_cloud_frame_to_grid_cells_handoff() -> None:
    """Verify PointCloudFrame ingestion and conversion to standardized GridCell contracts."""
    # Synthetic frame with points at varying elevations
    points = np.array(
        [
            [2.01, 3.01, 0.10],
            [2.02, 3.02, 0.15],
            [2.03, 3.03, 0.20],
            [15.0, 10.0, 0.50],  # Level 1
        ],
        dtype=np.float32,
    )

    frame = PointCloudFrame(
        points=points,
        timestamp=1700000000.0,
        frame_id="lidar_top",
    )

    grid, res = ingest_point_cloud(frame)
    assert isinstance(res, BatchInsertResult)
    assert res.num_accepted == 4
    assert grid.cell_count() == 2

    # Convert to GridCell contracts
    grid_cells = grid.to_grid_cells(timestamp=frame.timestamp)
    assert len(grid_cells) == 2
    for gc in grid_cells:
        assert isinstance(gc, GridCell)
        assert gc.timestamp == 1700000000.0
        assert gc.occupancy == 1.0

    # Near cell (2.0, 3.0) accumulated 3 points
    near_gc = [gc for gc in grid_cells if gc.resolution_level == "near"][0]
    assert near_gc.point_count == 3
    assert near_gc.min_z == pytest.approx(0.10)
    assert near_gc.max_z == pytest.approx(0.20)
    assert near_gc.elevation == pytest.approx(0.15)  # Median of 0.10, 0.15, 0.20
    assert near_gc.roughness > 0.0


def test_semantic_point_cloud_to_semantic_map_handoff() -> None:
    """Verify SemanticPointCloud ingestion and conversion to standardized SemanticMap."""
    points = np.array(
        [
            [3.0, 4.0, 0.05],  # Level 0, Class 0 (Road)
            [3.02, 4.02, 0.08],  # Level 0, Class 0 (Road)
            [15.0, 5.0, 0.80],  # Level 1, Class 3 (Pedestrian)
            [35.0, 0.0, 1.50],  # Level 2, Class 2 (Vehicle)
            [75.0, 0.0, 5.00],  # Level 3, Class 6 (Building)
        ],
        dtype=np.float32,
    )

    classes = np.array([0, 0, 3, 2, 6], dtype=np.int32)
    confidences = np.array([0.98, 0.95, 0.85, 0.90, 0.92], dtype=np.float32)

    cloud = SemanticPointCloud(
        points=points,
        semantic_class=classes,
        confidence=confidences,
        timestamp=100.5,
        frame_id="base_link",
    )

    payloads = [
        {"class": int(classes[i]), "conf": float(confidences[i]), "z": float(points[i, 2])}
        for i in range(len(points))
    ]

    grid = SparseFoveatedGrid()
    grid.insert_batch(cloud, payloads=payloads)

    pose = np.eye(4, dtype=np.float64)
    sem_map = grid.to_semantic_map(sensor_pose=pose, timestamp=cloud.timestamp)

    assert isinstance(sem_map, SemanticMap)
    assert sem_map.timestamp == 100.5
    assert sem_map.sensor_pose.shape == (4, 4)
    assert sem_map.metadata["occupied_cells_count"] == 4

    # Verify resolution ring stratification
    cells = sem_map.cells
    assert "near" in cells and len(cells["near"]) == 1
    assert "mid_near" in cells and len(cells["mid_near"]) == 1
    assert "mid" in cells and len(cells["mid"]) == 1
    assert "far" in cells and len(cells["far"]) == 1

    # Check near road cell attributes
    road_cell = cells["near"][0]
    assert road_cell.semantic_class == 0
    assert road_cell.point_count == 2
    assert road_cell.confidence == pytest.approx(0.965)  # mean of 0.98, 0.95

    # Check mid_near pedestrian cell
    ped_cell = cells["mid_near"][0]
    assert ped_cell.semantic_class == 3
    assert ped_cell.elevation == pytest.approx(0.80)


def test_iter_occupied_cells_non_mutating() -> None:
    """Verify iter_occupied_cells iterates cleanly without side-effects or allocating empty space."""
    grid = SparseFoveatedGrid()
    grid.insert(5.0, 5.0, data={"z": 0.0})
    grid.insert(-15.0, 10.0, data={"z": 0.5})

    count_iter = 0
    for cell in grid.iter_occupied_cells():
        assert isinstance(cell, SparseCell)
        count_iter += 1

    assert count_iter == 2
    assert grid.cell_count() == 2


def test_synthetic_scenes_mapping_integration() -> None:
    """Verify deterministic geometric synthetic curb and pothole scenes map seamlessly."""
    # 1. Curb Scene
    curb_cfg = SyntheticSceneConfig(scene_type="curb", num_points=1000, curb_height=0.15, seed=42)
    curb_frame, _ = generate_synthetic_scene(curb_cfg)
    grid_curb, res_curb = ingest_point_cloud(curb_frame)

    assert res_curb.num_accepted > 0
    assert grid_curb.cell_count() > 0

    sem_map_curb = grid_curb.to_semantic_map(timestamp=curb_frame.timestamp)
    assert len(sem_map_curb.cells["near"]) > 0

    # 2. Pothole Scene
    pothole_cfg = SyntheticSceneConfig(
        scene_type="pothole", num_points=1000, pothole_depth=0.08, seed=42
    )
    pothole_frame, _ = generate_synthetic_scene(pothole_cfg)
    grid_pothole, res_pothole = ingest_point_cloud(pothole_frame)

    assert res_pothole.num_accepted > 0
    assert grid_pothole.cell_count() > 0

    sem_map_pothole = grid_pothole.to_semantic_map(timestamp=pothole_frame.timestamp)
    assert len(sem_map_pothole.cells["near"]) > 0
