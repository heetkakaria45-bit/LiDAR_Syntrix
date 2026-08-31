"""Reproducible Benchmark: Scalar vs. Vectorized Batch Foveated Grid Operations.

Module: scripts/benchmark_foveated_grid.py
Owner: Manashri (Member 3 - Foveated Grid)
Purpose:
    Empirical and theoretical benchmark quantifying spatial capacity, actual
    sparse cell allocation, object-level memory consumption, scalar insertion rate,
    vectorized batch insertion rate, speedup factor, and spatial query throughput.

Adheres strictly to the SIH 2026 Anti-Fabrication Rule:
    - All reported empirical numbers originate from live runtime execution.
    - Fixed random seed for deterministic reproducibility.
    - Detailed platform and environment logging.
"""

from __future__ import annotations

import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.foveated_grid import (  # noqa: E402
    FoveatedGridIndexer,
    SparseFoveatedGrid,
)


def generate_synthetic_workload(
    num_points: int, seed: int = 42
) -> List[Tuple[float, float, Dict[str, float]]]:
    """Generate deterministic synthetic LiDAR point cloud workload.

    Simulates realistic 360-degree LiDAR range distribution:
    - Points distributed across azimuth theta in [0, 2*pi).
    - Radial distances sampled with realistic density decay r in [0.5, 99.5m].
    - Associated with elevation z and intensity payload.

    Args:
        num_points: Number of points to generate.
        seed: Random seed for deterministic reproducibility.

    Returns:
        List of (x, y, data_payload) tuples.
    """
    rng = np.random.default_rng(seed)

    # Azimuth uniformly distributed around full 360 deg
    theta = rng.uniform(0.0, 2.0 * math.pi, size=num_points)

    # Radial distribution: mixture of near-field ground reflection and extended range
    # 40% near (0.5 - 25m), 35% mid (25 - 50m), 25% far (50 - 99.5m)
    r_near = rng.uniform(0.5, 25.0, size=int(num_points * 0.40))
    r_mid = rng.uniform(25.0, 50.0, size=int(num_points * 0.35))
    r_far = rng.uniform(50.0, 99.5, size=num_points - len(r_near) - len(r_mid))
    r = np.concatenate([r_near, r_mid, r_far])
    rng.shuffle(r)

    x = r * np.cos(theta)
    y = r * np.sin(theta)
    z = rng.normal(0.0, 0.15, size=num_points)
    intensity = rng.uniform(0.1, 1.0, size=num_points)

    workload = [
        (
            float(x[idx]),
            float(y[idx]),
            {"z": float(z[idx]), "intensity": float(intensity[idx])},
        )
        for idx in range(num_points)
    ]
    return workload


def generate_query_workload(
    inserted_workload: List[Tuple[float, float, Any]],
    num_queries: int = 10000,
    seed: int = 123,
) -> List[Tuple[float, float]]:
    """Generate a balanced query set for lookup benchmarking.

    Composition:
    - 50% known occupied locations (from inserted workload)
    - 30% random unoccupied coordinates within [0, 100m)
    - 20% out-of-range coordinates (r >= 100m)

    Args:
        inserted_workload: Previously inserted point records.
        num_queries: Total number of queries to assemble.
        seed: Random seed.

    Returns:
        List of (x, y) query coordinate pairs.
    """
    rng = np.random.default_rng(seed)
    queries: List[Tuple[float, float]] = []

    # 1. 50% occupied locations
    n_occ = int(num_queries * 0.50)
    occ_indices = rng.choice(len(inserted_workload), size=n_occ, replace=True)
    for idx in occ_indices:
        queries.append((inserted_workload[idx][0], inserted_workload[idx][1]))

    # 2. 30% random in-bounds coordinates
    n_in = int(num_queries * 0.30)
    th_in = rng.uniform(0.0, 2.0 * math.pi, size=n_in)
    r_in = rng.uniform(0.5, 99.0, size=n_in)
    for idx in range(n_in):
        queries.append(
            (
                float(r_in[idx] * np.cos(th_in[idx])),
                float(r_in[idx] * np.sin(th_in[idx])),
            )
        )

    # 3. 20% out-of-bounds coordinates
    n_out = num_queries - n_occ - n_in
    th_out = rng.uniform(0.0, 2.0 * math.pi, size=n_out)
    r_out = rng.uniform(101.0, 150.0, size=n_out)
    for idx in range(n_out):
        queries.append(
            (
                float(r_out[idx] * np.cos(th_out[idx])),
                float(r_out[idx] * np.sin(th_out[idx])),
            )
        )

    rng.shuffle(queries)
    return queries


