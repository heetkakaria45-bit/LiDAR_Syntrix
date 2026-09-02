"""Unit tests for Foveated Spatial Grid module."""

import numpy as np
from src.foveated_grid import FoveatedGridIndexer, FoveationRing


def test_foveation_ring_ranges() -> None:
    """Ensure ring distance intervals are correctly identified."""
    indexer = FoveatedGridIndexer()

    # Level 0: 0-10m
    r0 = indexer.get_ring_for_distance(5.0)
    assert r0 is not None and r0.level_id == 0 and r0.resolution == 0.05

    # Level 1: 10-25m
    r1 = indexer.get_ring_for_distance(15.0)
    assert r1 is not None and r1.level_id == 1 and r1.resolution == 0.10

    # Level 2: 25-50m
    r2 = indexer.get_ring_for_distance(30.0)
    assert r2 is not None and r2.level_id == 2 and r2.resolution == 0.25

    # Level 3: 50-100m
    r3 = indexer.get_ring_for_distance(75.0)
    assert r3 is not None and r3.level_id == 3 and r3.resolution == 0.50

    # Out of range
    assert indexer.get_ring_for_distance(150.0) is None
    assert indexer.get_ring_for_distance(-1.0) is None


def test_world_to_cell_and_inverse() -> None:
    """Ensure coordinate transforms are invertible and handle negative coordinates."""
    indexer = FoveatedGridIndexer()

    x, y = -4.2, 3.8
    cell_info = indexer.world_to_cell(x, y)
    assert cell_info is not None
    level_id, cell_ix, cell_iy, cx, cy = cell_info

    # Invert
    inv_cx, inv_cy, res = indexer.cell_to_world(level_id, cell_ix, cell_iy)
    assert abs(inv_cx - cx) < 1e-5
    assert abs(inv_cy - cy) < 1e-5
    assert abs(cx - x) <= res
    assert abs(cy - y) <= res


def test_bin_points() -> None:
    """Ensure point cloud binning distributes points across multi-resolution cells."""
    indexer = FoveatedGridIndexer()
    points = np.array([
        [2.0, 1.0, 0.0],    # In ring 0 (near, 5cm)
        [2.01, 1.01, 0.0],  # Also in same cell in ring 0
        [12.0, 5.0, 0.0],   # In ring 1 (mid-near, 10cm)
        [60.0, 20.0, 0.0],  # In ring 3 (far, 50cm)
    ], dtype=np.float32)

    bins = indexer.bin_points(points)
    assert len(bins) >= 3

    # Check that the two close points share a bin
    shared_bins = [k for k, v in bins.items() if len(v) == 2]
    assert len(shared_bins) == 1
    assert shared_bins[0][0] == 0  # Ring 0


def test_adaptive_refinement_formula() -> None:
    """Ensure adaptive refinement reduces cell size for safety-critical targets."""
    indexer = FoveatedGridIndexer()
    base_res = 0.50  # 50cm in far ring

    # High semantic priority (VRU / Pedestrian)
    refined = indexer.compute_adaptive_resolution(
        base_resolution=base_res, semantic_priority=1.0, uncertainty=0.0
    )
    assert refined < base_res
    assert refined >= 0.05
