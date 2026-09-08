"""Unit tests for Sensor-Grounded Hazard Response & Collision Avoidance Engine."""

import math
import numpy as np
import pytest

from src.contracts import GridCell, SemanticMap
from src.mapping.avoidance import (
    AvoidanceConfig,
    AvoidanceDirection,
    HazardAvoidanceEngine,
    HazardState,
)


def create_mock_semantic_map(
    obstacle_cells: list[tuple[float, float, int]],  # (x, y, semantic_class)
) -> SemanticMap:
    """Helper to construct a mock SemanticMap populated with specific test obstacles."""
    cells: dict[str, dict[tuple[int, int], GridCell]] = {
        "near": {},
        "mid_near": {},
        "mid": {},
        "far": {},
    }

    for idx, (x, y, cls) in enumerate(obstacle_cells):
        dist = math.hypot(x, y)
        if dist < 10.0:
            level = "near"
            res = 0.05
        elif dist < 25.0:
            level = "mid_near"
            res = 0.10
        elif dist < 50.0:
            level = "mid"
            res = 0.20
        else:
            level = "far"
            res = 0.50

        gx = int(math.floor(x / res))
        gy = int(math.floor(y / res))

        cell = GridCell(
            resolution_level=level,
            cell_x=float(x),
            cell_y=float(y),
            elevation=0.0 if cls == 0 else 0.8,
            min_z=0.0,
            max_z=0.0 if cls == 0 else 1.5,
            semantic_class=cls,
            confidence=0.95,
            occupancy=0.05 if cls == 0 else 0.95,
            point_count=20,
            roughness=0.02 if cls == 0 else 0.25,
            timestamp=1.0,
        )
        cells[level][(gx, gy)] = cell

    return SemanticMap(
        cells=cells,
        resolution_levels={"near": 0.05, "mid_near": 0.10, "mid": 0.20, "far": 0.50},
        sensor_pose=np.eye(4, dtype=np.float64),
        timestamp=1.0,
        metadata={"frame_id": "test_frame"},
    )


def test_safe_state_clear_corridor() -> None:
    """When forward corridor is clear (>16m), engine must output SAFE / MAINTAIN_CRUISE."""
    # Obstacle is far away at 30m in forward corridor
    smap = create_mock_semantic_map([(30.0, 0.0, 2)])  # Vehicle at 30m
    engine = HazardAvoidanceEngine()

    decision = engine.compute_decision(smap, current_speed_mps=8.0, current_timestamp=100.0)

    assert decision.state == HazardState.SAFE.value
    assert decision.risk_level == "LOW"
    assert decision.recommended_action == "MAINTAIN_CRUISE"
    assert decision.avoidance_direction == AvoidanceDirection.CENTER.value
    assert decision.target_speed_kmh == 35.0
    assert decision.is_emergency_stop is False
    assert decision.local_refinement_active is False


def test_caution_state_approaching_hazard() -> None:
    """When obstacle is in forward corridor between 8m and 16m, engine must output CAUTION / REDUCE_SPEED."""
    smap = create_mock_semantic_map([(12.0, 0.0, 2)])  # Vehicle at 12m ahead
    engine = HazardAvoidanceEngine()

    decision = engine.compute_decision(smap, current_speed_mps=8.0, current_timestamp=100.0)

    assert decision.state == HazardState.CAUTION.value
    assert decision.risk_level == "MEDIUM"
    assert decision.recommended_action == "REDUCE_SPEED"
    assert decision.avoidance_direction == AvoidanceDirection.CENTER.value
    assert decision.target_speed_kmh <= 15.0
    assert decision.is_emergency_stop is False
    assert decision.local_refinement_active is True
    assert decision.refined_patch is not None
    assert decision.refined_patch.center_x == pytest.approx(12.0, abs=0.5)


