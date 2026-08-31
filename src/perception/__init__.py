"""
Semantic Perception Package.
Module Owner: Vedant (src/perception/)

Exports:
    - SemanticPerceptionEngine: Main perception pipeline inference engine.
    - PointCloudFeatureExtractor: Vectorized 3D geometric feature extractor.
    - CalibratedGeometricClassifier: Vectorized probabilistic semantic classifier.
    - BaseSemanticModel, CalibratedGeometricModelWrapper, GenericSklearnModelWrapper: Model wrappers.
    - SemanticKITTIAdapter, NuScenesAdapter, WaymoDatasetAdapter, get_adapter: Dataset adapters.
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
]