def calculate_theoretical_metrics(indexer: FoveatedGridIndexer) -> Dict[str, Any]:
    """Compute theoretical cell counts and geometric capacities."""
    max_radius = indexer.max_radius
    res_uniform = 0.05  # 5 cm baseline

    # 1. Uniform 5 cm grid
    # Bounding square: [-max_radius, max_radius] x [-max_radius, max_radius]
    square_width = 2.0 * max_radius
    cells_per_axis_uniform = int(math.ceil(square_width / res_uniform))
    uniform_square_cells = cells_per_axis_uniform * cells_per_axis_uniform

    # Circular coverage: Area = pi * R^2, Cell Area = delta^2
    uniform_circle_cells = int(math.ceil((math.pi * (max_radius**2)) / (res_uniform**2)))

    # 2. Foveated Concentric Rings
    foveated_breakdown = []
    total_foveated_square_cells = 0
    total_foveated_circle_cells = 0

    for lvl in indexer.levels:
        lvl_square_width = 2.0 * lvl.max_range
        lvl_cells_axis = int(math.ceil(lvl_square_width / lvl.resolution))
        lvl_square_cells = lvl_cells_axis * lvl_cells_axis

        annular_area = math.pi * (lvl.max_range**2 - lvl.min_range**2)
        lvl_circle_cells = int(math.ceil(annular_area / (lvl.resolution**2)))

        foveated_breakdown.append(
            {
                "level_id": lvl.level_id,
                "name": lvl.name,
                "range": f"[{lvl.min_range:.1f}, {lvl.max_range:.1f}) m",
                "resolution": f"{lvl.resolution * 100:.1f} cm",
                "dense_square_cells": lvl_square_cells,
                "annular_circle_cells": lvl_circle_cells,
            }
        )
        total_foveated_square_cells += lvl_square_cells
        total_foveated_circle_cells += lvl_circle_cells

    square_reduction_pct = (
        (uniform_square_cells - total_foveated_square_cells) / uniform_square_cells
    ) * 100.0
    circle_reduction_pct = (
        (uniform_circle_cells - total_foveated_circle_cells) / uniform_circle_cells
    ) * 100.0

    return {
        "uniform_square_cells": uniform_square_cells,
        "uniform_circle_cells": uniform_circle_cells,
        "total_foveated_square_cells": total_foveated_square_cells,
        "total_foveated_circle_cells": total_foveated_circle_cells,
        "square_reduction_pct": square_reduction_pct,
        "circle_reduction_pct": circle_reduction_pct,
        "foveated_breakdown": foveated_breakdown,
    }


