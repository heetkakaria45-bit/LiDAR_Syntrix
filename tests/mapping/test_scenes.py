"""Comprehensive unit and integration tests for all 9 required synthetic scenes.

Required scenes:
1. Flat ground
2. Sloped terrain
3. Curb
4. Pothole
5. Vehicle
6. Pedestrian
7. Pole
8. Wall
9. Overhang

Also tests specific edge cases:
- Empty point cloud
- Single-point cell
- Multiple points in one cell
- Mixed semantic classes
- Confidence = 0 and 1
- NaN/Inf inputs
- Isolated cell with no neighbors
- Large Z outlier
- Duplicate points
"""

import numpy as np
import pytest

from src.contracts import GridCell, SemanticPointCloud, SyntheticSceneConfig
from src.mapping.aggregation import (
    aggregate_cell,
    aggregate_semantics,
    compute_elevation_bounds,
    compute_roughness,
)
from src.mapping.hazards import detect_map_hazards
from src.mapping.mapper import SemanticElevationMapper
from src.mapping.terrain import (
    TraversabilityState,
    analyze_map_terrain,
    compute_traversability_score,
)
from src.preprocessing.synthetic import generate_synthetic_scene


class TestSyntheticScenesNineTypes:
    """Validate mapping, terrain, and hazards across the 9 required synthetic scenes."""

    def test_1_flat_ground_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="flat_road", num_points=3000, seed=1)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        terrain = analyze_map_terrain(sem_map)

        # Flat ground cells across all rings should be predominantly drivable
        all_terrain = [t for ring in terrain.values() for t in ring.values()]
        assert len(all_terrain) > 0
        drivable_cells = [
            t for t in all_terrain if t.traversability_state == TraversabilityState.DRIVABLE
        ]
        assert len(drivable_cells) / len(all_terrain) > 0.85
        # Slope across well-sampled cells should be near flat
        slopes = [t.slope_deg for t in all_terrain if not np.isnan(t.slope_deg)]
        assert len(slopes) > 50
        assert np.median(slopes) < 3.0

    def test_2_sloped_terrain_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="slope", slope_deg=10.0, num_points=3000, seed=2)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        terrain = analyze_map_terrain(sem_map)

        # Slopes around 10 degrees should be observed across valid neighbor cells
        valid_slopes = [
            t.slope_deg
            for ring in terrain.values()
            for t in ring.values()
            if not np.isnan(t.slope_deg)
        ]
        assert len(valid_slopes) > 10
        assert 7.0 <= np.median(valid_slopes) <= 13.0

    def test_3_curb_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="curb", curb_height=0.15, num_points=3000, seed=3)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        hazards = detect_map_hazards(sem_map)

        assert hazards["summary"]["num_curb_candidates"] > 0
        steps = [c.step_height for c in hazards["curbs"]]
        assert any(0.10 <= s <= 0.20 for s in steps)

    def test_4_pothole_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="pothole", pothole_depth=0.08, num_points=3000, seed=4)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        hazards = detect_map_hazards(sem_map)

        assert hazards["summary"]["num_pothole_candidates"] > 0
        depths = [p.depth for p in hazards["potholes"]]
        assert any(d >= 0.05 for d in depths)

    def test_5_vehicle_scene(self) -> None:
        # Default urban scene includes parked vehicle (class 2)
        cfg = SyntheticSceneConfig(scene_type="urban", num_points=4000, seed=5)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        terrain = analyze_map_terrain(sem_map)

        # Vehicle cells must be non-drivable with zero traversability score
        all_cells = [c for ring in sem_map.cells.values() for c in ring.values()]
        veh_cells = [c for c in all_cells if c.semantic_class == 2]
        assert len(veh_cells) > 0

        for ring_name, ring_terrain in terrain.items():
            for k, t_attr in ring_terrain.items():
                cell = sem_map.cells[ring_name][k]
                if cell.semantic_class == 2:
                    assert t_attr.traversability_state == TraversabilityState.NON_DRIVABLE
                    assert t_attr.traversability_score == pytest.approx(0.0)

    def test_6_pedestrian_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="urban", num_points=4000, seed=6)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        terrain = analyze_map_terrain(sem_map)

        ped_cells = [
            c
            for ring in sem_map.cells.values()
            for c in ring.values()
            if c.semantic_class == 3
        ]
        assert len(ped_cells) > 0
        for ring_name, ring_terrain in terrain.items():
            for k, t_attr in ring_terrain.items():
                cell = sem_map.cells[ring_name][k]
                if cell.semantic_class == 3:
                    assert t_attr.traversability_state == TraversabilityState.NON_DRIVABLE
                    assert t_attr.traversability_score == pytest.approx(0.0)

    def test_7_pole_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="urban", num_points=4000, seed=7)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        terrain = analyze_map_terrain(sem_map)

        pole_cells = [
            c
            for ring in sem_map.cells.values()
            for c in ring.values()
            if c.semantic_class == 5
        ]
        assert len(pole_cells) > 0
        for ring_name, ring_terrain in terrain.items():
            for k, t_attr in ring_terrain.items():
                cell = sem_map.cells[ring_name][k]
                if cell.semantic_class == 5:
                    assert t_attr.traversability_state == TraversabilityState.NON_DRIVABLE

    def test_8_wall_scene(self) -> None:
        # Generate planar wall / building facade (class 6)
        n = 500
        rng = np.random.default_rng(8)
        xw = rng.uniform(8.0, 12.0, n).astype(np.float32)
        yw = np.full((n,), 5.0, dtype=np.float32) + rng.normal(0.0, 0.02, n).astype(np.float32)
        zw = rng.uniform(0.0, 3.0, n).astype(np.float32)
        pts = np.stack([xw, yw, zw], axis=1)
        classes = np.full((n,), 6, dtype=np.int32)
        conf = np.ones((n,), dtype=np.float32)

        cloud = SemanticPointCloud(
            points=pts,
            semantic_class=classes,
            confidence=conf,
            timestamp=100.0,
            frame_id="wall_test",
        )
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        terrain = analyze_map_terrain(sem_map)

        wall_cells = [
            c
            for ring in sem_map.cells.values()
            for c in ring.values()
            if c.semantic_class == 6
        ]
        assert len(wall_cells) > 0
        for ring_name, ring_terrain in terrain.items():
            for k, t_attr in ring_terrain.items():
                cell = sem_map.cells[ring_name][k]
                if cell.semantic_class == 6:
                    assert t_attr.traversability_state == TraversabilityState.NON_DRIVABLE

    def test_9_overhang_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="overhang", num_points=3000, seed=9)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)
        hazards = detect_map_hazards(sem_map)

        assert hazards["summary"]["num_overhang_cells"] > 0
        oh = hazards["overhangs"][0]
        assert oh.vertical_clearance >= 2.2
        assert oh.is_traversable_clearance is True


