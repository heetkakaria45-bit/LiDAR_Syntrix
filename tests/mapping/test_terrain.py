"""Unit tests for Phase 2: Terrain and Traversability Analysis.

Verifies:
- Point density calculations
- Local slope estimation using planar regression
- Elevation discontinuity (step height)
- Categorical traversability: DRIVABLE, NON_DRIVABLE, UNKNOWN
- Continuous traversability score [0, 1]
- Semantic obstacle penalties (pedestrian, vehicle, wall, pole, grass)
- Slope and roughness thresholds from config
"""

import math
import numpy as np
import pytest

from src.contracts import GridCell
from src.mapping.config import TraversabilityConfig
from src.mapping.terrain import (
    TerrainAttributes,
    TraversabilityState,
    analyze_cell_terrain,
    compute_local_slope_and_step,
    compute_point_density,
    compute_traversability_score,
)


def _make_cell(
    x: float,
    y: float,
    z: float,
    sem_cls: int = 0,
    conf: float = 1.0,
    roughness: float = 0.0,
    point_count: int = 10,
    occupancy: float = 0.95,
) -> GridCell:
    return GridCell(
        resolution_level="near",
        cell_x=x,
        cell_y=y,
        elevation=z,
        min_z=z - roughness,
        max_z=z + roughness,
        semantic_class=sem_cls,
        confidence=conf,
        occupancy=occupancy,
        point_count=point_count,
        roughness=roughness,
        timestamp=100.0,
    )


class TestPointDensity:
    def test_density_calculation(self) -> None:
        # 10 points in a 0.1m x 0.1m cell -> Area = 0.01 m^2 -> 1000 pts/m^2
        density = compute_point_density(point_count=10, cell_resolution=0.10)
        assert density == pytest.approx(1000.0)

    def test_density_zero_res(self) -> None:
        assert compute_point_density(10, 0.0) == pytest.approx(0.0)


class TestLocalSlopeEstimation:
    def test_flat_terrain_slope(self) -> None:
        center = _make_cell(0.0, 0.0, 0.0)
        # 4 orthogonal neighbors all at z = 0.0
        neighbors = [
            _make_cell(0.1, 0.0, 0.0),
            _make_cell(-0.1, 0.0, 0.0),
            _make_cell(0.0, 0.1, 0.0),
            _make_cell(0.0, -0.1, 0.0),
        ]

        slope_rad, slope_deg, max_step = compute_local_slope_and_step(center, neighbors, 0.1)
        assert slope_deg == pytest.approx(0.0, abs=1e-3)
        assert max_step == pytest.approx(0.0, abs=1e-3)

    def test_sloped_ramp_terrain(self) -> None:
        # A 10-degree incline along +X: dz = dx * tan(10 deg)
        deg = 10.0
        tan_theta = math.tan(math.radians(deg))
        center = _make_cell(1.0, 0.0, 1.0 * tan_theta)
        neighbors = [
            _make_cell(0.9, 0.0, 0.9 * tan_theta),
            _make_cell(1.1, 0.0, 1.1 * tan_theta),
            _make_cell(1.0, 0.1, 1.0 * tan_theta),
            _make_cell(1.0, -0.1, 1.0 * tan_theta),
        ]

        slope_rad, slope_deg, max_step = compute_local_slope_and_step(center, neighbors, 0.1)
        assert slope_deg == pytest.approx(deg, abs=0.1)

    def test_isolated_cell_insufficient_neighbors(self) -> None:
        center = _make_cell(0.0, 0.0, 0.0)
        # 0 or 1 neighbor
        assert math.isnan(compute_local_slope_and_step(center, [], 0.1)[0])
        assert math.isnan(
            compute_local_slope_and_step(center, [_make_cell(0.1, 0.0, 0.0)], 0.1)[0]
        )


class TestTraversabilityClassification:
    def test_flat_road_is_drivable(self) -> None:
        cell = _make_cell(0.0, 0.0, 0.0, sem_cls=0, conf=0.95, roughness=0.01)
        state, score = compute_traversability_score(
            cell=cell,
            slope_deg=1.0,
            roughness=0.01,
            max_step=0.02,
        )
        assert state == TraversabilityState.DRIVABLE
        assert score > 0.8

    def test_steep_slope_is_non_drivable(self) -> None:
        # Config threshold is 15 degrees
        cell = _make_cell(0.0, 0.0, 0.0, sem_cls=0)
        state, score = compute_traversability_score(
            cell=cell,
            slope_deg=22.0,  # Exceeds 15 deg
            roughness=0.01,
            max_step=0.02,
        )
        assert state == TraversabilityState.NON_DRIVABLE
        assert score == pytest.approx(0.0)

    def test_high_roughness_is_non_drivable(self) -> None:
        # Config threshold is 0.05m
        cell = _make_cell(0.0, 0.0, 0.0, sem_cls=0, roughness=0.08)
        state, score = compute_traversability_score(
            cell=cell,
            slope_deg=2.0,
            roughness=0.08,
            max_step=0.02,
        )
        assert state == TraversabilityState.NON_DRIVABLE

    def test_large_step_discontinuity_is_non_drivable(self) -> None:
        # Step threshold is 0.10m
        cell = _make_cell(0.0, 0.0, 0.0, sem_cls=0)
        state, score = compute_traversability_score(
            cell=cell,
            slope_deg=0.0,
            roughness=0.01,
            max_step=0.18,  # Large vertical curb/step
        )
        assert state == TraversabilityState.NON_DRIVABLE

    def test_semantic_obstacles_are_non_drivable(self) -> None:
        # Classes: 2 (VEHICLE), 3 (PEDESTRIAN), 4 (CYCLIST), 5 (POLE), 6 (WALL)
        for obstacle_cls in [1, 2, 3, 4, 5, 6, 7]:
            cell = _make_cell(0.0, 0.0, 0.0, sem_cls=obstacle_cls)
            state, score = compute_traversability_score(
                cell=cell,
                slope_deg=0.0,
                roughness=0.0,
                max_step=0.0,
            )
            assert state == TraversabilityState.NON_DRIVABLE
            if obstacle_cls in [2, 3, 4, 5, 6, 7]:
                assert score == pytest.approx(0.0)

    def test_unobserved_or_low_occupancy_is_unknown(self) -> None:
        cell = _make_cell(0.0, 0.0, 0.0, point_count=0, occupancy=0.05)
        state, score = compute_traversability_score(
            cell=cell,
            slope_deg=0.0,
            roughness=0.0,
            max_step=0.0,
        )
        assert state == TraversabilityState.UNKNOWN
        assert score == pytest.approx(0.0)
