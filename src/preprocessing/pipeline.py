"""LiDAR Preprocessing Pipeline Orchestrator & Telemetry.

Module Owner: Amulya (Preprocessing)

Provides:
    - PreprocessingConfig: Typed configuration data class
    - PreprocessingMetrics: Runtime performance instrumentation (points, latency, reduction)
    - LiDARPreprocessor: Pipeline class executing validation, filtering, downsampling,
      outlier removal, and coordinate transformation
    - preprocess_frame: Functional entry point for simple one-line handoff
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import yaml

from src.contracts import PointCloudFrame
from src.preprocessing.filters import (
    filter_by_range,
    remove_outliers_statistical,
    transform_coordinates,
    validate_and_sanitize_points,
    voxel_downsample,
)


@dataclass
class PreprocessingConfig:
    """Configuration parameters for the LiDAR preprocessing pipeline.

    Attributes:
        min_range: Minimum Euclidean distance in meters (default: 0.5m).
        max_range: Maximum Euclidean distance in meters (default: 100.0m).
        range_filter_enabled: Whether to apply range filtering.
        voxel_downsample_enabled: Whether to apply voxel grid downsampling.
        voxel_leaf_size: Voxel cube edge length in meters.
        outlier_removal_enabled: Whether to apply statistical outlier removal.
        outlier_nb_neighbors: k-nearest neighbors for outlier estimation.
        outlier_std_ratio: Standard deviation multiplier threshold.
        coordinate_transform: Optional 4x4 matrix for sensor-to-base transformation.
    """

    min_range: float = 0.5
    max_range: float = 100.0
    range_filter_enabled: bool = True
    voxel_downsample_enabled: bool = False
    voxel_leaf_size: float = 0.05
    outlier_removal_enabled: bool = False
    outlier_nb_neighbors: int = 20
    outlier_std_ratio: float = 2.0
    coordinate_transform: Optional[np.ndarray] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PreprocessingConfig:
        """Create configuration from dictionary (e.g. parsed YAML)."""
        prep = d.get("preprocessing", d)
        range_cfg = prep.get("range_filter", {})
        outlier_cfg = prep.get("outlier_removal", {})
        voxel_cfg = prep.get("voxel_downsample", {})

        return cls(
            min_range=float(range_cfg.get("min_range", 0.5)),
            max_range=float(range_cfg.get("max_range", 100.0)),
            range_filter_enabled=bool(range_cfg.get("enabled", True)),
            voxel_downsample_enabled=bool(voxel_cfg.get("enabled", False)),
            voxel_leaf_size=float(voxel_cfg.get("leaf_size", 0.05)),
            outlier_removal_enabled=bool(outlier_cfg.get("enabled", False)),
            outlier_nb_neighbors=int(outlier_cfg.get("nb_neighbors", 20)),
            outlier_std_ratio=float(outlier_cfg.get("std_ratio", 2.0)),
        )

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> PreprocessingConfig:
        """Load configuration from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class PreprocessingMetrics:
    """Runtime execution metrics collected during preprocessing.

    All metrics are measured from actual execution.

    Attributes:
        input_points: Number of points before preprocessing.
        output_points: Number of points after preprocessing.
        latency_ms: Preprocessing elapsed wall-clock time in milliseconds.
        reduction_ratio: Fraction of points removed, (input - output) / input.
                         Equals 0.0 when input_points is 0.
        downsample_ratio: output_points / input_points (retention factor).
    """

    input_points: int
    output_points: int
    latency_ms: float
    reduction_ratio: float
    downsample_ratio: float


class LiDARPreprocessor:
    """Production entry point for LiDAR point cloud preprocessing.

    Orchestrates:
        1. Validation & sanitization (removes NaN/Inf coordinates)
        2. Euclidean range filtering (clips to [min_range, max_range])
        3. Optional statistical outlier removal
        4. Optional voxel grid downsampling
        5. Coordinate normalization (sensor to vehicle base frame)
        6. Standardized PointCloudFrame creation complying with CONTRACTS.md
    """

    def __init__(self, config: Optional[PreprocessingConfig] = None) -> None:
        self.config = config if config is not None else PreprocessingConfig()

    @classmethod
    def from_config_file(cls, config_path: Union[str, Path]) -> LiDARPreprocessor:
        """Instantiate preprocessor from project configuration file."""
        cfg = PreprocessingConfig.from_yaml(config_path)
        return cls(config=cfg)

    def preprocess(
        self, frame: PointCloudFrame
    ) -> Tuple[PointCloudFrame, PreprocessingMetrics]:
        """Execute the full preprocessing pipeline on an input PointCloudFrame.

        Args:
            frame: Input PointCloudFrame instance.

        Returns:
            processed_frame: Standardized PointCloudFrame ready for downstream perception.
            metrics: Actual measured execution telemetry.
        """
        start_time = time.perf_counter()

        raw_points = frame.points
        raw_intensity = frame.intensity
        input_count = raw_points.shape[0]

        # Stage 1: Validation & Sanitization (drop NaN, Inf)
        pts, intensity = validate_and_sanitize_points(raw_points, raw_intensity)

        # Stage 2: Euclidean Range Filtering
        if self.config.range_filter_enabled and pts.shape[0] > 0:
            pts, intensity = filter_by_range(
                pts,
                intensity,
                min_range=self.config.min_range,
                max_range=self.config.max_range,
            )

        # Stage 3: Optional Outlier Removal
        if self.config.outlier_removal_enabled and pts.shape[0] > 0:
            pts, intensity = remove_outliers_statistical(
                pts,
                intensity,
                nb_neighbors=self.config.outlier_nb_neighbors,
                std_ratio=self.config.outlier_std_ratio,
            )

        # Stage 4: Optional Voxel Downsampling
        if self.config.voxel_downsample_enabled and pts.shape[0] > 0:
            pts, intensity = voxel_downsample(
                pts,
                intensity,
                leaf_size=self.config.voxel_leaf_size,
            )

        # Stage 5: Coordinate Normalization / Transformation
        if self.config.coordinate_transform is not None and pts.shape[0] > 0:
            pts = transform_coordinates(pts, self.config.coordinate_transform)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        output_count = pts.shape[0]

        if input_count > 0:
            reduction_ratio = float((input_count - output_count) / input_count)
            downsample_ratio = float(output_count / input_count)
        else:
            reduction_ratio = 0.0
            downsample_ratio = 1.0

        metrics = PreprocessingMetrics(
            input_points=input_count,
            output_points=output_count,
            latency_ms=elapsed_ms,
            reduction_ratio=reduction_ratio,
            downsample_ratio=downsample_ratio,
        )

        processed_frame = PointCloudFrame(
            points=pts,
            intensity=intensity,
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            sensor_pose=frame.sensor_pose,
        )

        return processed_frame, metrics


def preprocess_frame(
    frame: PointCloudFrame,
    config: Optional[PreprocessingConfig] = None,
) -> PointCloudFrame:
    """Convenience function to preprocess a PointCloudFrame in a single call.

    Args:
        frame: Input PointCloudFrame.
        config: Optional custom PreprocessingConfig. If omitted, uses default config.

    Returns:
        processed_frame: Standardized PointCloudFrame.
    """
    preprocessor = LiDARPreprocessor(config=config)
    processed_frame, _ = preprocessor.preprocess(frame)
    return processed_frame