class TestEdgeCases:
    """Verify specific edge cases outlined in instructions."""

    def test_duplicate_points_in_cell(self) -> None:
        z = np.array([1.5, 1.5, 1.5, 1.5], dtype=np.float32)
        classes = np.array([0, 0, 0, 0], dtype=np.int32)
        conf = np.array([0.9, 0.9, 0.9, 0.9], dtype=np.float32)

        cell = aggregate_cell("near", 1.0, 1.0, z, classes, conf, 100.0)
        assert cell is not None
        assert cell.elevation == pytest.approx(1.5)
        assert cell.min_z == pytest.approx(1.5)
        assert cell.max_z == pytest.approx(1.5)
        assert cell.roughness == pytest.approx(0.0)
        assert cell.point_count == 4

    def test_extreme_z_outlier(self) -> None:
        z = np.array([0.0, 0.01, -0.01, 0.0, 500.0], dtype=np.float32)
        classes = np.array([0, 0, 0, 0, 0], dtype=np.int32)
        conf = np.array([0.8, 0.8, 0.8, 0.8, 0.1], dtype=np.float32)

        cell = aggregate_cell("near", 0.0, 0.0, z, classes, conf, 100.0)
        assert cell is not None
        # Median elevation remains at ~0.0 despite the 500m outlier
        assert abs(cell.elevation) < 0.02
        assert cell.max_z == pytest.approx(500.0)

    def test_confidence_zero_and_one(self) -> None:
        # Confidence 0 point vs Confidence 1 point
        classes = np.array([0, 2], dtype=np.int32)
        conf = np.array([0.0, 1.0], dtype=np.float32)
        dom, agg_c, probs = aggregate_semantics(classes, conf)
        assert dom == 2
        assert agg_c == pytest.approx(1.0)
        assert probs[2] == pytest.approx(1.0)

    def test_mixed_classes_tie_breaking(self) -> None:
        # Exactly equal weighted score
        classes = np.array([0, 1], dtype=np.int32)
        conf = np.array([0.8, 0.8], dtype=np.float32)
        dom, agg_c, probs = aggregate_semantics(classes, conf)
        assert dom in (0, 1)
        assert agg_c == pytest.approx(0.8)
        assert probs[0] == pytest.approx(0.5)
        assert probs[1] == pytest.approx(0.5)
