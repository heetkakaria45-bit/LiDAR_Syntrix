"""
Unit tests verifying mock stubs against interface contracts.
"""

import unittest
import numpy as np

from src.common.config import load_config
from src.common.interfaces import (
    IPreprocessor,
    ISemanticPerception,
    IFoveatedGrid,
    ISemantic25DMapper,
    ITraversabilityAnalyzer,
    ITemporalMapUpdater,
)
from src.common.mocks import (
    MockDatasetAdapter,
    MockFoveatedGrid,
    MockPreprocessor,
    MockSemantic25DMapper,
    MockSemanticPerception,
    MockTraversabilityAnalyzer,
    MockTemporalMapUpdater,
)
from src.common.types import (
    GridCell,
    PointCloudFrame,
    SemanticClass,
    SemanticPointCloud,
)


class TestMockInterfaces(unittest.TestCase):
    """Verifies that all mock implementations conform to the ABC specifications."""

    def setUp(self) -> None:
        self.config = load_config()

    def test_mock_preprocessor_interface(self) -> None:
        mock_prep = MockPreprocessor(self.config)
        self.assertIsInstance(mock_prep, IPreprocessor)

        raw = PointCloudFrame(points=np.zeros((10, 3), dtype=np.float32))
        clean = mock_prep.process(raw)
        self.assertIsInstance(clean, PointCloudFrame)
        self.assertEqual(clean.num_points, 10)

    def test_mock_semantic_perception_interface(self) -> None:
        mock_perc = MockSemanticPerception(self.config)
        self.assertIsInstance(mock_perc, ISemanticPerception)

        raw = PointCloudFrame(points=np.ones((20, 3), dtype=np.float32))
        sem = mock_perc.infer(raw)
        self.assertIsInstance(sem, SemanticPointCloud)
        self.assertEqual(sem.num_points, 20)
        self.assertEqual(len(sem.semantic_labels), 20)
        self.assertEqual(len(sem.confidence), 20)

    def test_mock_foveated_grid_interface(self) -> None:
        mock_grid = MockFoveatedGrid(self.config)
        self.assertIsInstance(mock_grid, IFoveatedGrid)

        # Standard zone queries
        self.assertEqual(mock_grid.get_level_for_distance(5.0), 0)   # 0-10m
        self.assertEqual(mock_grid.get_level_for_distance(15.0), 1)  # 10-25m
        self.assertEqual(mock_grid.get_level_for_distance(35.0), 2)  # 25-50m
        self.assertEqual(mock_grid.get_level_for_distance(75.0), 3)  # 50-100m
        self.assertEqual(mock_grid.get_level_for_distance(120.0), -1) # > 100m (out of range)

        # Explicit boundary transitions
        self.assertEqual(mock_grid.get_level_for_distance(9.999), 0)
        self.assertEqual(mock_grid.get_level_for_distance(10.000), 1)
        self.assertEqual(mock_grid.get_level_for_distance(10.001), 1)

        self.assertEqual(mock_grid.get_level_for_distance(24.999), 1)
        self.assertEqual(mock_grid.get_level_for_distance(25.000), 2)
        self.assertEqual(mock_grid.get_level_for_distance(25.001), 2)

        self.assertEqual(mock_grid.get_level_for_distance(49.999), 2)
        self.assertEqual(mock_grid.get_level_for_distance(50.000), 3)
        self.assertEqual(mock_grid.get_level_for_distance(50.001), 3)

        self.assertEqual(mock_grid.get_level_for_distance(99.999), 3)
        self.assertEqual(mock_grid.get_level_for_distance(100.000), 3) # Closed outer boundary
        self.assertEqual(mock_grid.get_level_for_distance(100.001), -1)

    def test_mock_foveated_grid_negative_coordinates(self) -> None:
        mock_grid = MockFoveatedGrid(self.config)

        # Test negative coordinates across quadrants
        ix_neg, iy_neg = mock_grid.world_to_cell(-15.2, -8.7, level=1)
        # Level 1 res = 0.10m
        self.assertEqual(ix_neg, int(np.floor(-15.2 / 0.10)))
        self.assertEqual(iy_neg, int(np.floor(-8.7 / 0.10)))

        cx, cy = mock_grid.cell_to_world(ix_neg, iy_neg, level=1)
        self.assertAlmostEqual(cx, (ix_neg + 0.5) * 0.10)
        self.assertAlmostEqual(cy, (iy_neg + 0.5) * 0.10)

    def test_mock_semantic_25d_mapper_interface(self) -> None:
        mock_mapper = MockSemantic25DMapper(self.config)
        self.assertIsInstance(mock_mapper, ISemantic25DMapper)

        sem_cloud = SemanticPointCloud(
            points=np.zeros((5, 3), dtype=np.float32),
            semantic_labels=np.zeros(5, dtype=np.uint8),
            confidence=np.ones(5, dtype=np.float32),
            timestamp=1.0,
            frame_id=10,
        )

        sem_map = mock_mapper.update_map(sem_cloud)
        self.assertEqual(sem_map.timestamp, 1.0)
        self.assertEqual(sem_map.frame_id, 10)

    def test_mock_traversability_analyzer_interface(self) -> None:
        mock_trav = MockTraversabilityAnalyzer(self.config)
        self.assertIsInstance(mock_trav, ITraversabilityAnalyzer)

        # Ground cell with low roughness
        gnd_cell = GridCell(
            resolution_level=0,
            cell_index=(0, 0),
            position=(0.0, 0.0),
            elevation=0.0,
            min_z=0.0,
            max_z=0.02,
            semantic_class=SemanticClass.DRIVABLE_GROUND,
            semantic_confidence=0.9,
            occupancy=0.5,
            point_count=10,
            roughness=0.01,
            timestamp=0.0,
        )
        score = mock_trav.evaluate_cell(gnd_cell)
        self.assertTrue(score.is_traversable)
        self.assertEqual(score.cost, 0.0)

        # Obstacle cell (Vehicle)
        obs_cell = GridCell(
            resolution_level=0,
            cell_index=(1, 1),
            position=(0.05, 0.05),
            elevation=0.5,
            min_z=0.0,
            max_z=1.5,
            semantic_class=SemanticClass.VEHICLE,
            semantic_confidence=0.95,
            occupancy=0.9,
            point_count=50,
            roughness=0.2,
            timestamp=0.0,
        )
        obs_score = mock_trav.evaluate_cell(obs_cell)
        self.assertFalse(obs_score.is_traversable)
        self.assertEqual(obs_score.cost, 1.0)

    def test_mock_dataset_adapter(self) -> None:
        adapter = MockDatasetAdapter(num_frames=3, points_per_frame=100)
        self.assertEqual(len(adapter), 3)

        frame = adapter.get_frame(0)
        self.assertIsInstance(frame, PointCloudFrame)
        self.assertEqual(frame.num_points, 100)
        self.assertEqual(frame.frame_id, 0)


if __name__ == "__main__":
    unittest.main()
