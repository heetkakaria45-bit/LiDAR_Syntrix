"""
Comprehensive Unit Tests for Vedant's Semantic Perception Subsystem.
"""

import unittest
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from src.common.types import (
    PointCloudFrame,
    SemanticClass,
    SemanticPointCloud,
)
from src.perception.interface import SemanticPerceptionEngine
from src.perception.features import PointCloudFeatureExtractor
from src.perception.classifier import CalibratedGeometricClassifier, softmax
from src.perception.models import (
    CalibratedGeometricModelWrapper,
    GenericSklearnModelWrapper,
)
from src.perception.adapters import (
    SemanticKITTIAdapter,
    NuScenesAdapter,
    WaymoDatasetAdapter,
    get_adapter,
)


class TestSemanticPerception(unittest.TestCase):
    """Unit tests for the perception pipeline, models, and adapters."""

    def setUp(self) -> None:
        self.engine = SemanticPerceptionEngine()

    def test_standard_inference_output_contracts(self) -> None:
        N = 500
        np.random.seed(42)
        pts = np.random.uniform(-30.0, 30.0, size=(N, 3)).astype(np.float32)
        pts[:, 2] = np.random.uniform(-1.0, 3.0, size=N)
        intensity = np.random.uniform(0.0, 255.0, size=N).astype(np.float32)

        frame = PointCloudFrame(
            points=pts,
            intensity=intensity,
            timestamp=12.34,
            frame_id="frame_042",
        )

        sem_cloud = self.engine.infer(frame)

        self.assertIsInstance(sem_cloud, SemanticPointCloud)
        self.assertEqual(sem_cloud.num_points, N)
        self.assertEqual(sem_cloud.semantic_labels.shape, (N,))
        self.assertEqual(sem_cloud.confidence.shape, (N,))
        self.assertEqual(sem_cloud.timestamp, 12.34)
        self.assertEqual(sem_cloud.frame_id, "frame_042")

        # Check semantic class validity (0..7)
        self.assertTrue(np.all(sem_cloud.semantic_labels >= 0))
        self.assertTrue(np.all(sem_cloud.semantic_labels <= 7))
        self.assertEqual(sem_cloud.semantic_labels.dtype, np.uint8)

        # Check confidence validity (0.0..1.0)
        self.assertTrue(np.all(sem_cloud.confidence >= 0.0))
        self.assertTrue(np.all(sem_cloud.confidence <= 1.0))
        self.assertEqual(sem_cloud.confidence.dtype, np.float32)

    def test_point_correspondence_invariant(self) -> None:
        N = 100
        np.random.seed(101)
        pts = np.random.randn(N, 3).astype(np.float32)
        frame = PointCloudFrame(points=pts)

        sem_cloud = self.engine.infer(frame)

        # Output coordinates must exactly match input coordinates
        np.testing.assert_array_equal(sem_cloud.points, pts)

    def test_empty_point_cloud(self) -> None:
        empty_pts = np.zeros((0, 3), dtype=np.float32)
        frame = PointCloudFrame(points=empty_pts)

        sem_cloud = self.engine.infer(frame)

        self.assertEqual(sem_cloud.num_points, 0)
        self.assertEqual(sem_cloud.points.shape, (0, 3))
        self.assertEqual(sem_cloud.semantic_labels.shape, (0,))
        self.assertEqual(sem_cloud.confidence.shape, (0,))

    def test_nan_and_infinite_point_handling(self) -> None:
        pts = np.array([
            [10.0, 2.0, 0.0],
            [np.nan, 0.0, 0.0],
            [5.0, np.inf, 1.0],
            [-np.inf, -2.0, 0.5],
            [12.0, -1.0, 0.1],
        ], dtype=np.float32)

        frame = PointCloudFrame(points=pts)
        sem_cloud = self.engine.infer(frame)

        self.assertEqual(sem_cloud.num_points, 5)
        # Corrupted points (index 1, 2, 3) must receive fallback OTHER_OBSTACLE and 0.0 confidence
        self.assertEqual(sem_cloud.confidence[1], 0.0)
        self.assertEqual(sem_cloud.semantic_labels[1], SemanticClass.OTHER_OBSTACLE)
        self.assertEqual(sem_cloud.confidence[2], 0.0)
        self.assertEqual(sem_cloud.confidence[3], 0.0)

        # Valid points (index 0, 4) should have valid predictions
        self.assertGreater(sem_cloud.confidence[0], 0.0)
        self.assertGreater(sem_cloud.confidence[4], 0.0)

    def test_infer_with_probs_distribution(self) -> None:
        N = 50
        pts = np.random.uniform(-10.0, 10.0, size=(N, 3)).astype(np.float32)
        frame = PointCloudFrame(points=pts)

        sem_cloud, probs = self.engine.infer_with_probs(frame)

        self.assertEqual(probs.shape, (N, 8))
        # Each row must sum to 1.0 (valid probability distribution)
        row_sums = np.sum(probs, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(N, dtype=np.float32), rtol=1e-4)

        # argmax of probs must match semantic_labels
        expected_labels = np.argmax(probs, axis=1).astype(np.uint8)
        np.testing.assert_array_equal(sem_cloud.semantic_labels, expected_labels)

        # max of probs must match confidence
        expected_conf = np.max(probs, axis=1).astype(np.float32)
        np.testing.assert_allclose(sem_cloud.confidence, expected_conf, rtol=1e-4)

    def test_determinism(self) -> None:
        np.random.seed(99)
        pts = np.random.randn(200, 3).astype(np.float32)
        frame1 = PointCloudFrame(points=pts.copy())
        frame2 = PointCloudFrame(points=pts.copy())

        out1 = self.engine.infer(frame1)
        out2 = self.engine.infer(frame2)

        np.testing.assert_array_equal(out1.semantic_labels, out2.semantic_labels)
        np.testing.assert_array_equal(out1.confidence, out2.confidence)

    def test_ground_vs_obstacle_geometric_signatures(self) -> None:
        ground_pts = np.array([
            [5.0, 0.0, 0.0],
            [5.1, 0.1, 0.01],
            [5.0, -0.1, -0.01],
            [10.0, 0.0, 0.0],
            [10.1, 0.2, 0.02],
        ], dtype=np.float32)

        vehicle_pts = np.array([
            [15.0, 0.0, 0.0],
            [15.0, 0.0, 0.5],
            [15.0, 0.0, 1.2],
            [15.0, 0.0, 1.8],
        ], dtype=np.float32)

        frame_gnd = PointCloudFrame(points=ground_pts)
        sem_gnd = self.engine.infer(frame_gnd)
        self.assertEqual(sem_gnd.semantic_labels[0], SemanticClass.DRIVABLE_GROUND)

        frame_veh = PointCloudFrame(points=vehicle_pts)
        sem_veh = self.engine.infer(frame_veh)
        self.assertEqual(sem_veh.semantic_labels[2], SemanticClass.VEHICLE)

    def test_dataset_adapters_semantickitti(self) -> None:
        adapter = SemanticKITTIAdapter()
        self.assertEqual(adapter.get_dataset_name(), "SemanticKITTI")

        self.assertEqual(adapter.map_label(10), SemanticClass.VEHICLE)
        self.assertEqual(adapter.map_label(30), SemanticClass.PEDESTRIAN)
        self.assertEqual(adapter.map_label(40), SemanticClass.DRIVABLE_GROUND)
        self.assertEqual(adapter.map_label(70), SemanticClass.NON_DRIVABLE_TERRAIN)
        self.assertEqual(adapter.map_label(80), SemanticClass.POLE)
        self.assertEqual(adapter.map_label(50), SemanticClass.WALL_BUILDING)
        self.assertEqual(adapter.map_label(11), SemanticClass.CYCLIST)

        raw_labels = np.array([10, 30, 40, 70, 80, 50, 11, 999], dtype=np.uint32)
        mapped = adapter.map_labels(raw_labels)
        expected = np.array([2, 3, 0, 1, 5, 6, 4, 7], dtype=np.uint8)
        np.testing.assert_array_equal(mapped, expected)

    def test_dataset_adapters_nuscenes(self) -> None:
        adapter = NuScenesAdapter()
        self.assertEqual(adapter.get_dataset_name(), "nuScenes")

        self.assertEqual(adapter.map_label(17), SemanticClass.VEHICLE)            # car -> 2
        self.assertEqual(adapter.map_label(2), SemanticClass.PEDESTRIAN)          # pedestrian adult -> 3
        self.assertEqual(adapter.map_label(24), SemanticClass.DRIVABLE_GROUND)    # driveable surface -> 0
        self.assertEqual(adapter.map_label(27), SemanticClass.NON_DRIVABLE_TERRAIN) # terrain -> 1
        self.assertEqual(adapter.map_label(28), SemanticClass.WALL_BUILDING)      # manmade -> 6

        raw = np.array([17, 2, 24, 27, 28, 99], dtype=np.uint8)
        mapped = adapter.map_labels(raw)
        expected = np.array([2, 3, 0, 1, 6, 7], dtype=np.uint8)
        np.testing.assert_array_equal(mapped, expected)

    def test_dataset_adapters_waymo(self) -> None:
        adapter = WaymoDatasetAdapter()
        self.assertEqual(adapter.get_dataset_name(), "Waymo")

        self.assertEqual(adapter.map_label(1), SemanticClass.VEHICLE)            # car -> 2
        self.assertEqual(adapter.map_label(4), SemanticClass.VEHICLE)            # other vehicle -> 2
        self.assertEqual(adapter.map_label(7), SemanticClass.PEDESTRIAN)         # pedestrian -> 3
        self.assertEqual(adapter.map_label(18), SemanticClass.DRIVABLE_GROUND)   # road -> 0
        self.assertEqual(adapter.map_label(10), SemanticClass.POLE)              # pole -> 5

    def test_get_adapter_factory(self) -> None:
        kitti_ad = get_adapter("kitti")
        self.assertIsInstance(kitti_ad, SemanticKITTIAdapter)

        nusc_ad = get_adapter("nuscenes")
        self.assertIsInstance(nusc_ad, NuScenesAdapter)

        waymo_ad = get_adapter("waymo")
        self.assertIsInstance(waymo_ad, WaymoDatasetAdapter)

        with self.assertRaises(ValueError):
            get_adapter("unknown_dataset")

    def test_custom_sklearn_model_wrapper(self) -> None:
        # Train a toy RandomForest on synthetic 10D features
        X_dummy = np.random.randn(20, 10).astype(np.float32)
        y_dummy = np.random.randint(0, 8, size=20)
        rf = RandomForestClassifier(n_estimators=5, random_state=42)
        rf.fit(X_dummy, y_dummy)

        wrapper = GenericSklearnModelWrapper(rf, model_name="ToyRandomForest")
        custom_engine = SemanticPerceptionEngine(model=wrapper)

        pts = np.random.randn(30, 3).astype(np.float32)
        frame = PointCloudFrame(points=pts)

        sem_out = custom_engine.infer(frame)
        self.assertEqual(sem_out.num_points, 30)
        self.assertEqual(sem_out.semantic_labels.dtype, np.uint8)
        self.assertEqual(sem_out.confidence.dtype, np.float32)
        self.assertTrue(np.all(sem_out.confidence >= 0.0))


if __name__ == "__main__":
    unittest.main()
