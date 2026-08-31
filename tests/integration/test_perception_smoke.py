"""
Integration Smoke Test for Semantic Perception Subsystem.
Demonstrates clean execution: PointCloudFrame -> SemanticPerceptionEngine -> SemanticPointCloud.
"""

import unittest
import numpy as np

from src.common.types import PointCloudFrame, SemanticPointCloud, SemanticClass
from src.perception.interface import SemanticPerceptionEngine


class TestPerceptionIntegrationSmoke(unittest.TestCase):
    """Integration smoke test for Vedant's perception subsystem."""

    def setUp(self) -> None:
        self.perception_engine = SemanticPerceptionEngine()

    def test_perception_pipeline_smoke(self) -> None:
        # Generate a small realistic LiDAR frame with ground and obstacle points
        np.random.seed(42)
        N = 1000
        xs = np.random.uniform(1.0, 50.0, N).astype(np.float32)
        ys = np.random.uniform(-15.0, 15.0, N).astype(np.float32)
        # Ground plane at z ~ 0 with random elevated objects
        zs = np.where(np.random.rand(N) > 0.8, np.random.uniform(0.5, 2.0, N), np.random.uniform(-0.1, 0.1, N)).astype(np.float32)
        points = np.column_stack([xs, ys, zs])
        intensity = np.random.uniform(10.0, 200.0, N).astype(np.float32)

        raw_frame = PointCloudFrame(
            points=points,
            intensity=intensity,
            timestamp=100.0,
            frame_id=1,
            sensor_pose=np.eye(4, dtype=np.float64),
        )

        # Execute perception inference
        sem_cloud = self.perception_engine.infer(raw_frame)

        # Assert contract compliance
        self.assertIsInstance(sem_cloud, SemanticPointCloud)
        self.assertEqual(sem_cloud.num_points, N)
        self.assertEqual(len(sem_cloud.semantic_labels), N)
        self.assertEqual(len(sem_cloud.confidence), N)
        self.assertEqual(sem_cloud.timestamp, 100.0)
        self.assertEqual(sem_cloud.frame_id, 1)

        # Check that latency is measured and non-zero
        self.assertGreater(self.perception_engine.last_inference_latency_ms, 0.0)

    def test_streaming_perception_sequence(self) -> None:
        # Simulate multi-frame stream
        num_frames = 5
        points_per_frame = 200

        for f_idx in range(num_frames):
            pts = np.random.uniform(-20.0, 20.0, size=(points_per_frame, 3)).astype(np.float32)
            frame = PointCloudFrame(points=pts, timestamp=float(f_idx) * 0.1, frame_id=f_idx)

            sem_cloud = self.perception_engine.infer(frame)
            self.assertEqual(sem_cloud.num_points, points_per_frame)
            self.assertEqual(sem_cloud.frame_id, f_idx)


if __name__ == "__main__":
    unittest.main()
