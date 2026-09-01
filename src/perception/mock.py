"""Mock and Heuristic Semantic Segmentation models for rapid testing.

Allows downstream developers (Manashri, Heet, Atharva, Himisha) to run the full pipeline
without waiting for neural network training or heavy GPU dependencies.
"""

from typing import Optional
import numpy as np

from src.contracts import PointCloudFrame, SemanticPointCloud
from src.perception.base import BaseSemanticSegmenter


class MockSemanticSegmenter(BaseSemanticSegmenter):
    """Mock semantic segmenter assigning ground truth or deterministic geometric classes."""

    def __init__(self, default_confidence: float = 0.95, ground_threshold_z: float = 0.15):
        self.default_confidence = float(np.clip(default_confidence, 0.0, 1.0))
        self.ground_threshold_z = ground_threshold_z

    def infer(self, frame: PointCloudFrame) -> SemanticPointCloud:
        """Infer classes using a simple geometric heuristic if raw, or preserve ground truth."""
        points = frame.points
        n_points = points.shape[0]

        if n_points == 0:
            return SemanticPointCloud(
                points=points,
                semantic_class=np.zeros((0,), dtype=np.int32),
                confidence=np.zeros((0,), dtype=np.float32),
                timestamp=frame.timestamp,
                frame_id=frame.frame_id,
                intensity=frame.intensity,
            )

        # Simple fast geometric heuristic:
        # z <= ground_threshold_z -> DRIVABLE_GROUND (0)
        # z > ground_threshold_z and height < 2.0 -> VEHICLE / PEDESTRIAN / OBSTACLE
        # height > 2.0 -> WALL_BUILDING (6)
        classes = np.zeros((n_points,), dtype=np.int32)
        z = points[:, 2]
        
        # Ground classification
        classes[z <= self.ground_threshold_z] = 0  # DRIVABLE_GROUND
        
        # Low-medium obstacles
        obstacle_mask = (z > self.ground_threshold_z) & (z < 2.0)
        classes[obstacle_mask] = 2  # VEHICLE / OBSTACLE
        
        # High obstacles / structures
        high_mask = z >= 2.0
        classes[high_mask] = 6  # WALL_BUILDING

        confidences = np.full((n_points,), self.default_confidence, dtype=np.float32)

        return SemanticPointCloud(
            points=points,
            semantic_class=classes,
            confidence=confidences,
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            intensity=frame.intensity,
        )
