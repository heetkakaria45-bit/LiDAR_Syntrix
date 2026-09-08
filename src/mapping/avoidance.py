"""Sensor-Grounded Collision Avoidance and Hazard Response State Machine.

Module Owner: Heet (src/mapping/) & Atharva (src/integration/)
Responsibilities:
    - Evaluate deterministic free-space corridor clearance from 2.5D SemanticMap
    - Execute 4-stage hazard state machine: SAFE -> CAUTION -> HIGH_RISK -> EMERGENCY_STOP
    - Select optimal local avoidance direction (LEFT / RIGHT) with anti-oscillation hysteresis
    - Speed-aware risk scaling incorporating vehicle velocity
    - Strict isolation from simulator ground truth: all metrics are derived solely from 2.5D map cells
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.contracts import AvoidanceDecision, GridCell, LocalRefinementPatch, SemanticMap


class HazardState(str, Enum):
    """Canonical 4-stage hazard state machine levels."""

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    HIGH_RISK = "HIGH_RISK"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class AvoidanceDirection(str, Enum):
    """Directional tactical avoidance maneuver commands."""

    CENTER = "CENTER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    STOP = "STOP"


@dataclass
class AvoidanceConfig:
    """Tunable parameters for corridor clearance and avoidance state machine."""

    # Clearance thresholds (meters)
    safe_forward_clearance: float = 16.0
    caution_forward_clearance: float = 8.0
    critical_forward_clearance: float = 3.2
    minimum_lateral_clearance: float = 4.0

    # Corridor geometric boundaries (meters in vehicle frame: X=forward, Y=left)
    center_corridor_half_width: float = 1.35
    left_lane_y_min: float = 1.2
    left_lane_y_max: float = 3.6
    right_lane_y_min: float = -3.6
    right_lane_y_max: float = -1.2
    max_evaluation_distance: float = 50.0

    # Vehicle speed targets (km/h)
    cruise_speed_kmh: float = 35.0
    caution_speed_kmh: float = 15.0
    avoidance_speed_kmh: float = 18.0

    # Steering targets (degrees)
    left_steer_angle_deg: float = 22.0
    right_steer_angle_deg: float = -22.0

    # Anti-oscillation hysteresis (seconds)
    hysteresis_lock_duration: float = 2.0

    # Speed-dependent dynamic margin scaling
    enable_speed_scaling: bool = True
    reaction_time_sec: float = 0.5
    max_deceleration_mps2: float = 4.5


class HazardAvoidanceEngine:
    """Evaluates 2.5D map traversability to compute explainable avoidance decisions."""

    def __init__(self, config: Optional[AvoidanceConfig] = None) -> None:
        self.config = config or AvoidanceConfig()
        self._last_avoidance_dir: AvoidanceDirection = AvoidanceDirection.CENTER
        self._last_decision_time: float = 0.0
        self._locked_until_time: float = 0.0

    def evaluate_corridor_clearance(
        self,
        semantic_map: SemanticMap,
        current_speed_mps: float = 0.0,
    ) -> Tuple[float, float, float, Optional[Tuple[float, float, int]]]:
        """Compute minimum obstacle clearances along forward, left, and right corridors.

        Evaluates solely from 2.5D map cells (Zero Ground-Truth Leakage).

        Args:
            semantic_map: Ingested composite 2.5D SemanticMap.
            current_speed_mps: Current vehicle velocity in m/s.

        Returns:
            Tuple of:
                - forward_clearance: Distance to nearest non-traversable obstacle in center lane (m)
                - left_clearance: Distance to nearest obstacle in left bypass lane (m)
                - right_clearance: Distance to nearest obstacle in right bypass lane (m)
                - closest_obstacle: Optional (cx, cy, semantic_class) of critical obstacle
        """
        cfg = self.config
        max_dist = cfg.max_evaluation_distance

        forward_clearance = max_dist
        left_clearance = max_dist
        right_clearance = max_dist
        closest_obstacle: Optional[Tuple[float, float, int]] = None
        min_forward_dist = max_dist

        # Non-traversable classes: 1 (terrain/sidewalk), 2 (vehicle), 3 (pedestrian),
        # 4 (cyclist), 5 (pole), 6 (wall/building), 7 (obstacle)
        non_traversable_classes = {1, 2, 3, 4, 5, 6, 7}

        for level_name, level_cells in semantic_map.cells.items():
            if not isinstance(level_cells, dict):
                continue

            for _, cell in level_cells.items():
                if not isinstance(cell, GridCell):
                    continue

                cx = cell.cell_x
                cy = cell.cell_y

                # Only evaluate obstacles in front of the vehicle (X > 0.5m)
                if cx <= 0.5 or cx > max_dist:
                    continue

                dist = math.hypot(cx, cy)
                is_obstacle = (
                    cell.semantic_class in non_traversable_classes
                    or cell.occupancy > 0.40
                    or cell.roughness > 0.12
                )

                if not is_obstacle:
                    continue

                # 1. Center Driving Corridor (|Y| <= half_width)
                if abs(cy) <= cfg.center_corridor_half_width:
                    if dist < forward_clearance:
                        forward_clearance = dist
                        if dist < min_forward_dist:
                            min_forward_dist = dist
                            closest_obstacle = (cx, cy, cell.semantic_class)

                # 2. Left Bypass Lane (Y in [1.2, 3.6])
                elif cfg.left_lane_y_min <= cy <= cfg.left_lane_y_max:
                    if dist < left_clearance:
                        left_clearance = dist

                # 3. Right Bypass Lane (Y in [-3.6, -1.2])
                elif cfg.right_lane_y_min <= cy <= cfg.right_lane_y_max:
                    if dist < right_clearance:
                        right_clearance = dist

        return forward_clearance, left_clearance, right_clearance, closest_obstacle

    def compute_decision(
        self,
        semantic_map: SemanticMap,
        current_speed_mps: float = 0.0,
        current_timestamp: Optional[float] = None,
    ) -> AvoidanceDecision:
        """Execute full deterministic hazard state machine and collision avoidance logic.

        Args:
            semantic_map: Composite 2.5D SemanticMap from LiDAR perception.
            current_speed_mps: Current forward speed in m/s.
            current_timestamp: Current timestamp (seconds).

        Returns:
            AvoidanceDecision typed contract.
        """
        cfg = self.config
        now = current_timestamp if current_timestamp is not None else time.time()

        # Dynamic speed scaling margin
        speed_margin = 0.0
        if cfg.enable_speed_scaling and current_speed_mps > 0.1:
            speed_margin = (
                current_speed_mps * cfg.reaction_time_sec
                + (current_speed_mps**2) / (2.0 * cfg.max_deceleration_mps2)
            )

        eff_safe_dist = cfg.safe_forward_clearance + speed_margin * 0.5
        eff_caution_dist = cfg.caution_forward_clearance + speed_margin * 0.3
        eff_crit_dist = cfg.critical_forward_clearance

        (
            fwd_clr,
            left_clr,
            right_clr,
            closest_obs,
        ) = self.evaluate_corridor_clearance(semantic_map, current_speed_mps)

        obs_x = closest_obs[0] if closest_obs else fwd_clr
        obs_y = closest_obs[1] if closest_obs else 0.0
        obs_cls = closest_obs[2] if closest_obs else 0
        obs_dist = float(fwd_clr)

        # State Machine Evaluation
        if fwd_clr >= eff_safe_dist:
            state = HazardState.SAFE
            risk_level = "LOW"
            action = "MAINTAIN_CRUISE"
            direction = AvoidanceDirection.CENTER
            target_speed = cfg.cruise_speed_kmh
            target_steer = 0.0
            is_estop = False
            refinement_active = False
            self._last_avoidance_dir = AvoidanceDirection.CENTER
            self._locked_until_time = 0.0

        elif fwd_clr >= eff_caution_dist:
            state = HazardState.CAUTION
            risk_level = "MEDIUM"
            action = "REDUCE_SPEED"
            direction = AvoidanceDirection.CENTER
            target_speed = cfg.caution_speed_kmh
            target_steer = 0.0
            is_estop = False
            refinement_active = True  # Trigger local foveation refinement at obstacle zone
            self._last_avoidance_dir = AvoidanceDirection.CENTER
            self._locked_until_time = 0.0

        elif fwd_clr >= eff_crit_dist:
            # High Risk: Local Lateral Avoidance
            state = HazardState.HIGH_RISK
            risk_level = "HIGH"
            refinement_active = True

            # Evaluate lateral free-space availability:
            # A bypass lane is safe if its obstacle distance is greater than the center obstacle distance + clearance buffer
            required_lateral_clearance = max(cfg.minimum_lateral_clearance, fwd_clr + 2.0)
            left_safe = left_clr >= required_lateral_clearance
            right_safe = right_clr >= required_lateral_clearance

            # Anti-oscillation hysteresis check
            in_hysteresis_lock = (
                now < self._locked_until_time
                and self._last_avoidance_dir in (AvoidanceDirection.LEFT, AvoidanceDirection.RIGHT)
            )

            if in_hysteresis_lock:
                # Maintain locked direction unless chosen side is critically blocked
                if self._last_avoidance_dir == AvoidanceDirection.LEFT and left_safe:
                    direction = AvoidanceDirection.LEFT
                elif self._last_avoidance_dir == AvoidanceDirection.RIGHT and right_safe:
                    direction = AvoidanceDirection.RIGHT
                else:
                    # Locked side is blocked; reassess immediately
                    in_hysteresis_lock = False

            if not in_hysteresis_lock:
                if left_safe and right_safe:
                    # Both sides clear: choose the side with greater clearance
                    if left_clr >= right_clr:
                        direction = AvoidanceDirection.LEFT
                    else:
                        direction = AvoidanceDirection.RIGHT
                    self._last_avoidance_dir = direction
                    self._locked_until_time = now + cfg.hysteresis_lock_duration
                elif left_safe:
                    direction = AvoidanceDirection.LEFT
                    self._last_avoidance_dir = direction
                    self._locked_until_time = now + cfg.hysteresis_lock_duration
                elif right_safe:
                    direction = AvoidanceDirection.RIGHT
                    self._last_avoidance_dir = direction
                    self._locked_until_time = now + cfg.hysteresis_lock_duration
                else:
                    # Both sides blocked: Fallback to Emergency Stop
                    state = HazardState.EMERGENCY_STOP
                    risk_level = "CRITICAL"
                    direction = AvoidanceDirection.STOP


            if direction == AvoidanceDirection.LEFT:
                action = "AVOID_LEFT"
                target_speed = cfg.avoidance_speed_kmh
                target_steer = cfg.left_steer_angle_deg
                is_estop = False
            elif direction == AvoidanceDirection.RIGHT:
                action = "AVOID_RIGHT"
                target_speed = cfg.avoidance_speed_kmh
                target_steer = cfg.right_steer_angle_deg
                is_estop = False
            else:
                action = "EMERGENCY_STOP"
                target_speed = 0.0
                target_steer = 0.0
                is_estop = True

        else:
            # Critical Distance or Complete Blockage
            state = HazardState.EMERGENCY_STOP
            risk_level = "CRITICAL"
            action = "EMERGENCY_STOP"
            direction = AvoidanceDirection.STOP
            target_speed = 0.0
            target_steer = 0.0
            is_estop = True
            refinement_active = True
            self._last_avoidance_dir = AvoidanceDirection.STOP

        refined_patch: Optional[LocalRefinementPatch] = None
        if refinement_active and closest_obs:
            refined_patch = LocalRefinementPatch(
                center_x=obs_x,
                center_y=obs_y,
                radius=2.5,
                target_resolution=0.10 if obs_dist < 25.0 else 0.10,
                source_ring_name="mid" if obs_dist < 50.0 else "far",
                target_ring_name="mid_near",
            )

        return AvoidanceDecision(
            state=state.value,
            obstacle_distance=float(obs_dist),
            obstacle_lateral_pos=float(obs_y),
            obstacle_class=int(obs_cls),
            risk_level=risk_level,
            recommended_action=action,
            avoidance_direction=direction.value,
            target_speed_kmh=float(target_speed),
            target_steer_deg=float(target_steer),
            left_clearance=float(left_clr),
            right_clearance=float(right_clr),
            forward_clearance=float(fwd_clr),
            is_emergency_stop=is_estop,
            local_refinement_active=refinement_active,
            refined_patch=refined_patch,
            timestamp=now,
        )
