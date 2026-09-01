"""Core Shared Data Contracts.

This module defines lightweight, typed data schemas for data exchange between
the independent pipeline modules:
    - Preprocessing  -> PointCloudFrame
    - Perception     -> SemanticPointCloud
    - Foveated Grid  -> Spatial Indexing & Cell Coordinates
    - Mapping        -> GridCell & SemanticMap
    - Integration    -> Pipeline Orchestration
    - Evaluation     -> Benchmark Inputs & Metric Outputs

IMPORTANT:
    These structures are the shared contracts across the team.
    Any breaking changes must follow the RFC procedure defined in CONTRACTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np


@dataclass
class PreprocessingStats:
    """Quantitative execution statistics for the point cloud preprocessing pipeline."""

    raw_points: int
    range_filtered_points: int
    outlier_filtered_points: int
    voxel_downsampled_points: int
    ground_points: int
    non_ground_points: int
    processing_time_ms: float
    reduction_percentage: float


@dataclass
class PreprocessedPointCloud:
    """Preprocessed and validated LiDAR frame with ground/non-ground separation.

    Produced by: src/preprocessing/ (Owner: Amulya)
    Consumed by: src/perception/ and downstream mapping
    """

    points: np.ndarray  # Shape: (N, 3), dtype: float32
    ground_mask: np.ndarray  # Shape: (N,), dtype: bool (True=Ground, False=Non-Ground)
    timestamp: float
    frame_id: str
    stats: PreprocessingStats
    intensity: Optional[np.ndarray] = None  # Shape: (N,), dtype: float32
    sensor_pose: np.ndarray = field(
        default_factory=lambda: np.eye(4, dtype=np.float64)
    )

    def __post_init__(self) -> None:
        if not isinstance(self.points, np.ndarray):
            self.points = np.asarray(self.points, dtype=np.float32)
        if not isinstance(self.ground_mask, np.ndarray):
            self.ground_mask = np.asarray(self.ground_mask, dtype=bool)

        num_points = self.points.shape[0]
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"points must have shape (N, 3), got {self.points.shape}")
        if self.ground_mask.shape != (num_points,):
            raise ValueError(
                f"ground_mask shape {self.ground_mask.shape} does not match N={num_points}"
            )
        if self.intensity is not None:
            if not isinstance(self.intensity, np.ndarray):
                self.intensity = np.asarray(self.intensity, dtype=np.float32)
            if self.intensity.shape != (num_points,):
                raise ValueError(
                    f"intensity shape {self.intensity.shape} does not match N={num_points}"
                )

    @property
    def ground_points(self) -> np.ndarray:
        """Slice of points classified as ground."""
        return self.points[self.ground_mask]

    @property
    def non_ground_points(self) -> np.ndarray:
        """Slice of points classified as non-ground / obstacles."""
        return self.points[~self.ground_mask]


@dataclass
class PointCloudFrame:
    """Standardized ingested raw or filtered LiDAR frame.

    Coordinate system:
        X = Forward
        Y = Left
        Z = Up
    Units: Meters
    """

    points: np.ndarray  # Shape: (N, 3), dtype: float32
    timestamp: float
    frame_id: str
    intensity: Optional[np.ndarray] = None  # Shape: (N,), dtype: float32
    sensor_pose: np.ndarray = field(
        default_factory=lambda: np.eye(4, dtype=np.float64)
    )  # 4x4 transformation matrix [R | t]

    def __post_init__(self) -> None:
        if not isinstance(self.points, np.ndarray):
            self.points = np.asarray(self.points, dtype=np.float32)
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"points array must have shape (N, 3), got {self.points.shape}")
        if self.intensity is not None:
            if not isinstance(self.intensity, np.ndarray):
                self.intensity = np.asarray(self.intensity, dtype=np.float32)
            if self.intensity.ndim != 1 or self.intensity.shape[0] != self.points.shape[0]:
                raise ValueError(
                    f"intensity array must have shape (N,), got {self.intensity.shape} "
                    f"for points of length {self.points.shape[0]}"
                )


@dataclass
class SemanticPointCloud:
    """Point cloud with per-point semantic predictions and confidence scores.

    Produced by: src/perception/ (Owner: Vedant)
    Consumed by: src/foveated_grid/ and src/mapping/
    """

    points: np.ndarray  # Shape: (N, 3), dtype: float32
    semantic_class: np.ndarray  # Shape: (N,), dtype: integer class ID (0..7)
    confidence: np.ndarray  # Shape: (N,), dtype: float32 in [0.0, 1.0]
    timestamp: float
    frame_id: str
    intensity: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        if not isinstance(self.points, np.ndarray):
            self.points = np.asarray(self.points, dtype=np.float32)
        if not isinstance(self.semantic_class, np.ndarray):
            self.semantic_class = np.asarray(self.semantic_class, dtype=np.int32)
        if not isinstance(self.confidence, np.ndarray):
            self.confidence = np.asarray(self.confidence, dtype=np.float32)

        num_points = self.points.shape[0]
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"points must have shape (N, 3), got {self.points.shape}")
        if self.semantic_class.shape != (num_points,):
            raise ValueError(
                f"semantic_class shape {self.semantic_class.shape} does not match N={num_points}"
            )
        if self.confidence.shape != (num_points,):
            raise ValueError(
                f"confidence shape {self.confidence.shape} does not match N={num_points}"
            )


@dataclass
class GridCell:
    """A single cell within a 2.5D multi-resolution semantic grid.

    Produced by: src/mapping/ (Owner: Heet)
    Spatial indexing managed by: src/foveated_grid/ (Owner: Manashri)
    """

    resolution_level: str  # e.g. "near", "mid_near", "mid", "far" or level index
    cell_x: float  # Center X coordinate in map/base frame (meters)
    cell_y: float  # Center Y coordinate in map/base frame (meters)
    elevation: float  # Nominal surface elevation Z
    min_z: float  # Minimum Z observed in cell
    max_z: float  # Maximum Z observed in cell
    semantic_class: int  # Aggregated semantic class ID (0..7)
    confidence: float  # Aggregated semantic confidence [0.0, 1.0]
    occupancy: float  # Occupancy probability [0.0, 1.0]
    point_count: int  # Number of raw LiDAR points falling in cell
    roughness: float  # Terrain surface roughness / height variance
    timestamp: float  # Timestamp of latest update

    # Extended attributes for temporal filtering, dynamic tracking & adaptive refinement
    velocity: Optional[Tuple[float, float, float]] = None  # (vx, vy, vz) in m/s
    observation_count: int = 1  # Number of temporal observations
    uncertainty: float = 0.0  # Elevation or semantic entropy uncertainty [0.0, 1.0]
    semantic_probabilities: Optional[np.ndarray] = None  # Full 8-class probability distribution


@dataclass
class SemanticMap:
    """Complete multi-resolution 2.5D Semantic Elevation Map.

    Produced by: src/mapping/ (Owner: Heet)
    Visualized by: src/visualization/ (Owner: Atharva)
    Evaluated by: src/evaluation/ (Owner: Himisha)
    """

    cells: Dict[str, Any]  # Map representation (e.g. dict of level -> cell array/sparse index)
    resolution_levels: Dict[str, Any]  # Active resolution definitions
    sensor_pose: np.ndarray  # 4x4 current sensor pose
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetLabelMap:
    """Helper to map dataset-specific integer labels to project semantic classes (0..7)."""

    mapping_dict: Dict[int, int]
    default_unmapped_class: int = 7  # Default to OTHER_OBSTACLE

    def map_labels(self, raw_labels: np.ndarray) -> np.ndarray:
        """Map raw dataset label array to project class ID array."""
        project_labels = np.full_like(raw_labels, self.default_unmapped_class, dtype=np.int32)
        for raw_id, proj_id in self.mapping_dict.items():
            project_labels[raw_labels == raw_id] = proj_id
        return project_labels


@dataclass
class SyntheticSceneConfig:
    """Configuration for deterministic synthetic geometric test scene generation."""

    scene_type: str = "flat_road"  # e.g., "flat_road", "curb", "pothole", "slope", "overhang"
    num_points: int = 5000
    noise_std: float = 0.01  # Gaussian sensor noise in meters
    road_width: float = 8.0
    curb_height: float = 0.15  # 15 cm step
    pothole_depth: float = 0.08  # 8 cm depression
    slope_deg: float = 10.0  # 10 degrees incline
    seed: int = 42
