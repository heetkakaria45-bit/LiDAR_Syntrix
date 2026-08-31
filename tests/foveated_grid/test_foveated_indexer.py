"""Unit tests for Foveated Spatial Grid Indexer and coordinate mapping operations.

Module: tests/foveated_grid/test_foveated_indexer.py
Tests:
    - resolution_for_distance()
    - world_to_cell()
    - cell_to_world()
    - Ring boundary conditions [0, 10), [10, 25), [25, 50), [50, 100)
    - Positive, negative, and quadrant combinations
    - Cell boundary quantization
    - Out of range / negative distances
    - Round-trip world -> cell -> world consistency
"""

import math

import pytest

from src.foveated_grid import (
    CellKey,
    FoveatedGridIndexer,
    cell_to_world,
    resolution_for_distance,
    world_to_cell,
)


@pytest.fixture
def indexer() -> FoveatedGridIndexer:
    """Instantiate default foveated grid indexer from project configuration."""
    return FoveatedGridIndexer()


# ==============================================================================
# 1. Tests for resolution_for_distance()
# ==============================================================================


def test_resolution_for_distance_nominal(indexer: FoveatedGridIndexer) -> None:
    """Verify expected resolutions across nominal mid-band distances."""
    # Level 0 (0-10m) -> 0.05m (5 cm)
    assert indexer.resolution_for_distance(0.0) == pytest.approx(0.05)
    assert indexer.resolution_for_distance(5.0) == pytest.approx(0.05)

    # Level 1 (10-25m) -> 0.10m (10 cm)
    assert indexer.resolution_for_distance(15.0) == pytest.approx(0.10)

    # Level 2 (25-50m) -> 0.25m (25 cm)
    assert indexer.resolution_for_distance(35.0) == pytest.approx(0.25)

    # Level 3 (50-100m) -> 0.50m (50 cm)
    assert indexer.resolution_for_distance(75.0) == pytest.approx(0.50)


def test_resolution_for_distance_exact_boundaries(indexer: FoveatedGridIndexer) -> None:
    """Verify strict half-open interval [r_k, r_{k+1}) ownership at exact boundaries."""
    # Exactly 0.0m belongs to Level 0 (0.05m)
    assert indexer.resolution_for_distance(0.0) == pytest.approx(0.05)

    # Exactly 10.0m belongs to Level 1 (0.10m)
    assert indexer.resolution_for_distance(10.0) == pytest.approx(0.10)

    # Exactly 25.0m belongs to Level 2 (0.25m)
    assert indexer.resolution_for_distance(25.0) == pytest.approx(0.25)

    # Exactly 50.0m belongs to Level 3 (0.50m)
    assert indexer.resolution_for_distance(50.0) == pytest.approx(0.50)

    # Exactly 100.0m is out of range
    assert indexer.resolution_for_distance(100.0) is None


def test_resolution_for_distance_epsilon_boundaries(indexer: FoveatedGridIndexer) -> None:
    """Verify resolution lookup just below and just above ring transitions."""
    eps = 1e-5

    # Near / Mid-near boundary around 10m
    assert indexer.resolution_for_distance(10.0 - eps) == pytest.approx(0.05)
    assert indexer.resolution_for_distance(10.0 + eps) == pytest.approx(0.10)

    # Mid-near / Mid boundary around 25m
    assert indexer.resolution_for_distance(25.0 - eps) == pytest.approx(0.10)
    assert indexer.resolution_for_distance(25.0 + eps) == pytest.approx(0.25)

    # Mid / Far boundary around 50m
    assert indexer.resolution_for_distance(50.0 - eps) == pytest.approx(0.25)
    assert indexer.resolution_for_distance(50.0 + eps) == pytest.approx(0.50)

    # Far boundary around 100m
    assert indexer.resolution_for_distance(100.0 - eps) == pytest.approx(0.50)
    assert indexer.resolution_for_distance(100.0 + eps) is None


def test_resolution_for_distance_out_of_bounds(indexer: FoveatedGridIndexer) -> None:
    """Verify None is returned for negative or beyond max_radius distances."""
    assert indexer.resolution_for_distance(-1.0) is None
    assert indexer.resolution_for_distance(-0.001) is None
    assert indexer.resolution_for_distance(100.0) is None
    assert indexer.resolution_for_distance(150.0) is None


# ==============================================================================
# 2. Tests for world_to_cell() across quadrants and boundaries
# ==============================================================================


