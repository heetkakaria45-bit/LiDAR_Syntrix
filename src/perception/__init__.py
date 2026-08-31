<<<<<<< HEAD
"""Point Cloud Perception & Semantic Segmentation Module.

Module Owner: Vedant
Responsibilities:
    - Point cloud semantic segmentation architectures
    - Model training, checkpoints, and inference pipelines
    - Per-point semantic class prediction and probability distributions
    - Prediction confidence score estimation
    - Model optimization (quantization, pruning, ONNX runtime export)
"""

__all__ = []
=======
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
>>>>>>> 99fc3d8 (feat(perception): implement semantic perception pipeline, features, calibrated classifier, and dataset adapters)