def test_high_risk_avoid_left_when_left_clear() -> None:
    """When obstacle is close (5.0m) and left lane is clear while right is blocked, steer LEFT."""
    smap = create_mock_semantic_map([
        (5.0, 0.0, 2),    # Critical obstacle in center corridor at 5m
        (5.0, -2.4, 2),   # Right lane blocked by another vehicle
        # Left lane (y = +2.4) is free!
    ])
    engine = HazardAvoidanceEngine()

    decision = engine.compute_decision(smap, current_speed_mps=4.0, current_timestamp=100.0)

    assert decision.state == HazardState.HIGH_RISK.value
    assert decision.risk_level == "HIGH"
    assert decision.recommended_action == "AVOID_LEFT"
    assert decision.avoidance_direction == AvoidanceDirection.LEFT.value
    assert decision.target_steer_deg > 0.0
    assert decision.is_emergency_stop is False


def test_high_risk_avoid_right_when_right_clear() -> None:
    """When obstacle is close (5.0m) and right lane is clear while left is blocked, steer RIGHT."""
    smap = create_mock_semantic_map([
        (5.0, 0.0, 2),   # Critical obstacle in center corridor at 5m
        (5.0, 2.4, 6),   # Left lane blocked by wall (y=+2.4)
        # Right lane (y = -2.4) is free!
    ])
    engine = HazardAvoidanceEngine()

    decision = engine.compute_decision(smap, current_speed_mps=4.0, current_timestamp=100.0)

    assert decision.state == HazardState.HIGH_RISK.value
    assert decision.risk_level == "HIGH"
    assert decision.recommended_action == "AVOID_RIGHT"
    assert decision.avoidance_direction == AvoidanceDirection.RIGHT.value
    assert decision.target_steer_deg < 0.0
    assert decision.is_emergency_stop is False


def test_emergency_stop_when_both_lanes_blocked() -> None:
    """When center obstacle is critical (4.5m) and BOTH left and right lanes are blocked, trigger EMERGENCY_STOP."""
    smap = create_mock_semantic_map([
        (4.5, 0.0, 2),   # Center obstacle
        (4.5, 2.4, 6),   # Left blocked by concrete wall
        (4.5, -2.4, 2),  # Right blocked by vehicle
    ])
    engine = HazardAvoidanceEngine()

    decision = engine.compute_decision(smap, current_speed_mps=4.0, current_timestamp=100.0)

    assert decision.state == HazardState.EMERGENCY_STOP.value
    assert decision.risk_level == "CRITICAL"
    assert decision.recommended_action == "EMERGENCY_STOP"
    assert decision.avoidance_direction == AvoidanceDirection.STOP.value
    assert decision.target_speed_kmh == 0.0
    assert decision.is_emergency_stop is True


def test_emergency_stop_critical_proximity() -> None:
    """When obstacle is within critical emergency distance (<3.2m), immediate full stop."""
    smap = create_mock_semantic_map([
        (2.5, 0.0, 3),  # Pedestrian right in front at 2.5m
    ])
    engine = HazardAvoidanceEngine()

    decision = engine.compute_decision(smap, current_speed_mps=3.0, current_timestamp=100.0)

    assert decision.state == HazardState.EMERGENCY_STOP.value
    assert decision.is_emergency_stop is True
    assert decision.target_speed_kmh == 0.0


def test_anti_oscillation_hysteresis() -> None:
    """Verify that an avoidance decision is locked for hysteresis duration to avoid LEFT/RIGHT oscillation."""
    smap = create_mock_semantic_map([
        (5.5, 0.0, 2),  # Center obstacle, both sides initially clear
    ])
    engine = HazardAvoidanceEngine(AvoidanceConfig(hysteresis_lock_duration=2.0))

    # Initial decision at t=10.0
    dec1 = engine.compute_decision(smap, current_speed_mps=4.0, current_timestamp=10.0)
    assert dec1.avoidance_direction in (AvoidanceDirection.LEFT.value, AvoidanceDirection.RIGHT.value)
    initial_dir = dec1.avoidance_direction

    # Step at t=10.5 (within lock period): must retain initial direction
    dec2 = engine.compute_decision(smap, current_speed_mps=4.0, current_timestamp=10.5)
    assert dec2.avoidance_direction == initial_dir

    # Step at t=11.5 (still within 2.0s lock): must retain initial direction
    dec3 = engine.compute_decision(smap, current_speed_mps=4.0, current_timestamp=11.5)
    assert dec3.avoidance_direction == initial_dir