def test_world_to_cell_origin(indexer: FoveatedGridIndexer) -> None:
    """Verify origin (0, 0) maps to level 0 center cell index."""
    cell = indexer.world_to_cell(0.0, 0.0)
    assert cell is not None
    assert cell.level == 0
    # For level 0: max_range = 10.0, delta = 0.05, x_min = -10.0
    # i = floor((0 - (-10)) / 0.05) = floor(200.0) = 200
    assert cell.i == 200
    assert cell.j == 200


def test_world_to_cell_quadrants(indexer: FoveatedGridIndexer) -> None:
    """Verify world_to_cell handles all 4 Cartesian quadrants deterministically."""
    # Point at radius ~5m (Level 0, delta=0.05, x_min=-10.0)
    # (+3, +4): Quadrant 1
    c_q1 = indexer.world_to_cell(3.0, 4.0)
    assert c_q1 is not None
    assert c_q1.level == 0
    assert c_q1.i == int(math.floor((3.0 - (-10.0)) / 0.05))  # floor(260.0) = 260
    assert c_q1.j == int(math.floor((4.0 - (-10.0)) / 0.05))  # floor(280.0) = 280

    # (-3, +4): Quadrant 2 (negative x)
    c_q2 = indexer.world_to_cell(-3.0, 4.0)
    assert c_q2 is not None
    assert c_q2.level == 0
    assert c_q2.i == int(math.floor((-3.0 - (-10.0)) / 0.05))  # floor(140.0) = 140
    assert c_q2.j == int(math.floor((4.0 - (-10.0)) / 0.05))  # floor(280.0) = 280

    # (-3, -4): Quadrant 3 (negative x and y)
    c_q3 = indexer.world_to_cell(-3.0, -4.0)
    assert c_q3 is not None
    assert c_q3.level == 0
    assert c_q3.i == int(math.floor((-3.0 - (-10.0)) / 0.05))  # 140
    assert c_q3.j == int(math.floor((-4.0 - (-10.0)) / 0.05))  # 120

    # (+3, -4): Quadrant 4 (negative y)
    c_q4 = indexer.world_to_cell(3.0, -4.0)
    assert c_q4 is not None
    assert c_q4.level == 0
    assert c_q4.i == int(math.floor((3.0 - (-10.0)) / 0.05))  # 260
    assert c_q4.j == int(math.floor((-4.0 - (-10.0)) / 0.05))  # 120


def test_world_to_cell_exact_radial_boundaries(indexer: FoveatedGridIndexer) -> None:
    """Verify level assignment for points located exactly on ring boundary radii."""
    # (10.0, 0.0) -> r = 10.0 -> must be level 1
    c_10 = indexer.world_to_cell(10.0, 0.0)
    assert c_10 is not None
    assert c_10.level == 1
    # Level 1: max_range=25.0, delta=0.10, x_min=-25.0
    # i = floor((10.0 - (-25.0)) / 0.10) = floor(350.0) = 350
    assert c_10.i == 350

    # (0.0, -25.0) -> r = 25.0 -> must be level 2
    c_25 = indexer.world_to_cell(0.0, -25.0)
    assert c_25 is not None
    assert c_25.level == 2

    # (-50.0, 0.0) -> r = 50.0 -> must be level 3
    c_50 = indexer.world_to_cell(-50.0, 0.0)
    assert c_50 is not None
    assert c_50.level == 3

    # (100.0, 0.0) -> r = 100.0 -> out of range
    assert indexer.world_to_cell(100.0, 0.0) is None
    assert indexer.world_to_cell(0.0, -100.0) is None


def test_world_to_cell_just_below_and_above_boundaries(indexer: FoveatedGridIndexer) -> None:
    """Verify transition correctness with epsilon offsets across ring boundaries."""
    eps = 1e-4

    # Boundary at r = 10.0 along +X
    c_below = indexer.world_to_cell(10.0 - eps, 0.0)
    c_above = indexer.world_to_cell(10.0 + eps, 0.0)
    assert c_below is not None and c_below.level == 0
    assert c_above is not None and c_above.level == 1

    # Boundary at r = 25.0 along +Y
    c_below = indexer.world_to_cell(0.0, 25.0 - eps)
    c_above = indexer.world_to_cell(0.0, 25.0 + eps)
    assert c_below is not None and c_below.level == 1
    assert c_above is not None and c_above.level == 2

    # Boundary at r = 50.0 along -X
    c_below = indexer.world_to_cell(-(50.0 - eps), 0.0)
    c_above = indexer.world_to_cell(-(50.0 + eps), 0.0)
    assert c_below is not None and c_below.level == 2
    assert c_above is not None and c_above.level == 3

    # Boundary at r = 100.0 along -Y
    c_below = indexer.world_to_cell(0.0, -(100.0 - eps))
    c_above = indexer.world_to_cell(0.0, -(100.0 + eps))
    assert c_below is not None and c_below.level == 3
    assert c_above is None


