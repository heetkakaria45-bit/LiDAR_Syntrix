"""
Unit tests for central configuration loading and validation.
"""

import unittest
from pathlib import Path

from src.common.config import (
    CoordinateConfig,
    FoveationConfig,
    FoveationLevelConfig,
    RuntimeConfig,
    SemanticTaxonomyConfig,
    SystemConfig,
    load_config,
)
from src.common.types import SemanticClass


class TestCentralConfiguration(unittest.TestCase):
    """Verifies that config/config.yaml loads accurately into typed dataclasses."""

    def setUp(self) -> None:
        self.config = load_config()

    def test_coordinate_system_frozen(self) -> None:
        coord = self.config.coordinate_system
        self.assertEqual(coord.convention, "FLU")
        self.assertEqual(coord.axes.get("x"), "forward")
        self.assertEqual(coord.axes.get("y"), "left")
        self.assertEqual(coord.axes.get("z"), "up")
        self.assertEqual(coord.units, "meters")

    def test_foveation_levels_frozen_values(self) -> None:
        fov = self.config.foveation
        self.assertEqual(fov.min_range_m, 0.0)
        self.assertEqual(fov.max_range_m, 100.0)
        self.assertEqual(len(fov.levels), 4)

        # Level 0: 0-10 m -> 0.05 m
        self.assertEqual(fov.levels[0].level, 0)
        self.assertEqual(fov.levels[0].min_radius_m, 0.0)
        self.assertEqual(fov.levels[0].max_radius_m, 10.0)
        self.assertAlmostEqual(fov.levels[0].cell_resolution_m, 0.05)

        # Level 1: 10-25 m -> 0.10 m
        self.assertEqual(fov.levels[1].level, 1)
        self.assertEqual(fov.levels[1].min_radius_m, 10.0)
        self.assertEqual(fov.levels[1].max_radius_m, 25.0)
        self.assertAlmostEqual(fov.levels[1].cell_resolution_m, 0.10)

        # Level 2: 25-50 m -> 0.25 m
        self.assertEqual(fov.levels[2].level, 2)
        self.assertEqual(fov.levels[2].min_radius_m, 25.0)
        self.assertEqual(fov.levels[2].max_radius_m, 50.0)
        self.assertAlmostEqual(fov.levels[2].cell_resolution_m, 0.25)

        # Level 3: 50-100 m -> 0.50 m
        self.assertEqual(fov.levels[3].level, 3)
        self.assertEqual(fov.levels[3].min_radius_m, 50.0)
        self.assertEqual(fov.levels[3].max_radius_m, 100.0)
        self.assertAlmostEqual(fov.levels[3].cell_resolution_m, 0.50)

    def test_foveation_validation_success(self) -> None:
        # Should not raise
        self.config.foveation.validate()

    def test_foveation_validation_detects_gap(self) -> None:
        bad_levels = [
            FoveationLevelConfig(0, 0.0, 10.0, 0.05),
            FoveationLevelConfig(1, 15.0, 25.0, 0.10), # Gap between 10.0 and 15.0
        ]
        bad_fov = FoveationConfig(min_range_m=0.0, max_range_m=25.0, levels=bad_levels)
        with self.assertRaises(ValueError):
            bad_fov.validate()

    def test_foveation_validation_detects_negative_resolution(self) -> None:
        bad_levels = [
            FoveationLevelConfig(0, 0.0, 10.0, -0.05),
            FoveationLevelConfig(1, 10.0, 25.0, 0.10),
        ]
        bad_fov = FoveationConfig(min_range_m=0.0, max_range_m=25.0, levels=bad_levels)
        with self.assertRaises(ValueError):
            bad_fov.validate()

    def test_semantic_taxonomy_frozen(self) -> None:
        sem = self.config.semantics
        self.assertEqual(sem.num_classes, 8)
        self.assertEqual(len(sem.classes), 8)

        expected_names = [
            (0, "DRIVABLE_GROUND", False, True, True),
            (1, "NON_DRIVABLE_TERRAIN", True, True, False),
            (2, "VEHICLE", True, False, False),
            (3, "PEDESTRIAN", True, False, False),
            (4, "CYCLIST", True, False, False),
            (5, "POLE", True, False, False),
            (6, "WALL_BUILDING", True, False, False),
            (7, "OTHER_OBSTACLE", True, False, False),
        ]

        for cid, name, is_obs, is_gnd, is_trav in expected_names:
            cinfo = sem.classes[cid]
            self.assertEqual(cinfo.name, name)
            self.assertEqual(cinfo.is_obstacle, is_obs)
            self.assertEqual(cinfo.is_ground, is_gnd)
            self.assertEqual(cinfo.default_traversable, is_trav)

    def test_runtime_and_telemetry_settings(self) -> None:
        runtime = self.config.runtime
        self.assertTrue(runtime.enable_telemetry)
        self.assertEqual(runtime.timer_backend, "time.perf_counter")
        self.assertEqual(runtime.warmup_frames, 10)
        self.assertTrue(runtime.profile_memory)

    def test_missing_config_fallback(self) -> None:
        non_existent = Path("non_existent_config_dir/missing.yaml")
        cfg = load_config(non_existent)
        self.assertIsInstance(cfg, SystemConfig)
        self.assertEqual(len(cfg.foveation.levels), 4)


if __name__ == "__main__":
    unittest.main()
