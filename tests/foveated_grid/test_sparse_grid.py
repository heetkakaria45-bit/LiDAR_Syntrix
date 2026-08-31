"""Unit tests for Concentric Multi-Ring Sparse Hash Grid Storage and Query Engine.

Module: tests/foveated_grid/test_sparse_grid.py
Tests:
    - Sparse allocation and zero pre-allocation verification
    - Point insertion and query fidelity
    - Duplicate/multi-point accumulation per cell
    - Negative coordinate handling across all quadrants
    - Half-open ring boundary insertion [0, 10), [10, 25), [25, 50), [50, 100)
    - Cell boundary quantization
    - Sparse region queries (empty, single, multi-cell, cross-band)
    - Accurate cell counting and non-mutating queries
    - Object-level memory estimation and breakdown
"""

import pytest

from src.foveated_grid import (
    CellKey,
    SparseCell,
    SparseFoveatedGrid,
)


@pytest.fixture
def grid() -> SparseFoveatedGrid:
    """Instantiate a fresh SparseFoveatedGrid instance."""
    return SparseFoveatedGrid()


# ==============================================================================
# 1. Tests for Sparse Allocation & Invariants
# ==============================================================================


def test_sparse_initialization_zero_allocation(grid: SparseFoveatedGrid) -> None:
    """Verify newly initialized grid contains zero cells and no pre-allocation."""
    assert grid.cell_count() == 0
    assert len(grid.get_cells()) == 0
    assert grid.memory_usage() > 0  # Bare empty dictionary overhead


def test_query_empty_does_not_allocate(grid: SparseFoveatedGrid) -> None:
    """Verify querying unoccupied coordinates returns None without creating cells."""
    assert grid.query(2.5, 3.5) is None
    assert grid.query(-15.0, 8.0) is None
    assert grid.query(45.0, -20.0) is None
    assert grid.cell_count() == 0  # Must remain zero


def test_query_out_of_range(grid: SparseFoveatedGrid) -> None:
    """Verify querying out-of-range coordinates returns None without side effects."""
    assert grid.query(105.0, 0.0) is None
    assert grid.query(0.0, -150.0) is None
    assert grid.cell_count() == 0


# ==============================================================================
# 2. Tests for Point Insertion & Query Operations
# ==============================================================================


def test_insert_single_point(grid: SparseFoveatedGrid) -> None:
    """Verify inserting a single point stores and retrieves it correctly."""
    key = grid.insert(3.0, 4.0, data={"z": 0.15, "intensity": 0.8})
    assert key is not None
    assert key.level == 0
    assert grid.cell_count() == 1

    cell = grid.query(3.0, 4.0)
    assert cell is not None
    assert isinstance(cell, SparseCell)
    assert cell.key == key
    assert cell.point_count == 1
    assert cell.items[0]["z"] == 0.15
    assert cell.level_name == "near"


def test_insert_out_of_range_rejected(grid: SparseFoveatedGrid) -> None:
    """Verify points >= 100m are rejected and return None without allocating storage."""
    assert grid.insert(100.0, 0.0, data="out") is None
    assert grid.insert(0.0, -100.0, data="out") is None
    assert grid.insert(80.0, 80.0, data="out") is None  # r = sqrt(6400 + 6400) = 113.1m > 100m
    assert grid.cell_count() == 0


def test_insert_multiple_points_same_cell(grid: SparseFoveatedGrid) -> None:
    """Verify multiple points falling in the same cell accumulate in the items list."""
    # In Level 0 (delta=0.05), cell around center (2.025, 3.025)
    p1 = (2.01, 3.01, 0.1)
    p2 = (2.02, 3.02, 0.2)
    p3 = (2.04, 3.04, 0.3)

    k1 = grid.insert(2.01, 3.01, data=p1)
    k2 = grid.insert(2.02, 3.02, data=p2)
    k3 = grid.insert(2.04, 3.04, data=p3)

    assert k1 == k2 == k3
    assert grid.cell_count() == 1  # Only 1 unique spatial cell occupied

    cell = grid.query(2.02, 3.02)
    assert cell is not None
    assert cell.point_count == 3
    assert cell.items == [p1, p2, p3]


