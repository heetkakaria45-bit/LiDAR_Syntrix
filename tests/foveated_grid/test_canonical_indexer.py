"""Comprehensive verification and regression tests for Canonical Foveated Grid Indexer.

Tests:
    - P0 Task 1: Canonical interface with tuple unpacking & named attribute access
    - P0 Task 2: Strict four ring verification (0-10m, 10-25m, 25-50m, 50-100m)
    - P0 Task 2: Boundary precision (exact, just-inside, just-outside, origin, out-of-bounds)
    - P0 Task 2: All 4 Cartesian quadrants (negative X/Y)
    - P0 Task 3: Sparse grid compatibility & memory efficiency
    - P0 Task 5: Deterministic mapping assignment (assign_points protocol)
    - Module import compatibility (src.foveated_grid.grid_indexer vs foveated_indexer)
"""

import math
import numpy as np
import pytest

from src.contracts import GridCell, PointCloudFrame, SemanticPointCloud
from src.foveated_grid import (
    CellKey,
    FoveatedGridIndexer,
    FoveationLevelConfig,
    SparseFoveatedGrid,
    assign_points,
    cell_to_world,
    get_level_for_distance,
    load_foveation_config,
    resolution_for_distance,
    world_to_cell,
)
import src.foveated_grid.grid_indexer as compat_grid_indexer


@pytest.fixture
def indexer() -> FoveatedGridIndexer:
    return FoveatedGridIndexer()


# ==============================================================================
# P0 Task 1: Canonical Interface & Tuple Compatibility
# ==============================================================================

def test_cell_key_tuple_unpacking() -> None:
    """Verify CellKey behaves as a canonical NamedTuple and is fully unpackable."""
    key = CellKey(level=1, i=120, j=85)

    # Tuple unpacking
    ring_idx, cell_x, cell_y = key
    assert ring_idx == 1
    assert cell_x == 120
    assert cell_y == 85

    # Index access
    assert key[0] == 1
    assert key[1] == 120
    assert key[2] == 85

    # Named attributes
    assert key.level == 1
    assert key.i == 120
    assert key.j == 85
    assert key.ring_idx == 1
    assert key.ring == 1
    assert key.level_id == 1
    assert key.cell_x == 120
    assert key.cell_y == 85
    assert key.x == 120
    assert key.y == 85

    # Conversion to tuple
    assert key.to_tuple() == (1, 120, 85)
    assert isinstance(key, tuple)


def test_grid_indexer_compatibility_reexports() -> None:
    """Verify src.foveated_grid.grid_indexer re-exports match foveated_indexer."""
    assert compat_grid_indexer.CellKey is CellKey
    assert compat_grid_indexer.FoveatedGridIndexer is FoveatedGridIndexer
    assert compat_grid_indexer.world_to_cell is world_to_cell
    assert compat_grid_indexer.cell_to_world is cell_to_world
    assert compat_grid_indexer.assign_points is assign_points


def test_cell_to_world_flexible_signatures(indexer: FoveatedGridIndexer) -> None:
    """Verify cell_to_world handles CellKey, tuple, and 3-arg calling conventions."""
    # 1. Using CellKey
    k = indexer.world_to_cell(5.0, 2.0)
    assert k is not None
    cx1, cy1 = indexer.cell_to_world(k)

    # 2. Using standard 3-tuple (level, i, j)
    cx2, cy2 = indexer.cell_to_world((k.level, k.i, k.j))
    assert cx1 == pytest.approx(cx2)
    assert cy1 == pytest.approx(cy2)

    # 3. Using 3 arguments (ix, iy, level)
    cx3, cy3 = indexer.cell_to_world(k.i, k.j, k.level)
    assert cx1 == pytest.approx(cx3)
    assert cy1 == pytest.approx(cy3)


# ==============================================================================
# P0 Task 2: Four Rings & Boundary Verification
# ==============================================================================

def test_four_rings_nominal_resolutions(indexer: FoveatedGridIndexer) -> None:
    """Verify the four concentric rings and their defined resolutions."""
    levels = indexer.levels
    assert len(levels) == 4

    # Ring 0: 0-10m, 0.05m (5 cm)
    assert levels[0].name == "near"
    assert levels[0].level_id == 0
    assert levels[0].min_range == 0.0
    assert levels[0].max_range == 10.0
    assert levels[0].resolution == pytest.approx(0.05)

    # Ring 1: 10-25m, 0.10m (10 cm)
    assert levels[1].name == "mid_near"
    assert levels[1].level_id == 1
    assert levels[1].min_range == 10.0
    assert levels[1].max_range == 25.0
    assert levels[1].resolution == pytest.approx(0.10)

    # Ring 2: 25-50m, 0.25m (25 cm)
    assert levels[2].name == "mid"
    assert levels[2].level_id == 2
    assert levels[2].min_range == 25.0
    assert levels[2].max_range == 50.0
    assert levels[2].resolution == pytest.approx(0.25)

    # Ring 3: 50-100m, 0.50m (50 cm)
    assert levels[3].name == "far"
    assert levels[3].level_id == 3
    assert levels[3].min_range == 50.0
    assert levels[3].max_range == 100.0
    assert levels[3].resolution == pytest.approx(0.50)