def run_benchmark(
    point_workloads: Optional[List[int]] = None,
    num_trials: int = 5,
    query_count: int = 10000,
) -> Dict[str, Any]:
    """Execute end-to-end benchmark comparing scalar vs batch across point workloads."""
    workloads = point_workloads if point_workloads is not None else [10000, 50000, 100000]
    indexer = FoveatedGridIndexer()
    theoretical = calculate_theoretical_metrics(indexer)

    results = []

    # Warmup runs (scalar & batch)
    warmup_data = generate_synthetic_workload(1000, seed=999)
    warmup_arr = np.array([[p[0], p[1], p[2]["z"]] for p in warmup_data], dtype=np.float64)
    warmup_grid_s = SparseFoveatedGrid(indexer=indexer)
    for px, py, pdata in warmup_data:
        warmup_grid_s.insert(px, py, data=pdata)
    _ = warmup_grid_s.query(1.0, 1.0)
    del warmup_grid_s

    warmup_grid_b = SparseFoveatedGrid(indexer=indexer)
    warmup_grid_b.insert_batch(warmup_arr)
    _ = warmup_grid_b.query(1.0, 1.0)
    del warmup_grid_b

    for n_points in workloads:
        workload = generate_synthetic_workload(n_points, seed=42)
        points_arr = np.array([[p[0], p[1], p[2]["z"]] for p in workload], dtype=np.float64)
        payloads_list = [p[2] for p in workload]
        queries = generate_query_workload(workload, num_queries=query_count, seed=123)

        # 1. Scalar Insertion Trials
        scalar_times = []
        scalar_occupied = []
        scalar_mems = []

        for _trial in range(num_trials):
            grid_s = SparseFoveatedGrid(indexer=indexer)
            t0 = time.perf_counter()
            for px, py, pdata in workload:
                grid_s.insert(px, py, data=pdata)
            t1 = time.perf_counter()

            scalar_times.append(t1 - t0)
            scalar_occupied.append(grid_s.cell_count())
            scalar_mems.append(grid_s.memory_usage())

        # 2. Vectorized Batch Insertion Trials
        batch_times = []
        batch_occupied = []
        batch_mems = []

        for _trial in range(num_trials):
            grid_b = SparseFoveatedGrid(indexer=indexer)
            t0 = time.perf_counter()
            grid_b.insert_batch(points_arr, payloads=payloads_list)
            t1 = time.perf_counter()

            batch_times.append(t1 - t0)
            batch_occupied.append(grid_b.cell_count())
            batch_mems.append(grid_b.memory_usage())

        # 3. Lookup Timing (over batch grid)
        lookup_times = []
        for _trial in range(num_trials):
            t0 = time.perf_counter()
            for qx, qy in queries:
                _ = grid_b.query(qx, qy)
            t1 = time.perf_counter()
            lookup_times.append(t1 - t0)

        # Compute Median Statistics
        median_scalar_sec = float(np.median(scalar_times))
        scalar_rate_pts_sec = n_points / median_scalar_sec if median_scalar_sec > 0 else 0.0

        median_batch_sec = float(np.median(batch_times))
        batch_rate_pts_sec = n_points / median_batch_sec if median_batch_sec > 0 else 0.0

        speedup_factor = (
            batch_rate_pts_sec / scalar_rate_pts_sec if scalar_rate_pts_sec > 0 else 1.0
        )

        median_lookup_sec = float(np.median(lookup_times))
        lookup_rate_sec = query_count / median_lookup_sec if median_lookup_sec > 0 else 0.0

        median_occupied_cells = int(np.median(batch_occupied))
        median_mem_bytes = int(np.median(batch_mems))
        mem_breakdown = grid_b.memory_usage_breakdown()

        results.append(
            {
                "num_points": n_points,
                "occupied_cells": median_occupied_cells,
                "memory_bytes": median_mem_bytes,
                "memory_kib": median_mem_bytes / 1024.0,
                "memory_mib": median_mem_bytes / (1024.0 * 1024.0),
                "scalar_time_sec": median_scalar_sec,
                "scalar_rate_pts_sec": scalar_rate_pts_sec,
                "batch_time_sec": median_batch_sec,
                "batch_rate_pts_sec": batch_rate_pts_sec,
                "speedup_factor": speedup_factor,
                "lookup_time_sec": median_lookup_sec,
                "lookup_rate_sec": lookup_rate_sec,
                "memory_breakdown": mem_breakdown,
            }
        )

    env_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "system": platform.system(),
        "release": platform.release(),
    }

    return {
        "environment": env_info,
        "theoretical": theoretical,
        "workload_results": results,
    }


