"""Performance and Timing Benchmark Tests for Mapping Stages.

Measures realistic runtime latency across:
1. Elevation aggregation
2. Semantic fusion aggregation
3. Terrain analysis (slope & traversability)
4. Geometric hazard detection (curbs, potholes, overhangs)
5. Complete end-to-end mapping pipeline

Provides real, measured timing telemetry for Atharva (Integration) and Himisha (Evaluation).
"""

import time
import numpy as np
import pytest

from src.contracts import SyntheticSceneConfig
from src.mapping.aggregation import (
    aggregate_semantics,
    compute_elevation_bounds,
    compute_roughness,
)
from src.mapping.hazards import detect_map_hazards
from src.mapping.mapper import SemanticElevationMapper
from src.mapping.terrain import analyze_map_terrain
from src.preprocessing.synthetic import generate_synthetic_scene


@pytest.fixture(scope="module")
def realistic_urban_cloud():
    """Generate a realistic 10,000 point synthetic urban scene."""
    cfg = SyntheticSceneConfig(scene_type="urban", num_points=10000, seed=42)
    _, cloud = generate_synthetic_scene(cfg)
    return cloud


class TestMappingPerformanceBenchmarks:
    """Benchmark tests measuring execution latency on synthetic point clouds."""

    def test_benchmarks_and_stage_timings(self, realistic_urban_cloud) -> None:
        cloud = realistic_urban_cloud
        mapper = SemanticElevationMapper()

        # 1. Elevation Aggregation Micro-benchmark
        z_sample = cloud.points[:, 2]
        t0 = time.perf_counter()
        for _ in range(100):
            compute_elevation_bounds(z_sample, strategy="median")
        t_elev_ms = ((time.perf_counter() - t0) / 100.0) * 1000.0

        # 2. Semantic Fusion Micro-benchmark
        cls_sample = cloud.semantic_class
        conf_sample = cloud.confidence
        t0 = time.perf_counter()
        for _ in range(100):
            aggregate_semantics(cls_sample, conf_sample)
        t_sem_ms = ((time.perf_counter() - t0) / 100.0) * 1000.0

        # 3. End-to-End Point Cloud Mapping
        t0 = time.perf_counter()
        sem_map = mapper.map_point_cloud(cloud)
        t_map_ms = (time.perf_counter() - t0) * 1000.0

        # 4. Terrain & Traversability Analysis
        t0 = time.perf_counter()
        terrain = analyze_map_terrain(sem_map)
        t_terrain_ms = (time.perf_counter() - t0) * 1000.0

        # 5. Geometric Hazard Detection
        t0 = time.perf_counter()
        hazards = detect_map_hazards(sem_map)
        t_hazards_ms = (time.perf_counter() - t0) * 1000.0

        # Total Pipeline Time for 10,000 points
        total_time_ms = t_map_ms + t_terrain_ms + t_hazards_ms

        print("\n--- HEET MAPPING PERFORMANCE BENCHMARK (10,000 Points) ---")
        print(f"1. Elevation Aggregation (10k pts):  {t_elev_ms:.4f} ms")
        print(f"2. Semantic Fusion (10k pts):        {t_sem_ms:.4f} ms")
        print(f"3. Full Grid Mapping & Aggregation:  {t_map_ms:.2f} ms")
        print(f"4. Terrain & Traversability Analysis:{t_terrain_ms:.2f} ms")
        print(f"5. Geometric Hazard Detection:       {t_hazards_ms:.2f} ms")
        print(f"Total End-to-End Mapping & Analysis: {total_time_ms:.2f} ms")
        print(f"Output Cells Generated:              {sem_map.metadata['num_cells']}")
        print(f"Hazard Candidates Detected:          {hazards['summary']}")

        assert t_elev_ms > 0.0
        assert t_sem_ms > 0.0
        assert t_map_ms > 0.0
        assert t_terrain_ms > 0.0
        assert t_hazards_ms > 0.0
        assert sem_map.metadata["num_cells"] > 500