def test_ring_boundaries_and_epsilon_transitions(indexer: FoveatedGridIndexer) -> None:
    """Verify strict half-open interval transitions [r_k, r_{k+1})."""
    eps = 1e-6

    # Origin (0.0m) -> Ring 0
    assert indexer.get_level_idx_for_distance(0.0) == 0
    assert indexer.resolution_for_distance(0.0) == pytest.approx(0.05)

    # Boundary 10.0m: just-inside -> Ring 0, exact & just-outside -> Ring 1
    assert indexer.get_level_idx_for_distance(10.0 - eps) == 0
    assert indexer.get_level_idx_for_distance(10.0) == 1
    assert indexer.get_level_idx_for_distance(10.0 + eps) == 1

    # Boundary 25.0m: just-inside -> Ring 1, exact & just-outside -> Ring 2
    assert indexer.get_level_idx_for_distance(25.0 - eps) == 1
    assert indexer.get_level_idx_for_distance(25.0) == 2
    assert indexer.get_level_idx_for_distance(25.0 + eps) == 2

    # Boundary 50.0m: just-inside -> Ring 2, exact & just-outside -> Ring 3
    assert indexer.get_level_idx_for_distance(50.0 - eps) == 2
    assert indexer.get_level_idx_for_distance(50.0) == 3
    assert indexer.get_level_idx_for_distance(50.0 + eps) == 3

    # Boundary 100.0m: just-inside -> Ring 3, exact 100m -> Out of bounds (None)
    assert indexer.get_level_idx_for_distance(100.0 - eps) == 3
    assert indexer.get_level_idx_for_distance(100.0) is None
    assert indexer.get_level_idx_for_distance(100.0 + eps) is None

    # Negative distances -> None
    assert indexer.get_level_idx_for_distance(-0.1) is None
    assert indexer.resolution_for_distance(-5.0) is None


def test_four_quadrants_negative_coordinates(indexer: FoveatedGridIndexer) -> None:
    """Verify symmetric mapping across all 4 Cartesian quadrants."""
    # Radius = 5.0m in all quadrants
    q1 = indexer.world_to_cell(3.0, 4.0)   # (+X, +Y)
    q2 = indexer.world_to_cell(-3.0, 4.0)  # (-X, +Y)
    q3 = indexer.world_to_cell(-3.0, -4.0) # (-X, -Y)
    q4 = indexer.world_to_cell(3.0, -4.0)  # (+X, -Y)

    for q in (q1, q2, q3, q4):
        assert q is not None
        assert q.level == 0  # Near ring

    # Roundtrip accuracy
    for x_orig, y_orig in [(3.0, 4.0), (-3.0, 4.0), (-3.0, -4.0), (3.0, -4.0)]:
        k = indexer.world_to_cell(x_orig, y_orig)
        assert k is not None
        cx, cy = indexer.cell_to_world(k)
        assert abs(cx - x_orig) <= 0.05 / 2.0 + 1e-6
        assert abs(cy - y_orig) <= 0.05 / 2.0 + 1e-6


# ==============================================================================
# P0 Task 3: Sparse Representation Verification
# ==============================================================================

def test_sparse_grid_storage_and_queries() -> None:
    """Verify SparseFoveatedGrid stores non-empty cells sparsely without dense allocation."""
    grid = SparseFoveatedGrid()

    # Insert 3 points across near, mid_near, and far rings
    grid.insert(2.0, 3.0, data={"z": 0.1})
    grid.insert(15.0, 10.0, data={"z": 0.5})
    grid.insert(-60.0, 40.0, data={"z": 1.2})

    assert grid.cell_count() == 3

    # Point query
    c1 = grid.get_cell_at(2.0, 3.0)
    assert c1 is not None
    assert c1.level_name == "near"
    assert c1.point_count == 1

    # Non-occupied query returns None without allocating memory
    c_empty = grid.get_cell_at(50.0, 50.0)
    assert c_empty is None
    assert grid.cell_count() == 3


# ==============================================================================
# P0 Task 5: Integration Check (assign_points Protocol)
# ==============================================================================

def test_assign_points_protocol(indexer: FoveatedGridIndexer) -> None:
    """Verify assign_points partitions point arrays into discrete spatial dictionary."""
    points = np.array([
        [2.0, 3.0, 0.1],     # Ring 0
        [2.02, 3.01, 0.12],  # Ring 0 (same cell)
        [15.0, 10.0, 0.5],   # Ring 1
        [30.0, 20.0, 0.8],   # Ring 2
        [60.0, 40.0, 1.5],   # Ring 3
        [150.0, 0.0, 0.0],   # Out of bounds (>100m)
    ], dtype=np.float32)

    assignments = indexer.assign_points(points)

    assert "near" in assignments
    assert "mid_near" in assignments
    assert "mid" in assignments
    assert "far" in assignments

    # Near level should have the two clustered points in one cell
    near_cells = assignments["near"]
    assert len(near_cells) == 1
    cell_key = list(near_cells.keys())[0]
    cx, cy, pt_indices = near_cells[cell_key]
    assert len(pt_indices) == 2
    assert 0 in pt_indices and 1 in pt_indices

    # Out-of-bounds point (index 5) is rejected
    all_assigned = np.concatenate([
        pt_idx for level_dict in assignments.values() for _, _, pt_idx in level_dict.values()
    ])
    assert 5 not in all_assigned
    assert len(all_assigned) == 5
