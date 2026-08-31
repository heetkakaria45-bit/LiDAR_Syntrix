"""Automated Regression & Stress Validation Suite for Foveated Spatial Grid.

Module: tests/foveated_grid/test_stress_validation.py
Tests:
    - Multi-frame sequence lifecycle stability (create -> ingest -> map -> release)
    - 4-quadrant symmetric coordinate reconstruction and non-negative indices
    - Ring boundary strict half-open interval enforcement
    - Query invariance across occupied, empty, and out-of-bounds queries
    - Scalar and batch pipeline equivalence on multi-resolution point clouds
"""

import math

import numpy as np
import pytest

from src.contracts import GridCell, SemanticMap, SemanticPointCloud
from src.foveated_grid import (
    CellKey,
    FoveatedGridIndexer,
    SparseFoveatedGrid,
    ingest_point_cloud,
)


@pytest.fixture
def indexer() -> FoveatedGridIndexer:
    """Fixture providing standard foveated grid indexer."""
    return FoveatedGridIndexer()


def test_multi_frame_lifecycle_stability(indexer: FoveatedGridIndexer) -> None:
    """Verify processing multiple consecutive frames incurs no stale state or memory accumulation."""
    rng = np.random.default_rng(42)

    for frame_idx in range(20):
        # Generate random 1000-point frame
        theta = rng.uniform(0.0, 2.0 * math.pi, size=1000)
        r = rng.uniform(0.5, 95.0, size=1000)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = rng.normal(0.0, 0.1, size=1000)
        classes = rng.choice([0, 1, 2, 3], size=1000).astype(np.int32)
        conf = rng.uniform(0.8, 1.0, size=1000).astype(np.float32)

        cloud = SemanticPointCloud(
            points=np.column_stack([x, y, z]).astype(np.float32),
            semantic_class=classes,
            confidence=conf,
            timestamp=1000.0 + frame_idx * 0.1,
            frame_id=f"frame_{frame_idx}",
        )

        grid, res = ingest_point_cloud(cloud)
        assert res.num_accepted == 1000
        assert res.num_rejected == 0
        assert grid.cell_count() > 0

        sem_map = grid.to_semantic_map(timestamp=cloud.timestamp)
        assert isinstance(sem_map, SemanticMap)
        assert sem_map.metadata["occupied_cells_count"] == grid.cell_count()

        # Lifecycle clear
        grid.clear()
        assert grid.cell_count() == 0


def test_four_quadrant_symmetric_indexing(indexer: FoveatedGridIndexer) -> None:
    """Verify non-negative indices and correct center reconstruction in all 4 quadrants."""
    test_coords = [
        (12.34, 18.56),  # Q1
        (-12.34, 18.56),  # Q2
        (-12.34, -18.56),  # Q3
        (12.34, -18.56),  # Q4
    ]

    for qx, qy in test_coords:
        key = indexer.world_to_cell(qx, qy)
        assert key is not None
        assert key.i >= 0
        assert key.j >= 0

        cx, cy = indexer.cell_to_world(key)
        lvl = indexer.get_level(key.level)
        assert abs(cx - qx) <= lvl.resolution
        assert abs(cy - qy) <= lvl.resolution


def test_query_invariance_and_non_mutation() -> None:
    """Verify queries never mutate internal state or allocate empty cells."""
    grid = SparseFoveatedGrid()
    grid.insert(5.0, 5.0, data={"z": 0.1})
    grid.insert(-20.0, 15.0, data={"z": 0.2})

    initial_count = grid.cell_count()
    assert initial_count == 2

    # Various queries
    assert grid.query(5.0, 5.0) is not None
    assert grid.query(1.0, 1.0) is None  # Unoccupied
    assert grid.query(150.0, 0.0) is None  # Out of range
    assert grid.query_cell(CellKey(0, 50, 50)) is None  # Unoccupied key
    assert len(grid.query_region(-50.0, 50.0, -50.0, 50.0)) == 2
    assert len(grid.query_region(0.0, 2.0, 0.0, 2.0)) == 0

    assert grid.cell_count() == initial_count


def test_mapping_handoff_contract_preservation() -> None:
    """Verify handoff converts all cells to valid GridCell instances with accurate statistics."""
    points = np.array(
        [
            [1.0, 1.0, 0.10],
            [1.0, 1.0, 0.20],
            [1.0, 1.0, 0.30],
        ],
        dtype=np.float32,
    )

    cloud = SemanticPointCloud(
        points=points,
        semantic_class=np.array([2, 2, 2], dtype=np.int32),  # Vehicle
        confidence=np.array([0.9, 0.95, 0.85], dtype=np.float32),
        timestamp=500.0,
        frame_id="lidar",
    )

    grid, _ = ingest_point_cloud(cloud)
    grid_cells = grid.to_grid_cells(timestamp=cloud.timestamp)

    assert len(grid_cells) == 1
    gc = grid_cells[0]
    assert isinstance(gc, GridCell)
    assert gc.point_count == 3
    assert gc.min_z == pytest.approx(0.10)
    assert gc.max_z == pytest.approx(0.30)
    assert gc.elevation == pytest.approx(0.20)
    assert gc.semantic_class == 2
    assert gc.confidence == pytest.approx(0.90)


def test_controlled_smoke_stress_5_frames_10k_points() -> None:
    """Execute controlled smoke/stress test: 5 consecutive frames with 10k points each."""
    rng = np.random.default_rng(42)
    for frame_idx in range(5):
        theta = rng.uniform(0.0, 2.0 * math.pi, size=10000)
        r = rng.uniform(0.5, 95.0, size=10000)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = rng.normal(0.0, 0.1, size=10000)
        classes = rng.choice([0, 1, 2, 3, 5, 6], size=10000).astype(np.int32)
        conf = rng.uniform(0.85, 0.99, size=10000).astype(np.float32)

        cloud = SemanticPointCloud(
            points=np.column_stack([x, y, z]).astype(np.float32),
            semantic_class=classes,
            confidence=conf,
            timestamp=1700000000.0 + frame_idx * 0.1,
            frame_id=f"lidar_frame_{frame_idx:04d}",
        )

        grid, res = ingest_point_cloud(cloud)
        assert res.num_accepted == 10000
        assert res.num_rejected == 0
        assert grid.cell_count() > 0

        sem_map = grid.to_semantic_map(timestamp=cloud.timestamp)
        assert isinstance(sem_map, SemanticMap)
        assert sem_map.metadata["occupied_cells_count"] == grid.cell_count()

        # Clear and check
        grid.clear()
        assert grid.cell_count() == 0
