"""Tests for SemanticElevationMapper and multi-resolution foveated SemanticMap generation.

Verifies:
- Transformation from SemanticPointCloud to SemanticMap
- Foveation preservation across all rings: near (5cm), mid_near (10cm), mid (25cm), far (50cm)
- Direct consumption of external spatial_assignments from Manashri's module
- Preservation of sensor pose and timestamps
- Lightweight performance timing telemetry collection
"""

import numpy as np
import pytest

from src.contracts import SemanticPointCloud
from src.mapping.config import MappingConfig
from src.mapping.mapper import SemanticElevationMapper, SimpleFoveatedGridAdapter
from src.preprocessing.synthetic import generate_synthetic_scene


class TestSemanticElevationMapper:
    def test_map_point_cloud_foveation_levels(self) -> None:
        """Verify mapper preserves separate resolution rings across distance bands."""
        # Generate points spanning near (5m), mid_near (15m), mid (35m), and far (75m)
        pts = np.array(
            [
                [5.0, 0.0, 0.1],   # Ring 0: near (< 10m)
                [15.0, 0.0, 0.2],  # Ring 1: mid_near (10-25m)
                [35.0, 0.0, 0.3],  # Ring 2: mid (25-50m)
                [75.0, 0.0, 0.4],  # Ring 3: far (50-100m)
            ],
            dtype=np.float32,
        )
        classes = np.array([0, 1, 2, 6], dtype=np.int32)
        confidences = np.array([0.9, 0.85, 0.95, 0.7], dtype=np.float32)

        cloud = SemanticPointCloud(
            points=pts,
            semantic_class=classes,
            confidence=confidences,
            timestamp=1000.0,
            frame_id="test_sensor",
        )

        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)

        assert "near" in sem_map.cells
        assert "mid_near" in sem_map.cells
        assert "mid" in sem_map.cells
        assert "far" in sem_map.cells

        # Exactly 1 cell populated per ring
        assert len(sem_map.cells["near"]) == 1
        assert len(sem_map.cells["mid_near"]) == 1
        assert len(sem_map.cells["mid"]) == 1
        assert len(sem_map.cells["far"]) == 1

        # Check near cell characteristics
        near_cell = list(sem_map.cells["near"].values())[0]
        assert near_cell.resolution_level == "near"
        assert near_cell.elevation == pytest.approx(0.1)
        assert near_cell.semantic_class == 0

        # Check far cell characteristics
        far_cell = list(sem_map.cells["far"].values())[0]
        assert far_cell.resolution_level == "far"
        assert far_cell.elevation == pytest.approx(0.4)
        assert far_cell.semantic_class == 6

        # Telemetry metrics exist
        assert "telemetry" in sem_map.metadata
        telem = sem_map.metadata["telemetry"]
        assert "total_mapping_time_ms" in telem
        assert telem["num_cells"] == 4

    def test_map_point_cloud_empty(self) -> None:
        cloud = SemanticPointCloud(
            points=np.zeros((0, 3), dtype=np.float32),
            semantic_class=np.zeros((0,), dtype=np.int32),
            confidence=np.zeros((0,), dtype=np.float32),
            timestamp=50.0,
            frame_id="empty_frame",
        )
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)

        assert sem_map.metadata["num_cells"] == 0
        for ring in ["near", "mid_near", "mid", "far"]:
            assert len(sem_map.cells[ring]) == 0

    def test_map_point_cloud_with_synthetic_urban_scene(self) -> None:
        """Integration check using the synthetic dataset generator."""
        _, cloud = generate_synthetic_scene()
        mapper = SemanticElevationMapper()
        sem_map = mapper.map_point_cloud(cloud)

        assert sem_map.metadata["num_cells"] > 100
        assert sem_map.timestamp == cloud.timestamp
        assert sem_map.metadata["frame_id"] == "synthetic_lidar"
        assert sem_map.sensor_pose.shape == (4, 4)

    def test_external_spatial_assignments_integration(self) -> None:
        """Verify mapper directly consumes external spatial assignments without recomputing."""
        pts = np.array(
            [
                [2.0, 1.0, 0.15],
                [2.02, 1.01, 0.17],
                [12.0, 5.0, 0.30],
            ],
            dtype=np.float32,
        )
        classes = np.array([0, 0, 1], dtype=np.int32)
        confidences = np.array([0.9, 0.8, 0.95], dtype=np.float32)

        cloud = SemanticPointCloud(
            points=pts,
            semantic_class=classes,
            confidence=confidences,
            timestamp=500.0,
            frame_id="external_indexing_test",
        )

        # Explicit mock of Manashri's spatial assignments format
        custom_spatial_assignments = {
            "near": {
                (40, 20): (2.025, 1.025, np.array([0, 1], dtype=np.int64)),
            },
            "mid_near": {
                (120, 50): (12.05, 5.05, np.array([2], dtype=np.int64)),
            },
            "mid": {},
            "far": {},
        }

        # Mapper with a dummy grid indexer that would fail if called
        class FailingIndexer:
            def assign_points(self, points: np.ndarray):
                raise AssertionError("Internal assign_points should not be called!")

        mapper = SemanticElevationMapper(grid_indexer=FailingIndexer())
        sem_map = mapper.map_point_cloud(cloud, spatial_assignments=custom_spatial_assignments)

        assert len(sem_map.cells["near"]) == 1
        assert len(sem_map.cells["mid_near"]) == 1
        assert (40, 20) in sem_map.cells["near"]
        assert (120, 50) in sem_map.cells["mid_near"]

        near_cell = sem_map.cells["near"][(40, 20)]
        assert near_cell.resolution_level == "near"
        assert near_cell.cell_x == pytest.approx(2.025)
        assert near_cell.cell_y == pytest.approx(1.025)
        assert near_cell.point_count == 2
        assert near_cell.elevation == pytest.approx(0.16)

        mid_cell = sem_map.cells["mid_near"][(120, 50)]
        assert mid_cell.resolution_level == "mid_near"
        assert mid_cell.cell_x == pytest.approx(12.05)
        assert mid_cell.cell_y == pytest.approx(5.05)
        assert mid_cell.semantic_class == 1
