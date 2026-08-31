"""Unit tests for Phase 4: Geometric Hazard Detection & Obstacle Representation.

Verifies:
- Curb candidate detection across adjacent road/sidewalk cells
- Pothole detection relative to surrounding drivable road
- Multi-layer vertical overhang representation and clearance evaluation
- Verification on synthetic scenes (flat road, curb, pothole, overhang)
"""

from typing import Optional, Tuple
import numpy as np
import pytest

from src.contracts import GridCell, SyntheticSceneConfig
from src.mapping.config import HazardConfig
from src.mapping.hazards import (
    CurbCandidate,
    OverhangCell,
    PotholeCandidate,
    detect_curb_candidates,
    detect_map_hazards,
    detect_overhang_cells,
    detect_pothole_candidates,
)
from src.mapping.mapper import SemanticElevationMapper
from src.preprocessing.synthetic import generate_synthetic_scene


def _make_cell(
    gx: int,
    gy: int,
    z: float,
    sem_cls: int = 0,
    min_z: Optional[float] = None,
    max_z: Optional[float] = None,
    conf: float = 1.0,
) -> Tuple[Tuple[int, int], GridCell]:
    res = 0.10
    cx = gx * res + res / 2.0
    cy = gy * res + res / 2.0
    cell = GridCell(
        resolution_level="near",
        cell_x=cx,
        cell_y=cy,
        elevation=z,
        min_z=min_z if min_z is not None else z,
        max_z=max_z if max_z is not None else z,
        semantic_class=sem_cls,
        confidence=conf,
        occupancy=0.95,
        point_count=15,
        roughness=0.01,
        timestamp=100.0,
    )
    return (gx, gy), cell


class TestCurbDetection:
    def test_curb_detection_pair(self) -> None:
        # Cell A: Road at z = 0.0m (class 0)
        # Cell B: Sidewalk at z = 0.15m (class 1), 15 cm step
        cells = dict([
            _make_cell(0, 0, z=0.0, sem_cls=0),
            _make_cell(1, 0, z=0.15, sem_cls=1),
        ])

        candidates = detect_curb_candidates(cells)
        assert len(candidates) == 1
        curb = candidates[0]
        assert curb.step_height == pytest.approx(0.15)
        assert curb.adjacent_road_cell == (0, 0)
        assert curb.adjacent_sidewalk_cell == (1, 0)
        assert curb.confidence > 0.5

    def test_curb_rejected_if_step_too_small_or_large(self) -> None:
        # Step of 3 cm (< 8 cm min)
        small_cells = dict([
            _make_cell(0, 0, z=0.0, sem_cls=0),
            _make_cell(1, 0, z=0.03, sem_cls=1),
        ])
        assert len(detect_curb_candidates(small_cells)) == 0

        # Step of 50 cm (> 25 cm max)
        wall_cells = dict([
            _make_cell(0, 0, z=0.0, sem_cls=0),
            _make_cell(1, 0, z=0.50, sem_cls=1),
        ])
        assert len(detect_curb_candidates(wall_cells)) == 0


class TestPotholeDetection:
    def test_pothole_detection_in_road(self) -> None:
        # Create a 3x3 road patch where the center cell is depressed by 8 cm (-0.08m)
        cells = {}
        for x in range(-1, 2):
            for y in range(-1, 2):
                if x == 0 and y == 0:
                    k, c = _make_cell(x, y, z=-0.08, sem_cls=7)  # Depressed pothole
                else:
                    k, c = _make_cell(x, y, z=0.0, sem_cls=0)  # Surrounding flat road
                cells[k] = c

        potholes = detect_pothole_candidates(cells)
        assert len(potholes) == 1
        p = potholes[0]
        assert p.cell_key == (0, 0)
        assert p.depth == pytest.approx(0.08)
        assert p.surrounding_mean_z == pytest.approx(0.0)
        assert p.confidence > 0.4


class TestOverhangRepresentation:
    def test_overhang_clearance_evaluation(self) -> None:
        # Overhead bridge cell: ground at min_z = 0.0, slab at max_z = 3.5m
        k, c = _make_cell(5, 5, z=1.75, sem_cls=6, min_z=0.0, max_z=3.5)
        cells = {k: c}

        overhangs = detect_overhang_cells(cells)
        assert len(overhangs) == 1
        oh = overhangs[0]
        assert oh.vertical_clearance == pytest.approx(3.5)
        assert oh.is_traversable_clearance is True

    def test_low_barrier_not_overhang(self) -> None:
        # Vehicle box: min_z = 0.0, max_z = 1.4m (< 2.2m clearance)
        k, c = _make_cell(2, 2, z=0.7, sem_cls=2, min_z=0.0, max_z=1.4)
        cells = {k: c}
        assert len(detect_overhang_cells(cells)) == 0


class TestSyntheticScenesHazardVerification:
    def test_synthetic_curb_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="curb", num_points=3000, seed=42)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)

        hazards = detect_map_hazards(sem_map)
        assert hazards["summary"]["num_curb_candidates"] > 0
        # Check step heights are around the configured 15 cm step
        steps = [c.step_height for c in hazards["curbs"]]
        assert any(0.10 <= s <= 0.20 for s in steps)

    def test_synthetic_pothole_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="pothole", num_points=3000, seed=42)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)

        hazards = detect_map_hazards(sem_map)
        assert hazards["summary"]["num_pothole_candidates"] > 0
        depths = [p.depth for p in hazards["potholes"]]
        assert any(d >= 0.05 for d in depths)

    def test_synthetic_overhang_scene(self) -> None:
        cfg = SyntheticSceneConfig(scene_type="overhang", num_points=3000, seed=42)
        _, cloud = generate_synthetic_scene(cfg)
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)

        hazards = detect_map_hazards(sem_map)
        assert hazards["summary"]["num_overhang_cells"] > 0
        clearances = [oh.vertical_clearance for oh in hazards["overhangs"]]
        assert any(c >= 3.0 for c in clearances)
