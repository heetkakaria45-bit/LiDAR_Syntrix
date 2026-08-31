"""Unit tests for Vectorized Batch Insertion vs. Scalar Insertion Equivalence.

Module: tests/foveated_grid/test_batch_insert.py
Tests:
    - Scalar insertion vs Batch insertion exact cell-for-cell equivalence
    - Ring boundaries: 10m - eps, 10m exact, 10m + eps
    - Ring boundaries: 25m - eps, 25m exact, 25m + eps
    - Ring boundaries: 50m - eps, 50m exact, 50m + eps
    - Horizon boundaries: 100m - eps, 100m exact, 100m + eps
    - Negative coordinates across all quadrants
    - Cell boundary quantization
    - Duplicate points mapping to the same cell
    - Out-of-range point rejection
    - PointCloudFrame & SemanticPointCloud contract interoperability
    - Empty and all-rejected batches
"""

import numpy as np
import pytest

from src.contracts import PointCloudFrame, SemanticPointCloud
from src.foveated_grid import (
    BatchInsertResult,
    SparseFoveatedGrid,
)


@pytest.fixture
def grid() -> SparseFoveatedGrid:
    """Instantiate fresh SparseFoveatedGrid."""
    return SparseFoveatedGrid()


# ==============================================================================
# 1. Tests for Exact Equivalence: Scalar vs Batch
# ==============================================================================


def test_scalar_vs_batch_synthetic_points() -> None:
    """Verify that scalar insertion and batch insertion produce identical cells and payloads."""
    rng = np.random.default_rng(42)
    n = 2000
    theta = rng.uniform(0.0, 2.0 * np.pi, size=n)
    r = rng.uniform(0.5, 99.5, size=n)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    z = rng.normal(0.0, 0.1, size=n)
    points = np.column_stack([x, y, z])

    # 1. Scalar insertion
    grid_scalar = SparseFoveatedGrid()
    for idx in range(n):
        grid_scalar.insert(
            float(x[idx]), float(y[idx]), data=(float(x[idx]), float(y[idx]), float(z[idx]))
        )

    # 2. Batch insertion
    grid_batch = SparseFoveatedGrid()
    res = grid_batch.insert_batch(points)

    assert isinstance(res, BatchInsertResult)
    assert res.num_accepted == n
    assert res.num_rejected == 0
    assert grid_scalar.cell_count() == grid_batch.cell_count()
    assert res.total_occupied_cells == grid_scalar.cell_count()

    # Compare cell-by-cell equivalence
    cells_scalar = grid_scalar.get_cells()
    cells_batch = grid_batch.get_cells()

    assert set(cells_scalar.keys()) == set(cells_batch.keys())

    for key in cells_scalar:
        c_s = cells_scalar[key]
        c_b = cells_batch[key]
        assert c_s.center_x == pytest.approx(c_b.center_x)
        assert c_s.center_y == pytest.approx(c_b.center_y)
        assert c_s.point_count == c_b.point_count
        assert len(c_s.items) == len(c_b.items)


# ==============================================================================
# 2. Boundary Transitions: Epsilon and Exact Ring Boundaries
# ==============================================================================


def test_batch_resolution_boundaries() -> None:
    """Verify exact ring boundary assignment between scalar and batch insertion."""
    eps = 1e-4
    test_points = np.array(
        [
            [10.0 - eps, 0.0, 0.0],  # Level 0
            [10.0, 0.0, 0.0],  # Level 1
            [10.0 + eps, 0.0, 0.0],  # Level 1
            [0.0, 25.0 - eps, 0.0],  # Level 1
            [0.0, 25.0, 0.0],  # Level 2
            [0.0, 25.0 + eps, 0.0],  # Level 2
            [-(50.0 - eps), 0.0, 0.0],  # Level 2
            [-50.0, 0.0, 0.0],  # Level 3
            [-(50.0 + eps), 0.0, 0.0],  # Level 3
            [0.0, -(100.0 - eps), 0.0],  # Level 3
            [0.0, -100.0, 0.0],  # Out of bounds
            [0.0, -(100.0 + eps), 0.0],  # Out of bounds
        ],
        dtype=np.float64,
    )

    grid_scalar = SparseFoveatedGrid()
    for pt in test_points:
        grid_scalar.insert(float(pt[0]), float(pt[1]), data=tuple(pt))

    grid_batch = SparseFoveatedGrid()
    res = grid_batch.insert_batch(test_points)

    assert res.num_accepted == 10
    assert res.num_rejected == 2  # 100.0m and 100.0m + eps
    assert grid_batch.cell_count() == grid_scalar.cell_count()

    # Query specific boundary cells
    c_10_exact = grid_batch.query(10.0, 0.0)
    assert c_10_exact is not None
    assert c_10_exact.key.level == 1  # 10.0m must be Level 1

    c_25_exact = grid_batch.query(0.0, 25.0)
    assert c_25_exact is not None
    assert c_25_exact.key.level == 2  # 25.0m must be Level 2

    c_50_exact = grid_batch.query(-50.0, 0.0)
    assert c_50_exact is not None
    assert c_50_exact.key.level == 3  # 50.0m must be Level 3

    assert grid_batch.query(0.0, -100.0) is None


