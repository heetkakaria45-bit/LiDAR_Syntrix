"""LiDAR Preprocessing & Dataset Pipeline Module.

Module Owner: Amulya
Responsibilities:
    - Dataset loading and point cloud ingestion
    - Outlier filtering and noise removal
    - Downsampling / voxel grid decimation
    - Coordinate transformations (sensor to base/map frames)
    - Standardized PointCloudFrame generation complying with CONTRACTS.md
    - Synthetic geometric test scene generation for deterministic testing
"""

from src.preprocessing.filters import validate_and_sanitize_points
from src.preprocessing.synthetic import generate_synthetic_scene

__all__ = [
    "generate_synthetic_scene",
    "validate_and_sanitize_points",
]
