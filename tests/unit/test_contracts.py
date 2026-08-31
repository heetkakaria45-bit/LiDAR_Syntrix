"""
Unit tests for data contracts, shapes, properties, and validation.
"""

import unittest
import numpy as np

from src.common.types import (
    CoordinateSystem,
    FoveationLevelConfig,
    GridCell,
    PointCloudFrame,
    SemanticClass,
    SemanticPointCloud,
    SemanticMap,
    TraversabilityScore,
    TelemetryMetrics,
)


class TestDataContracts(unittest.TestCase):
    """Verifies core data contract structures and shape validation rules."""

    def test_point_cloud_frame_valid(self) -> None:
        pts = np.zeros((100, 3), dtype=np.float32)
        intensities = np.ones(100, dtype=np.float32)
        frame = PointCloudFrame(points=pts, intensity=intensities, timestamp=1.5, frame_id=42)

        self.assertEqual(frame.num_points, 100)
        self.assertEqual(frame.timestamp, 1.5)
        self.assertEqual(frame.frame_id, 42)
        self.assertEqual(frame.sensor_pose.shape, (4, 4))

    def test_point_cloud_frame_invalid_shape(self) -> None:
        bad_pts = np.zeros((100, 4), dtype=np.float32)
        with self.assertRaises(ValueError):
            PointCloudFrame(points=bad_pts)

    def test_point_cloud_frame_mismatched_intensity(self) -> None:
        pts = np.zeros((100, 3), dtype=np.float32)
        bad_intensities = np.ones(50, dtype=np.float32)
        with self.assertRaises(ValueError):
            PointCloudFrame(points=pts, intensity=bad_intensities)

    def test_semantic_point_cloud_valid(self) -> None:
        N = 250
        pts = np.random.randn(N, 3).astype(np.float32)
        labels = np.random.randint(0, 8, size=(N,), dtype=np.uint8)
        conf = np.random.uniform(0.0, 1.0, size=(N,)).astype(np.float32)

        sem_cloud = SemanticPointCloud(
            points=pts,
            semantic_labels=labels,
            confidence=conf,
            timestamp=2.0,
            frame_id="seq00_001",
        )

        self.assertEqual(sem_cloud.num_points, N)
        self.assertEqual(sem_cloud.semantic_labels.dtype, np.uint8)
        self.assertEqual(sem_cloud.confidence.dtype, np.float32)

    def test_semantic_point_cloud_mismatched_labels(self) -> None:
        pts = np.zeros((100, 3), dtype=np.float32)
        bad_labels = np.zeros(50, dtype=np.uint8)
        conf = np.ones(100, dtype=np.float32)
        with self.assertRaises(ValueError):
            SemanticPointCloud(points=pts, semantic_labels=bad_labels, confidence=conf)

    def test_grid_cell_contract(self) -> None:
        cell = GridCell(
            resolution_level=1,
            cell_index=(12, -5),
            position=(1.25, -0.45),
            elevation=0.12,
            min_z=-0.05,
            max_z=0.35,
            semantic_class=SemanticClass.DRIVABLE_GROUND,
            semantic_confidence=0.92,
            occupancy=0.8,
            point_count=24,
            roughness=0.015,
            timestamp=10.5,
            velocity=(0.0, 1.2, 0.0),
            observation_count=5,
            uncertainty=0.02,
            semantic_probs=[0.92, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
        )

        self.assertEqual(cell.resolution_level, 1)
        self.assertEqual(cell.cell_index, (12, -5))
        self.assertAlmostEqual(cell.height_span, 0.40)
        self.assertEqual(cell.semantic_class, 0)
        self.assertAlmostEqual(cell.roughness, 0.015)
        self.assertEqual(cell.velocity, (0.0, 1.2, 0.0))
        self.assertEqual(cell.observation_count, 5)
        self.assertAlmostEqual(cell.uncertainty, 0.02)
        self.assertEqual(len(cell.semantic_probs), 8)

    def test_semantic_map_contract(self) -> None:
        sem_map = SemanticMap()
        self.assertEqual(sem_map.cell_count, 0)

        cell = GridCell(
            resolution_level=0,
            cell_index=(0, 0),
            position=(0.025, 0.025),
            elevation=0.0,
            min_z=0.0,
            max_z=0.1,
            semantic_class=0,
            semantic_confidence=1.0,
            occupancy=1.0,
            point_count=10,
            roughness=0.0,
            timestamp=0.0,
        )
        sem_map.cells[(0, 0, 0)] = cell
        self.assertEqual(sem_map.cell_count, 1)
        self.assertIsNotNone(sem_map.get_cell(0, 0, 0))
        self.assertIsNone(sem_map.get_cell(1, 0, 0))

    def test_traversability_score_contract(self) -> None:
        score = TraversabilityScore(
            is_traversable=True,
            cost=0.15,
            slope_rad=0.05,
            step_height_m=0.02,
            roughness_m=0.01,
            semantic_penalty=0.0,
        )
        self.assertTrue(score.is_traversable)
        self.assertAlmostEqual(score.cost, 0.15)

    def test_telemetry_metrics_contract(self) -> None:
        metrics = TelemetryMetrics(
            preprocessing_latency_ms=1.2,
            inference_latency_ms=15.4,
            projection_latency_ms=0.8,
            mapping_latency_ms=2.5,
            rendering_latency_ms=3.1,
            total_latency_ms=23.0,
            fps=43.5,
            ram_usage_mb=128.5,
            vram_usage_mb=512.0,
            input_point_count=65000,
            grid_cell_count=14200,
            timestamp=123.456,
        )
        self.assertAlmostEqual(metrics.total_latency_ms, 23.0)
        self.assertEqual(metrics.input_point_count, 65000)

    def test_semantic_class_enum_helpers(self) -> None:
        self.assertTrue(SemanticClass.is_ground(SemanticClass.DRIVABLE_GROUND))
        self.assertTrue(SemanticClass.is_ground(SemanticClass.NON_DRIVABLE_TERRAIN))
        self.assertFalse(SemanticClass.is_ground(SemanticClass.VEHICLE))

        self.assertFalse(SemanticClass.is_obstacle(SemanticClass.DRIVABLE_GROUND))
        self.assertTrue(SemanticClass.is_obstacle(SemanticClass.VEHICLE))
        self.assertTrue(SemanticClass.is_obstacle(SemanticClass.PEDESTRIAN))
        self.assertTrue(SemanticClass.is_obstacle(SemanticClass.WALL_BUILDING))

        self.assertEqual(SemanticClass.get_name(0), "DRIVABLE_GROUND")
        self.assertEqual(SemanticClass.get_name(3), "PEDESTRIAN")
        self.assertEqual(SemanticClass.get_name(99), "UNKNOWN_99")


if __name__ == "__main__":
    unittest.main()