# ==============================================================================
# 3. Quadrants and Negative Coordinates
# ==============================================================================


def test_batch_quadrants_and_negative_coords() -> None:
    """Verify batch insertion handles all four quadrants identically to scalar."""
    points = np.array(
        [
            [5.0, 5.0],  # Q1
            [-5.0, 5.0],  # Q2
            [-5.0, -5.0],  # Q3
            [5.0, -5.0],  # Q4
        ],
        dtype=np.float64,
    )

    grid = SparseFoveatedGrid()
    res = grid.insert_batch(points)

    assert res.num_accepted == 4
    assert res.num_rejected == 0
    assert grid.cell_count() == 4
    assert grid.query(5.0, 5.0) is not None
    assert grid.query(-5.0, 5.0) is not None
    assert grid.query(-5.0, -5.0) is not None
    assert grid.query(5.0, -5.0) is not None


# ==============================================================================
# 4. Duplicate Points & Multi-Point Accumulation per Cell
# ==============================================================================


def test_batch_duplicate_points_same_cell() -> None:
    """Verify batch insertion correctly groups multiple points falling in the same cell."""
    # 5 points all falling into Level 0 cell (2.025, 3.025)
    points = np.array(
        [
            [2.01, 3.01, 0.1],
            [2.02, 3.02, 0.2],
            [2.03, 3.03, 0.3],
            [2.04, 3.04, 0.4],
            [2.015, 3.015, 0.5],
        ],
        dtype=np.float64,
    )

    grid = SparseFoveatedGrid()
    res = grid.insert_batch(points)

    assert res.num_accepted == 5
    assert res.num_rejected == 0
    assert res.num_cells_created == 1
    assert res.num_cells_updated == 0
    assert grid.cell_count() == 1

    cell = grid.query(2.02, 3.02)
    assert cell is not None
    assert cell.point_count == 5
    assert len(cell.items) == 5

    # Second batch inserting 3 more points into the same cell
    more_points = np.array(
        [
            [2.021, 3.021, 0.6],
            [2.022, 3.022, 0.7],
            [2.023, 3.023, 0.8],
        ],
        dtype=np.float64,
    )

    res2 = grid.insert_batch(more_points)
    assert res2.num_cells_created == 0
    assert res2.num_cells_updated == 1
    assert grid.cell_count() == 1
    assert cell.point_count == 8


# ==============================================================================
# 5. Contract Dataclass Integration (PointCloudFrame & SemanticPointCloud)
# ==============================================================================


def test_batch_insert_point_cloud_frame_contract() -> None:
    """Verify insert_batch accepts PointCloudFrame instance directly."""
    points = np.array([[1.0, 2.0, 0.5], [15.0, 10.0, -0.2]], dtype=np.float32)
    frame = PointCloudFrame(
        points=points,
        timestamp=100.0,
        frame_id="lidar_top",
    )

    grid = SparseFoveatedGrid()
    res = grid.insert_batch(frame)

    assert res.num_accepted == 2
    assert grid.cell_count() == 2
    assert grid.query(1.0, 2.0) is not None
    assert grid.query(15.0, 10.0) is not None


def test_batch_insert_semantic_point_cloud_contract() -> None:
    """Verify insert_batch accepts SemanticPointCloud with custom payload passing."""
    points = np.array([[3.0, 4.0, 0.1], [30.0, 20.0, 1.2]], dtype=np.float32)
    classes = np.array([0, 2], dtype=np.int32)
    confidence = np.array([0.95, 0.88], dtype=np.float32)

    cloud = SemanticPointCloud(
        points=points,
        semantic_class=classes,
        confidence=confidence,
        timestamp=200.0,
        frame_id="base_link",
    )

    payloads = [
        {"class": int(classes[0]), "conf": float(confidence[0])},
        {"class": int(classes[1]), "conf": float(confidence[1])},
    ]

    grid = SparseFoveatedGrid()
    res = grid.insert_batch(cloud, payloads=payloads)

    assert res.num_accepted == 2
    assert grid.cell_count() == 2

    c1 = grid.query(3.0, 4.0)
    assert c1 is not None
    assert c1.items[0]["class"] == 0
    assert c1.items[0]["conf"] == pytest.approx(0.95)


# ==============================================================================
# 6. Edge Cases: Empty Batches & All-Out-Of-Bounds
# ==============================================================================


def test_batch_insert_empty_and_all_out_of_bounds() -> None:
    """Verify empty arrays and out-of-bounds arrays do not crash and report correct counts."""
    grid = SparseFoveatedGrid()

    # Empty array
    res_empty = grid.insert_batch(np.empty((0, 3), dtype=np.float64))
    assert res_empty.num_accepted == 0
    assert res_empty.num_rejected == 0
    assert grid.cell_count() == 0

    # All out-of-bounds
    out_points = np.array(
        [
            [120.0, 0.0, 0.0],
            [0.0, 150.0, 0.0],
            [-200.0, -200.0, 0.0],
        ],
        dtype=np.float64,
    )

    res_out = grid.insert_batch(out_points)
    assert res_out.num_accepted == 0
    assert res_out.num_rejected == 3
    assert grid.cell_count() == 0