def test_world_to_cell_exact_cell_boundaries(indexer: FoveatedGridIndexer) -> None:
    """Verify points exactly on cell grid boundaries floor deterministically."""
    # In Level 0: delta = 0.05, x_min = -10.0
    # Point at x = 0.05, y = 0.10 (r = 0.1118m < 10m)
    # (x - x_min)/delta = (0.05 - (-10.0))/0.05 = 10.05 / 0.05 = 201.0 -> floor is 201
    c = indexer.world_to_cell(0.05, 0.10)
    assert c is not None
    assert c.level == 0
    assert c.i == 201
    assert c.j == 202

    # Point just below boundary: x = 0.04999
    # 10.04999 / 0.05 = 200.9998 -> floor is 200
    c_below = indexer.world_to_cell(0.04999, 0.10)
    assert c_below is not None
    assert c_below.i == 200


# ==============================================================================
# 3. Tests for cell_to_world() and round-trip consistency
# ==============================================================================


def test_cell_to_world_center(indexer: FoveatedGridIndexer) -> None:
    """Verify cell_to_world computes the exact geometric center of the cell."""
    # Level 0, cell (200, 200) -> origin cell
    # x_center = -10.0 + (200 + 0.5) * 0.05 = -10.0 + 10.025 = 0.025
    # y_center = -10.0 + (200 + 0.5) * 0.05 = 0.025
    x_c, y_c = indexer.cell_to_world(CellKey(level=0, i=200, j=200))
    assert x_c == pytest.approx(0.025)
    assert y_c == pytest.approx(0.025)

    # Level 1, cell (350, 250)
    # Level 1: max_range = 25.0, delta = 0.10, x_min = -25.0
    # x_center = -25.0 + (350 + 0.5) * 0.10 = -25.0 + 35.05 = 10.05
    # y_center = -25.0 + (250 + 0.5) * 0.10 = -25.0 + 25.05 = 0.05
    x_c, y_c = indexer.cell_to_world(CellKey(level=1, i=350, j=250))
    assert x_c == pytest.approx(10.05)
    assert y_c == pytest.approx(0.05)


def test_roundtrip_cell_world_cell(indexer: FoveatedGridIndexer) -> None:
    """Verify identity world_to_cell(cell_to_world(cell)) == cell for all valid cells."""
    test_points = [
        (0.5, -0.5),
        (3.2, 4.8),
        (-8.5, 2.1),
        (12.4, -15.8),
        (-22.0, -10.0),
        (35.2, 28.1),
        (-45.0, 12.0),
        (65.0, -50.0),
        (-80.0, -40.0),
    ]

    for x, y in test_points:
        cell = indexer.world_to_cell(x, y)
        assert cell is not None, f"Failed to map ({x}, {y})"

        # Reconstruct cell center
        x_center, y_center = indexer.cell_to_world(cell)

        # Mapping the cell center must produce the exact same cell
        recovered_cell = indexer.world_to_cell(x_center, y_center)
        assert recovered_cell == cell, (
            f"Roundtrip failed for ({x}, {y}): original={cell}, "
            f"center=({x_center}, {y_center}), recovered={recovered_cell}"
        )


def test_cell_to_world_invalid_level(indexer: FoveatedGridIndexer) -> None:
    """Verify KeyError is raised when cell level ID does not exist."""
    with pytest.raises(KeyError, match=r"Unknown foveation level ID"):
        indexer.cell_to_world(CellKey(level=99, i=0, j=0))


# ==============================================================================
# 4. Tests for standalone functional helpers and CellKey packing
# ==============================================================================


def test_standalone_functions() -> None:
    """Verify module-level standalone helper functions."""
    assert resolution_for_distance(5.0) == pytest.approx(0.05)
    assert resolution_for_distance(15.0) == pytest.approx(0.10)

    cell = world_to_cell(2.0, 3.0)
    assert cell is not None
    assert cell.level == 0

    x_c, y_c = cell_to_world(cell)
    assert isinstance(x_c, float)
    assert isinstance(y_c, float)


def test_cell_key_packed_uint64() -> None:
    """Verify 64-bit unsigned integer key serialization and deserialization."""
    key = CellKey(level=2, i=350, j=120)
    packed = key.to_packed_uint64()
    assert isinstance(packed, int)

    unpacked = CellKey.from_packed_uint64(packed)
    assert unpacked == key
    assert unpacked.level == 2
    assert unpacked.i == 350
    assert unpacked.j == 120