def test_insert_distinct_cells(grid: SparseFoveatedGrid) -> None:
    """Verify inserting points into distinct cells increases cell_count accordingly."""
    grid.insert(1.0, 1.0, data="pt1")
    grid.insert(2.0, 2.0, data="pt2")
    grid.insert(12.0, 0.0, data="pt3")  # Level 1

    assert grid.cell_count() == 3
    assert grid.query(1.0, 1.0).items == ["pt1"]
    assert grid.query(2.0, 2.0).items == ["pt2"]
    assert grid.query(12.0, 0.0).items == ["pt3"]


# ==============================================================================
# 3. Tests for Negative Coordinates & All Four Quadrants
# ==============================================================================


def test_negative_coordinates_all_quadrants(grid: SparseFoveatedGrid) -> None:
    """Verify insertion and lookup across all four Cartesian quadrants."""
    # Quadrant 1 (+x, +y)
    k_q1 = grid.insert(5.0, 5.0, data="Q1")
    # Quadrant 2 (-x, +y)
    k_q2 = grid.insert(-5.0, 5.0, data="Q2")
    # Quadrant 3 (-x, -y)
    k_q3 = grid.insert(-5.0, -5.0, data="Q3")
    # Quadrant 4 (+x, -y)
    k_q4 = grid.insert(5.0, -5.0, data="Q4")

    assert len({k_q1, k_q2, k_q3, k_q4}) == 4  # All 4 keys must be distinct
    assert grid.cell_count() == 4

    assert grid.query(5.0, 5.0).items == ["Q1"]
    assert grid.query(-5.0, 5.0).items == ["Q2"]
    assert grid.query(-5.0, -5.0).items == ["Q3"]
    assert grid.query(5.0, -5.0).items == ["Q4"]


# ==============================================================================
# 4. Tests for Resolution Boundaries [0, 10), [10, 25), [25, 50), [50, 100)
# ==============================================================================


def test_resolution_boundaries_strict_ownership(grid: SparseFoveatedGrid) -> None:
    """Verify points right below, exactly on, and right above ring transitions."""
    eps = 1e-4

    # 10m Boundary
    k_below_10 = grid.insert(10.0 - eps, 0.0, data="below_10")
    k_exact_10 = grid.insert(10.0, 0.0, data="exact_10")
    k_above_10 = grid.insert(10.0 + eps, 0.0, data="above_10")

    assert k_below_10.level == 0
    assert k_exact_10.level == 1  # 10.0m belongs to Level 1
    assert k_above_10.level == 1

    # 25m Boundary
    k_below_25 = grid.insert(0.0, 25.0 - eps, data="below_25")
    k_exact_25 = grid.insert(0.0, 25.0, data="exact_25")
    k_above_25 = grid.insert(0.0, 25.0 + eps, data="above_25")

    assert k_below_25.level == 1
    assert k_exact_25.level == 2  # 25.0m belongs to Level 2
    assert k_above_25.level == 2

    # 50m Boundary
    k_below_50 = grid.insert(-(50.0 - eps), 0.0, data="below_50")
    k_exact_50 = grid.insert(-50.0, 0.0, data="exact_50")
    k_above_50 = grid.insert(-(50.0 + eps), 0.0, data="above_50")

    assert k_below_50.level == 2
    assert k_exact_50.level == 3  # 50.0m belongs to Level 3
    assert k_above_50.level == 3

    # 100m Boundary
    k_below_100 = grid.insert(0.0, -(100.0 - eps), data="below_100")
    k_exact_100 = grid.insert(0.0, -100.0, data="exact_100")
    k_above_100 = grid.insert(0.0, -(100.0 + eps), data="above_100")

    assert k_below_100.level == 3
    assert k_exact_100 is None  # 100.0m is out of range
    assert k_above_100 is None

    # Cross-resolution level identity: Level 0 cell != Level 1 cell
    assert k_below_10 != k_exact_10