def print_benchmark_report(benchmark_data: Dict[str, Any]) -> None:
    """Format and print benchmark results to console in standard markdown tables."""
    env = benchmark_data["environment"]
    theo = benchmark_data["theoretical"]
    results = benchmark_data["workload_results"]

    print("\n" + "=" * 80)
    print("      SIH 2026: FOVEATED SPATIAL GRID BENCHMARK (SCALAR VS BATCH)      ")
    print("=" * 80)
    print(f"Platform:        {env['platform']} ({env['processor']})")
    print(f"Python Version:  {env['python_version']}")
    print("Max Radius:      100.0 m")
    print("Timing Method:   time.perf_counter() [Median of 5 trials]")
    print("-" * 80)

    print("\n### 1. THEORETICAL CELL CAPACITY COMPARISON\n")
    print(
        "| Representation | Resolution Bands | Coverage | Theoretical Cells | Storage Mode |"
        " Capacity Reduction |"
    )
    print("| :--- | :--- | :--- | :---: | :---: | :---: |")
    print(
        f"| **Uniform Baseline** | 5.0 cm uniform | 200m x 200m Square | {theo['uniform_square_cells']:,} | Dense | 0.0% |"
    )
    print(
        f"| **Uniform Baseline** | 5.0 cm uniform | 100m Radius Circle | {theo['uniform_circle_cells']:,} | Dense | 0.0% |"
    )
    print(
        f"| **Foveated Rings** | 5 / 10 / 25 / 50 cm | Bounding Squares | {theo['total_foveated_square_cells']:,} | Dense Multi-Grid | **{theo['square_reduction_pct']:.2f}%** |"
    )
    print(
        f"| **Foveated Rings** | 5 / 10 / 25 / 50 cm | Concentric Annuli | {theo['total_foveated_circle_cells']:,} | Sparse Hash Grid | **{theo['circle_reduction_pct']:.2f}%** |"
    )

    print("\n### 2. SCALAR VS. VECTORIZED BATCH INSERTION BENCHMARK\n")
    print(
        "| Points | Occupied Cells | Scalar pts/s | Batch pts/s | Speedup | Batch Time (ms) | Lookup Rate (/s) |"
    )
    print(
        "| -----: | -------------: | -----------: | ----------: | ------: | --------------: | ---------------: |"
    )
    for r in results:
        batch_ms = r["batch_time_sec"] * 1000.0
        print(
            f"| {r['num_points']:,} | {r['occupied_cells']:,} "
            f"| {r['scalar_rate_pts_sec']:,.0f} pts/s "
            f"| {r['batch_rate_pts_sec']:,.0f} pts/s "
            f"| **{r['speedup_factor']:.2f}x** "
            f"| {batch_ms:.2f} ms "
            f"| {r['lookup_rate_sec']:,.0f} /s |"
        )

    print("\n### 3. MEMORY ALLOCATION BREAKDOWN (100k Workload)\n")
    r_100k = results[-1]
    mb = r_100k["memory_breakdown"]
    print(
        f"- Total Allocated:         {mb['total_bytes'] / (1024 * 1024):.2f} MiB ({mb['total_bytes']:,} bytes)"
    )
    print(
        f"  - Hash Table Dict:       {mb['dict_table_bytes'] / 1024:.1f} KiB ({mb['dict_table_bytes']:,} bytes)"
    )
    print(
        f"  - CellKey Tuples:        {mb['keys_bytes'] / 1024:.1f} KiB ({mb['keys_bytes']:,} bytes)"
    )
    print(
        f"  - SparseCell Instances:  {mb['cells_bytes'] / 1024:.1f} KiB ({mb['cells_bytes']:,} bytes)"
    )
    print(
        f"  - Item List Containers:  {mb['items_containers_bytes'] / 1024:.1f} KiB ({mb['items_containers_bytes']:,} bytes)"
    )
    print(
        f"  - Stored Point Payloads: {mb['payloads_bytes'] / 1024:.1f} KiB ({mb['payloads_bytes']:,} bytes)"
    )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    benchmark_output = run_benchmark()
    print_benchmark_report(benchmark_output)

    # Save structured JSON benchmark artifact
    out_dir = PROJECT_ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "grid_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_output, f, indent=2)
    print(f"Structured benchmark results saved to: {out_file}\n")
