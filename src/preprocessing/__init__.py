"""LiDAR Preprocessing & Dataset Pipeline Module.

Module Owner: Amulya (Member 2)

Responsibilities:
    - Dataset loading and point cloud ingestion (KITTI / SemanticKITTI binary, raw arrays)
    - Non-finite (NaN, Inf) point validation and sanitization
    - Euclidean range filtering with exact boundaries
    - Voxel grid downsampling
    - Optional outlier removal (statistical and radius)
    - Coordinate transformations (sensor to ego base frame)
    - Standardized PointCloudFrame generation complying with CONTRACTS.md
    - Synthetic geometric test scene generation for deterministic testing
"""

from src.preprocessing.filters import (
    filter_by_range,
    remove_outliers_radius,
    remove_outliers_statistical,
    transform_coordinates,
    validate_and_sanitize_points,
    voxel_downsample,
)
from src.preprocessing.loaders import (
    load_kitti_bin,
    load_raw_points,
)
from src.preprocessing.pipeline import (
    LiDARPreprocessor,
    PreprocessingConfig,
    PreprocessingMetrics,
    preprocess_frame,
)
from src.preprocessing.synthetic import (
    generate_synthetic_scene,
)

__all__ = [
    # Main Pipeline & Telemetry
    "LiDARPreprocessor",
    "PreprocessingConfig",
    "PreprocessingMetrics",
    "preprocess_frame",
    # Loaders & Ingestion
    "load_kitti_bin",
    "load_raw_points",
    # Filtering & Transform Utilities
    "validate_and_sanitize_points",
    "filter_by_range",
    "voxel_downsample",
    "remove_outliers_statistical",
    "remove_outliers_radius",
    "transform_coordinates",
    # Synthetic Generation (preserves existing exports)
    "generate_synthetic_scene",
]
