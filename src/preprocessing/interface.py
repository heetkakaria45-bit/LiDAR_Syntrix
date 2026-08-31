"""
LiDAR Preprocessing Interface Scaffolding.
Module Owner: Amulya (src/preprocessing/)

Responsibility:
    - Ingest raw LiDAR frames (PointCloudFrame).
    - Remove invalid/NaN/Inf points.
    - Crop point cloud to operational range (-100m to +100m).
    - Remove ego-vehicle reflections / footprint noise.
    - Output normalized, clean PointCloudFrame.
"""

from __future__ import annotations

from typing import Optional
from src.common.config import SystemConfig, load_config
from src.common.interfaces import IPreprocessor
from src.common.types import PointCloudFrame


class LiDARPreprocessor(IPreprocessor):
    """
    Core Preprocessor implementation scaffold.
    To be fully implemented by Amulya in Phase B/C.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def process(self, raw_frame: PointCloudFrame) -> PointCloudFrame:
        """
        Executes point cloud cleaning and range cropping.
        Note: Full algorithmic implementation scheduled for Phase B/C.
        """
        if not isinstance(raw_frame, PointCloudFrame):
            raise TypeError(f"Expected PointCloudFrame, got {type(raw_frame)}")
        return raw_frame

    def downsample(self, frame: PointCloudFrame, voxel_size_m: float) -> PointCloudFrame:
        """
        Executes voxel downsampling.
        Note: Full algorithmic implementation scheduled for Phase B/C.
        """
        if voxel_size_m <= 0:
            raise ValueError(f"voxel_size_m must be positive, got {voxel_size_m}")
        return frame
