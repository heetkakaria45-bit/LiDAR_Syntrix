"""Base interfaces and abstract classes for Semantic Perception.

Module Owner: Vedant (src/perception/)
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

from src.contracts import PointCloudFrame, SemanticPointCloud


class BaseSemanticSegmenter(ABC):
    """Abstract interface for 3D LiDAR point cloud semantic segmentation models.
    
    Subclasses can implement RangeNet++, Cylinder3D, PointNet++, or SparseConv.
    """

    @abstractmethod
    def infer(self, frame: PointCloudFrame) -> SemanticPointCloud:
        """Perform semantic segmentation on an incoming LiDAR frame.

        Args:
            frame: Standardized PointCloudFrame.

        Returns:
            SemanticPointCloud containing per-point class predictions (0..7)
            and normalized confidence scores in [0.0, 1.0].
        """
        pass