# ==============================================================================
# 5. Tests for Cell Boundaries
# ==============================================================================


def test_cell_boundaries_quantization(grid: SparseFoveatedGrid) -> None:
    """Verify points exactly on cell grid boundaries map and query deterministically."""
    # In Level 0: delta = 0.05
    k1 = grid.insert(0.05, 0.10, data="on_boundary")
    k2 = grid.insert(0.04999, 0.10, data="just_below")

    assert k1 != k2
    assert grid.cell_count() == 2
    assert grid.query(0.05, 0.10).items == ["on_boundary"]
    assert grid.query(0.04999, 0.10).items == ["just_below"]


# ==============================================================================
# 6. Tests for Region Queries (query_region)
# ==============================================================================


def test_query_region_empty(grid: SparseFoveatedGrid) -> None:
    """Verify region query returns empty list when no cells fall within the box."""
    grid.insert(5.0, 5.0, data="p1")
    grid.insert(8.0, 8.0, data="p2")

    # Region that contains no points
    results = grid.query_region(min_x=-10.0, max_x=0.0, min_y=-10.0, max_y=0.0)
    assert len(results) == 0


def test_query_region_single_and_multi_cell(grid: SparseFoveatedGrid) -> None:
    """Verify region query retrieves matching subset of occupied cells."""
    c1 = grid.insert(1.0, 1.0, data="p1")
    c2 = grid.insert(2.0, 2.0, data="p2")
    grid.insert(15.0, 15.0, data="p3")

    # Query box around [0, 3] x [0, 3] -> should contain c1 and c2, but not c3
    results = grid.query_region(min_x=0.0, max_x=3.0, min_y=0.0, max_y=3.0)
    assert len(results) == 2
    keys = {cell.key for cell in results}
    assert keys == {c1, c2}


def test_query_region_negative_coordinates(grid: SparseFoveatedGrid) -> None:
    """Verify region query functions across negative coordinate boxes."""
    c_neg1 = grid.insert(-3.0, -4.0, data="neg1")
    c_neg2 = grid.insert(-8.0, -7.0, data="neg2")
    grid.insert(3.0, 4.0, data="pos")

    # Query box in Quadrant 3 [-10, -1] x [-10, -1]
    results = grid.query_region(min_x=-10.0, max_x=-1.0, min_y=-10.0, max_y=-1.0)
    assert len(results) == 2
    keys = {cell.key for cell in results}
    assert keys == {c_neg1, c_neg2}


def test_query_region_crossing_resolution_bands(grid: SparseFoveatedGrid) -> None:
    """Verify region query seamlessly captures cells spanning multiple foveation bands."""
    # Near ring (Level 0, ~5m)
    grid.insert(5.0, 0.0, data="near_cell")
    # Mid-near ring (Level 1, ~15m)
    grid.insert(15.0, 0.0, data="mid_near_cell")
    # Mid ring (Level 2, ~35m)
    grid.insert(35.0, 0.0, data="mid_cell")
    # Far ring (Level 3, ~75m)
    grid.insert(75.0, 0.0, data="far_cell")

    # Query wide corridor [0, 80] x [-5, 5]
    results = grid.query_region(min_x=0.0, max_x=80.0, min_y=-5.0, max_y=5.0)
    assert len(results) == 4
    levels = {cell.key.level for cell in results}
    assert levels == {0, 1, 2, 3}


