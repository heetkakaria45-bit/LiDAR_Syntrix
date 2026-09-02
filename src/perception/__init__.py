"""Semantic Point Cloud Perception Module.

Module Owner: Vedant (src/perception/)
Responsibilities:
    - 3D point cloud semantic segmentation
    - Point-wise semantic class prediction (0..7) and confidence estimation
    - Model compression, ONNX runtime, and inference acceleration
    - Class probability distribution generation
"""

from src.perception.interface import SemanticPerceptionEngine
from src.perception.features import PointCloudFeatureExtractor
from src.perception.classifier import CalibratedGeometricClassifier, softmax
from src.perception.models import (
    BaseSemanticModel,
    CalibratedGeometricModelWrapper,
    GenericSklearnModelWrapper,
    load_model_from_file,
)
from src.perception.adapters import (
    BaseDatasetAdapter,
    SemanticKITTIAdapter,
    NuScenesAdapter,
    WaymoDatasetAdapter,
    get_adapter,
)
from src.perception.base import BaseSemanticSegmenter
from src.perception.mock import MockSemanticSegmenter

__all__ = [
    "SemanticPerceptionEngine",
    "PointCloudFeatureExtractor",
    "CalibratedGeometricClassifier",
    "softmax",
    "BaseSemanticModel",
    "CalibratedGeometricModelWrapper",
    "GenericSklearnModelWrapper",
    "load_model_from_file",
    "BaseDatasetAdapter",
    "SemanticKITTIAdapter",
    "NuScenesAdapter",
    "WaymoDatasetAdapter",
    "get_adapter",
    "BaseSemanticSegmenter",
    "MockSemanticSegmenter",
]
