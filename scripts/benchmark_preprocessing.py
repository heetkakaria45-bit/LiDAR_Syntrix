#!/usr/bin/env python3
"""Preprocessing Pipeline Empirical Performance Benchmark.

Evaluates latency, throughput, point reduction, and memory usage for the
LiDAR Preprocessing Pipeline across 10,000, 50,000, and 100,000 point workloads.

Output: outputs/preprocessing_benchmark_results.json
"""

import gc
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.contracts import PointCloudFrame
from src.preprocessing.pipeline import PreprocessingPipeline


def generate_benchmark_cloud(num_points: int, seed: int = 42) -> PointCloudFrame:
    """Generate deterministic synthetic point cloud with ground and obstacle structures."""
    rng = np.random.default_rng(seed)

    # 60% ground points (r from 0.5 to 90m, z ~ 0)
    n_ground = int(num_points * 0.6)
    r_ground = rng.uniform(0.5, 90.0, size=n_ground)
    theta_ground = rng.uniform(0, 2 * np.pi, size=n_ground)
    x_g = r_ground * np.cos(theta_ground)
    y_g = r_ground * np.sin(theta_ground)
    z_g = rng.normal(0.0, 0.04, size=n_ground)

    # 35% obstacle/vehicle/pedestrian/building points (z from 0.3 to 5.0m)
    n_obs = int(num_points * 0.35)
    r_obs = rng.uniform(2.0, 80.0, size=n_obs)
    theta_obs = rng.uniform(0, 2 * np.pi, size=n_obs)
    x_o = r_obs * np.cos(theta_obs)
    y_o = r_obs * np.sin(theta_obs)
    z_o = rng.uniform(0.3, 4.5, size=n_obs)

    # 5% out-of-bounds noise & isolated speckles (r < 0.4m or r > 105m or high noise)
    n_noise = num_points - n_ground - n_obs
    x_n = rng.uniform(-120.0, 120.0, size=n_noise)
    y_n = rng.uniform(-120.0, 120.0, size=n_noise)
    z_n = rng.uniform(-5.0, 15.0, size=n_noise)

    points = np.vstack(
        [
            np.column_stack([x_g, y_g, z_g]),
            np.column_stack([x_o, y_o, z_o]),
            np.column_stack([x_n, y_n, z_n]),
        ]
    ).astype(np.float32)

    intensity = rng.uniform(0.1, 1.0, size=len(points)).astype(np.float32)

    return PointCloudFrame(
        points=points,
        intensity=intensity,
        timestamp=time.time(),
        frame_id=f"bench_{num_points}",
    )


def run_preprocessing_benchmark() -> Dict[str, Any]:
    """Execute empirical benchmark over 10k, 50k, and 100k point workloads."""
    print("=" * 80)
    print("       SIH 2026: LIDAR PREPROCESSING EMPIRICAL BENCHMARK       ")
    print("=" * 80)
    print(f"Platform:        {platform.platform()} ({platform.processor()})")
    print(f"Python Version:  {platform.python_version()}")
    print("-" * 80)

    pipeline = PreprocessingPipeline()
    workloads = [10000, 50000, 100000]
    repetitions = 5
    results: List[Dict[str, Any]] = []

    for num_points in workloads:
        print(f"\n[Benchmarking Workload] {num_points:,} input points ({repetitions} repetitions)...")
        frame = generate_benchmark_cloud(num_points)

        latencies_ms: List[float] = []
        reduction_percentages: List[float] = []
        out_counts: List[int] = []
        ground_counts: List[int] = []
        non_ground_counts: List[int] = []

        # Warmup
        _ = pipeline.process(frame)

        for rep in range(repetitions):
            gc.disable()
            t0 = time.perf_counter()
            preprocessed = pipeline.process(frame)
            t1 = time.perf_counter()
            gc.enable()

            dt_ms = (t1 - t0) * 1000.0
            latencies_ms.append(dt_ms)
            out_counts.append(len(preprocessed.points))
            ground_counts.append(preprocessed.stats.ground_points)
            non_ground_counts.append(preprocessed.stats.non_ground_points)
            reduction_percentages.append(preprocessed.stats.reduction_percentage)

        median_lat = float(np.median(latencies_ms))
        min_lat = float(np.min(latencies_ms))
        max_lat = float(np.max(latencies_ms))
        mean_out = int(np.mean(out_counts))
        mean_ground = int(np.mean(ground_counts))
        mean_non_ground = int(np.mean(non_ground_counts))
        mean_reduction = float(np.mean(reduction_percentages))
        throughput_pts_sec = float(num_points / (median_lat / 1000.0))

        workload_result = {
            "input_points": num_points,
            "output_points": mean_out,
            "ground_points": mean_ground,
            "non_ground_points": mean_non_ground,
            "reduction_percentage": round(mean_reduction, 2),
            "median_latency_ms": round(median_lat, 2),
            "min_latency_ms": round(min_lat, 2),
            "max_latency_ms": round(max_lat, 2),
            "throughput_pts_sec": round(throughput_pts_sec, 0),
        }
        results.append(workload_result)

        print(f"  -> Median Latency:     {median_lat:.2f} ms")
        print(f"  -> Throughput:         {throughput_pts_sec:,.0f} pts/sec")
        print(f"  -> Ingested -> Output: {num_points:,} -> {mean_out:,} pts ({mean_reduction:.1f}% reduction)")
        print(f"  -> Ground / Obstacles: {mean_ground:,} ground / {mean_non_ground:,} non-ground")

    benchmark_data = {
        "metadata": {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "pipeline_stages": [
                "Validation",
                "RangeFilter (0.5m - 100.0m)",
                "OutlierFilter (1.0m radius)",
                "VoxelDownsampler (5cm voxel)",
                "GroundFilter (0.20m threshold)",
            ],
        },
        "workloads": results,
    }

    # Save to outputs directory
    out_dir = REPO_ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "preprocessing_benchmark_results.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"\nSaved empirical benchmark results to: {out_path}")
    print("=" * 80)
    return benchmark_data


if __name__ == "__main__":
    run_preprocessing_benchmark()
