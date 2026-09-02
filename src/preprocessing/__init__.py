"""LiDAR Preprocessing & Point Cloud Quality Pipeline Module.

Module Owner: Amulya
Responsibilities:
    - Dataset loading and point cloud ingestion
    - Radial range filtering [min_range, max_range]
    - Fast spatial-hash outlier / noise removal
    - Voxel grid downsampling
    - Ground / non-ground geometric separation
    - Standardized PointCloudFrame and PreprocessedPointCloud generation
"""

from src.preprocessing.filters import (
    GroundFilter,
    OutlierFilter,
    RangeFilter,
    VoxelDownsampler,
)
from src.preprocessing.pipeline import PreprocessingPipeline
from src.preprocessing.synthetic import generate_synthetic_scene

__all__ = [
    "GroundFilter",
    "OutlierFilter",
    "PreprocessingPipeline",
    "RangeFilter",
    "VoxelDownsampler",
    "generate_synthetic_scene",
]
