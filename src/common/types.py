"""
Core Data Contracts and Types for Foveated Semantic 2.5D LiDAR Mapping.

FROZEN COORDINATE SYSTEM:
    X = forward (meters)
    Y = left    (meters)
    Z = up      (meters)

FROZEN SEMANTIC TAXONOMY:
    0 = DRIVABLE_GROUND
    1 = NON_DRIVABLE_TERRAIN
    2 = VEHICLE
    3 = PEDESTRIAN
    4 = CYCLIST
    5 = POLE
    6 = WALL_BUILDING
    7 = OTHER_OBSTACLE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class CoordinateSystem(IntEnum):
    """Coordinate frame convention: FLU (Forward-Left-Up)."""
    FORWARD_LEFT_UP = 1


class SemanticClass(IntEnum):
    """
    Frozen Semantic Taxonomy (8 classes).
    All dataset adapters MUST map external annotations onto this taxonomy.
    """
    DRIVABLE_GROUND = 0
    NON_DRIVABLE_TERRAIN = 1
    VEHICLE = 2
    PEDESTRIAN = 3
    CYCLIST = 4
    POLE = 5
    WALL_BUILDING = 6
    OTHER_OBSTACLE = 7

    @classmethod
    def get_name(cls, class_id: int) -> str:
        try:
            return cls(class_id).name
        except ValueError:
            return f"UNKNOWN_{class_id}"

    @classmethod
    def is_ground(cls, class_id: int) -> bool:
        return class_id in (cls.DRIVABLE_GROUND, cls.NON_DRIVABLE_TERRAIN)

    @classmethod
    def is_obstacle(cls, class_id: int) -> bool:
        return class_id not in (cls.DRIVABLE_GROUND,)


@dataclass(frozen=True)
class FoveationLevelConfig:
    """Configuration contract for a single foveation zone."""
    level: int
    min_radius_m: float
    max_radius_m: float
    cell_resolution_m: float
    description: str = ""

    def contains_distance(self, distance_m: float, is_outermost: bool = False) -> bool:
        """
        Check if distance falls within [min_radius_m, max_radius_m) or
        [min_radius_m, max_radius_m] for the outermost boundary.
        """
        if is_outermost:
            return self.min_radius_m <= distance_m <= self.max_radius_m
        return self.min_radius_m <= distance_m < self.max_radius_m


@dataclass
class PointCloudFrame:
    """
    Standard Raw/Preprocessed Point Cloud Frame Contract.

    Attributes:
        points: (N, 3) ndarray of float32/float64 (X=forward, Y=left, Z=up in meters).
        intensity: Optional (N,) or (N, 1) ndarray of float32 LiDAR return intensity.
        timestamp: Timestamp in seconds (float64) or nanoseconds.
        frame_id: Monotonically increasing or dataset frame identifier.
        sensor_pose: 4x4 homogeneous transformation matrix in map/world frame.
    """
    points: np.ndarray
    intensity: Optional[np.ndarray] = None
    timestamp: float = 0.0
    frame_id: Union[int, str] = 0
    sensor_pose: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))

    def __post_init__(self) -> None:
        if not isinstance(self.points, np.ndarray):
            self.points = np.asarray(self.points, dtype=np.float32)
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"PointCloudFrame points must have shape (N, 3), got {self.points.shape}")
        if self.intensity is not None:
            if not isinstance(self.intensity, np.ndarray):
                self.intensity = np.asarray(self.intensity, dtype=np.float32)
            if self.intensity.shape[0] != self.points.shape[0]:
                raise ValueError(
                    f"Intensity length {self.intensity.shape[0]} does not match points length {self.points.shape[0]}"
                )
        if not isinstance(self.sensor_pose, np.ndarray) or self.sensor_pose.shape != (4, 4):
            raise ValueError(f"sensor_pose must be a (4, 4) transformation matrix, got {self.sensor_pose.shape}")

    @property
    def num_points(self) -> int:
        return self.points.shape[0]


@dataclass
class SemanticPointCloud:
    """
    Semantic Point Cloud Contract (output of Perception, input to Foveated Mapping).

    Attributes:
        points: (N, 3) ndarray of coordinates (X=forward, Y=left, Z=up in meters).
        semantic_labels: (N,) ndarray of uint8 semantic class IDs (0-7).
        confidence: (N,) ndarray of float32 confidence scores [0.0, 1.0].
        intensity: Optional (N,) ndarray of intensities.
        timestamp: Timestamp in seconds.
        frame_id: Frame identifier.
        sensor_pose: 4x4 homogeneous transformation matrix.
    """
    points: np.ndarray
    semantic_labels: np.ndarray
    confidence: np.ndarray
    intensity: Optional[np.ndarray] = None
    timestamp: float = 0.0
    frame_id: Union[int, str] = 0
    sensor_pose: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))

    def __post_init__(self) -> None:
        if not isinstance(self.points, np.ndarray):
            self.points = np.asarray(self.points, dtype=np.float32)
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"SemanticPointCloud points must have shape (N, 3), got {self.points.shape}")

        N = self.points.shape[0]
        if not isinstance(self.semantic_labels, np.ndarray):
            self.semantic_labels = np.asarray(self.semantic_labels, dtype=np.uint8)
        if self.semantic_labels.shape[0] != N:
            raise ValueError(f"semantic_labels length {self.semantic_labels.shape[0]} != points count {N}")

        if not isinstance(self.confidence, np.ndarray):
            self.confidence = np.asarray(self.confidence, dtype=np.float32)
        if self.confidence.shape[0] != N:
            raise ValueError(f"confidence length {self.confidence.shape[0]} != points count {N}")

        if self.intensity is not None:
            if not isinstance(self.intensity, np.ndarray):
                self.intensity = np.asarray(self.intensity, dtype=np.float32)
            if self.intensity.shape[0] != N:
                raise ValueError(f"intensity length {self.intensity.shape[0]} != points count {N}")

    @property
    def num_points(self) -> int:
        return self.points.shape[0]


@dataclass
class GridCell:
    """
    Semantic 2.5D Foveated Grid Cell Contract.

    Represents a spatial column (XY cell) containing elevation, semantics, and traversability.

    Core fields:
        resolution_level: Foveation level index (0, 1, 2, 3).
        cell_index: Discrete integer grid indices (ix, iy).
        position: Continuous center coordinates (center_x, center_y) in meters.
        elevation: Mean or estimated ground elevation Z in meters.
        min_z: Minimum Z value observed in the cell column.
        max_z: Maximum Z value observed in the cell column.
        semantic_class: Dominant semantic class ID (0-7).
        semantic_confidence: Confidence score of dominant semantic classification [0.0, 1.0].
        occupancy: Occupancy probability [0.0, 1.0] or state.
        point_count: Number of points aggregated within this cell.
        roughness: Surface roughness (e.g. variance of Z, plane residual) in meters.
        timestamp: Timestamp of the latest update.

    Future extension fields:
        velocity: Optional 3D velocity vector (vx, vy, vz) for dynamic objects.
        observation_count: Cumulative number of observations over temporal frames.
        uncertainty: Elevation or spatial uncertainty.
        semantic_probs: Optional full class probability distribution vector (length 8).
    """
    resolution_level: int
    cell_index: Tuple[int, int]
    position: Tuple[float, float]
    elevation: float
    min_z: float
    max_z: float
    semantic_class: int
    semantic_confidence: float
    occupancy: float
    point_count: int
    roughness: float
    timestamp: float

    # Future extension points
    velocity: Optional[Tuple[float, float, float]] = None
    observation_count: int = 1
    uncertainty: float = 0.0
    semantic_probs: Optional[List[float]] = None

    @property
    def height_span(self) -> float:
        """Vertical height extent in meters."""
        return self.max_z - self.min_z


@dataclass
class TraversabilityScore:
    """Traversability evaluation result for a cell or navigation query."""
    is_traversable: bool
    cost: float  # [0.0 = completely free/optimal, 1.0 = lethal obstacle]
    slope_rad: float = 0.0
    step_height_m: float = 0.0
    roughness_m: float = 0.0
    semantic_penalty: float = 0.0


@dataclass
class SemanticMap:
    """
    Foveated Semantic 2.5D Map Container Contract.

    Represents the active aggregate map state without locking internal spatial indexing.
    """
    cells: Dict[Tuple[int, int, int], GridCell] = field(default_factory=dict)
    # Key convention: (resolution_level, grid_ix, grid_iy) -> GridCell
    resolution_levels: List[FoveationLevelConfig] = field(default_factory=list)
    sensor_pose: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))
    timestamp: float = 0.0
    frame_id: Union[int, str] = 0

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    def get_cell(self, level: int, ix: int, iy: int) -> Optional[GridCell]:
        return self.cells.get((level, ix, iy))


@dataclass
class TelemetryMetrics:
    """
    Performance and System Health Telemetry Contract.
    Zero-fabrication contract: All values must stem from physical timer measurements.
    """
    preprocessing_latency_ms: float = 0.0
    inference_latency_ms: float = 0.0
    projection_latency_ms: float = 0.0
    mapping_latency_ms: float = 0.0
    rendering_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    fps: float = 0.0
    ram_usage_mb: float = 0.0
    vram_usage_mb: float = 0.0
    input_point_count: int = 0
    grid_cell_count: int = 0
    timestamp: float = 0.0
