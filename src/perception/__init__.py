"""Semantic Point Cloud Perception Module.

Module Owner: Vedant (src/perception/)
Responsibilities:
    - 3D point cloud semantic segmentation
    - Point-wise semantic class prediction (0..7) and confidence estimation
    - Model compression, ONNX runtime, and inference acceleration
    - Class probability distribution generation
"""

from src.perception.base import BaseSemanticSegmenter
from src.perception.mock import MockSemanticSegmenter

__all__ = [
    "BaseSemanticSegmenter",
    "MockSemanticSegmenter",
]