def test_query_region_bounding_box_mode(grid: SparseFoveatedGrid) -> None:
    """Verify region query with use_cell_center=False tests cell bounding intersection."""
    # In Level 3 (delta = 0.50m), cell center around (60.25, 0.25)
    c_far = grid.insert(60.2, 0.2, data="far")
    cell = grid.query_cell(c_far)
    assert cell is not None

    # Query box that overlaps cell corner but does NOT contain cell center
    # Cell bounds: [60.0, 60.5] x [0.0, 0.5]
    # Box: [60.4, 61.0] x [0.4, 1.0] (center 60.25, 0.25 is outside, but overlap is True)
    center_mode = grid.query_region(60.4, 61.0, 0.4, 1.0, use_cell_center=True)
    overlap_mode = grid.query_region(60.4, 61.0, 0.4, 1.0, use_cell_center=False)

    assert len(center_mode) == 0
    assert len(overlap_mode) == 1


# ==============================================================================
# 7. Tests for Direct Key Lookup, Clear, and Memory Estimation
# ==============================================================================


def test_query_cell_direct_key(grid: SparseFoveatedGrid) -> None:
    """Verify direct CellKey lookup without coordinate conversions."""
    key = grid.insert(12.0, 4.0, data="payload_data")
    assert key is not None

    # Query using CellKey object
    cell = grid.query_cell(key)
    assert cell is not None
    assert cell.items == ["payload_data"]

    # Query using raw tuple (level, i, j)
    cell_tuple = grid.query_cell((key.level, key.i, key.j))
    assert cell_tuple == cell

    # Non-existent key
    assert grid.query_cell(CellKey(level=0, i=0, j=0)) is None


def test_clear_grid(grid: SparseFoveatedGrid) -> None:
    """Verify clear() resets storage completely."""
    grid.insert(1.0, 1.0, data="p1")
    grid.insert(20.0, 0.0, data="p2")
    assert grid.cell_count() == 2

    grid.clear()
    assert grid.cell_count() == 0
    assert grid.query(1.0, 1.0) is None
    assert len(grid.get_cells()) == 0


def test_memory_usage_accounting(grid: SparseFoveatedGrid) -> None:
    """Verify memory_usage() and memory_usage_breakdown() report deterministic positive metrics."""
    initial_mem = grid.memory_usage()
    assert initial_mem > 0

    # Insert 100 points
    for idx in range(100):
        grid.insert(float(idx % 10) * 0.5 + 0.1, float(idx // 10) * 0.5 + 0.1, data=(idx, 1.0))

    loaded_breakdown = grid.memory_usage_breakdown()
    assert loaded_breakdown["dict_table_bytes"] > 0
    assert loaded_breakdown["keys_bytes"] > 0
    assert loaded_breakdown["cells_bytes"] > 0
    assert loaded_breakdown["items_containers_bytes"] > 0
    assert loaded_breakdown["payloads_bytes"] > 0
    assert loaded_breakdown["total_bytes"] > initial_mem
    assert grid.memory_usage() == loaded_breakdown["total_bytes"]


def test_benchmark_functionality() -> None:
    """Verify that the benchmark execution logic runs correctly on a mini workload."""
    from scripts.benchmark_foveated_grid import (
        calculate_theoretical_metrics,
        generate_query_workload,
        generate_synthetic_workload,
        run_benchmark,
    )
    from src.foveated_grid import FoveatedGridIndexer

    indexer = FoveatedGridIndexer()
    theo = calculate_theoretical_metrics(indexer)
    assert theo["uniform_square_cells"] == 16000000
    assert theo["total_foveated_square_cells"] == 730000
    assert theo["square_reduction_pct"] > 95.0

    workload = generate_synthetic_workload(50, seed=42)
    assert len(workload) == 50

    queries = generate_query_workload(workload, num_queries=20, seed=42)
    assert len(queries) == 20

    res = run_benchmark(point_workloads=[50], num_trials=1, query_count=20)
    assert len(res["workload_results"]) == 1
    assert res["workload_results"][0]["num_points"] == 50
