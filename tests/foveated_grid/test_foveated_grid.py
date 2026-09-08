import math
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
    assert r2 is not None and r2.level_id == 2 and r2.resolution == 0.20

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


def test_navigation_importance_scoring() -> None:
    """Ensure navigation-critical obstacles in path receive high importance score."""
    indexer = FoveatedGridIndexer()

    # Pedestrian (class 3) in forward corridor at 15m
    score_ped, components_ped, req_refine_ped = indexer.compute_navigation_importance(
        x=15.0, y=0.5, semantic_class=3, is_hazard=False, is_non_traversable=True
    )
    assert score_ped >= 0.60
    assert req_refine_ped is True
    assert components_ped["semantic_score"] == 1.0

    # Drivable road background (class 0) at 40m
    score_road, _, req_refine_road = indexer.compute_navigation_importance(
        x=40.0, y=10.0, semantic_class=0, is_hazard=False, is_non_traversable=False
    )
    assert score_road < 0.40
    assert req_refine_road is False


def test_sparse_local_patch_refinement() -> None:
    """Ensure local patch refinement refines only points in the obstacle radius."""
    indexer = FoveatedGridIndexer()

    # Generate synthetic points around obstacle at (30.0, 0.0)
    pts_hazard = np.random.uniform(-1.0, 1.0, size=(50, 3)).astype(np.float32)
    pts_hazard[:, 0] += 30.0  # Center around (30, 0)

    # Distant points far from hazard (e.g. at 45m)
    pts_far = np.random.uniform(-1.0, 1.0, size=(50, 3)).astype(np.float32)
    pts_far[:, 0] += 45.0
    pts_far[:, 1] += 15.0

    all_pts = np.vstack([pts_hazard, pts_far])

    # Refine only local patch at (30.0, 0.0) with radius 2.5m down to 10cm (0.10m)
    refined_cells = indexer.refine_local_patch(
        all_pts, center_x=30.0, center_y=0.0, radius=2.5, target_resolution=0.10
    )

    assert len(refined_cells) > 0
    # All refined cells should be centered near (30.0, 0.0) within radius + resolution
    for _, (cx, cy, indices) in refined_cells.items():
        assert math.hypot(cx - 30.0, cy - 0.0) <= 3.5
        assert len(indices) > 0

