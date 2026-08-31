"""
Semantic Perception Engine Implementation.
Module Owner: Vedant (src/perception/)

Conforms strictly to ISemanticPerception interface:
    PointCloudFrame -> SemanticPerceptionEngine.infer() -> SemanticPointCloud
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np

from src.common.config import SystemConfig, load_config
from src.common.interfaces import ISemanticPerception
from src.common.types import PointCloudFrame, SemanticClass, SemanticPointCloud
from src.perception.models import (
    BaseSemanticModel,
    CalibratedGeometricModelWrapper,
    load_model_from_file,
)


class SemanticPerceptionEngine(ISemanticPerception):
    """
    Semantic Perception Inference Engine.

    Maintains a model-independent interface that seamlessly swaps between
    pretrained deep models, scikit-learn models, and the built-in
    calibrated geometric/statistical classifier.
    """

    def __init__(
        self,
        config: Optional[SystemConfig] = None,
        model: Optional[BaseSemanticModel] = None,
    ) -> None:
        self.config = config or load_config()
        self.model: BaseSemanticModel = model or CalibratedGeometricModelWrapper()
        self._last_inference_latency_ms: float = 0.0

    @property
    def last_inference_latency_ms(self) -> float:
        """Wall-clock time of the latest inference run in milliseconds."""
        return self._last_inference_latency_ms

    def load_model(self, weights_path: str) -> None:
        """
        Loads model checkpoint weights (.joblib, .pkl, .json).
        """
        self.model = load_model_from_file(weights_path)

    def infer(self, frame: PointCloudFrame) -> SemanticPointCloud:
        """
        Executes semantic segmentation inference on input PointCloudFrame.

        Invariants:
            - Validates input shape (N, 3).
            - Preserves point coordinates and point correspondence (output[i] <-> input[i]).
            - Returns semantic class IDs in [0..7] (uint8).
            - Returns confidence scores in [0.0, 1.0] (float32).
            - Handles empty point clouds (N=0) without error.
            - Handles NaNs and Infs safely with fallback confidence.
        """
        if not isinstance(frame, PointCloudFrame):
            raise TypeError(f"Expected PointCloudFrame, got {type(frame)}")

        t0 = time.perf_counter()

        points = frame.points
        N = points.shape[0]

        # Handle empty point cloud
        if N == 0:
            self._last_inference_latency_ms = (time.perf_counter() - t0) * 1000.0
            return SemanticPointCloud(
                points=np.zeros((0, 3), dtype=np.float32),
                semantic_labels=np.zeros(0, dtype=np.uint8),
                confidence=np.zeros(0, dtype=np.float32),
                intensity=np.zeros(0, dtype=np.float32) if frame.intensity is not None else None,
                timestamp=frame.timestamp,
                frame_id=frame.frame_id,
                sensor_pose=frame.sensor_pose.copy(),
            )

        # Check for NaN / Inf coordinates
        valid_mask = np.isfinite(points).all(axis=1)

        if not np.all(valid_mask):
            # Process valid points through model, fill invalid points with fallback
            clean_points = np.where(np.isnan(points) | np.isinf(points), 0.0, points)
            labels, confidence, _ = self.model.predict(clean_points, frame.intensity)

            # Assign OTHER_OBSTACLE with 0.0 confidence for corrupted points
            labels[~valid_mask] = SemanticClass.OTHER_OBSTACLE
            confidence[~valid_mask] = 0.0
        else:
            labels, confidence, _ = self.model.predict(points, frame.intensity)

        # Final contract enforcement
        labels = np.clip(labels, 0, 7).astype(np.uint8)
        confidence = np.clip(confidence, 0.0, 1.0).astype(np.float32)

        self._last_inference_latency_ms = (time.perf_counter() - t0) * 1000.0

        return SemanticPointCloud(
            points=points.copy(),
            semantic_labels=labels,
            confidence=confidence,
            intensity=frame.intensity.copy() if frame.intensity is not None else None,
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            sensor_pose=frame.sensor_pose.copy(),
        )

    def infer_with_probs(
        self, frame: PointCloudFrame
    ) -> Tuple[SemanticPointCloud, np.ndarray]:
        """
        Extended inference returning both the standard SemanticPointCloud and
        the (N, 8) full class probability distribution matrix.
        """
        if not isinstance(frame, PointCloudFrame):
            raise TypeError(f"Expected PointCloudFrame, got {type(frame)}")

        points = frame.points
        N = points.shape[0]

        if N == 0:
            sem_cloud = self.infer(frame)
            return sem_cloud, np.zeros((0, 8), dtype=np.float32)

        valid_mask = np.isfinite(points).all(axis=1)
        clean_points = np.where(np.isnan(points) | np.isinf(points), 0.0, points)
        labels, confidence, probs = self.model.predict(clean_points, frame.intensity)

        if not np.all(valid_mask):
            labels[~valid_mask] = SemanticClass.OTHER_OBSTACLE
            confidence[~valid_mask] = 0.0
            probs[~valid_mask] = 0.0

        sem_cloud = SemanticPointCloud(
            points=points.copy(),
            semantic_labels=labels.astype(np.uint8),
            confidence=confidence.astype(np.float32),
            intensity=frame.intensity.copy() if frame.intensity is not None else None,
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            sensor_pose=frame.sensor_pose.copy(),
        )

        return sem_cloud, probs

    def get_model_metadata(self) -> Dict[str, Any]:
        """Returns diagnostic metadata about the active perception model."""
        meta = self.model.get_metadata()
        meta["last_latency_ms"] = self._last_inference_latency_ms
        return meta
