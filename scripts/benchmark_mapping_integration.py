"""Phase 5 Mapping Integration Benchmark: End-to-End Pipeline Profiling.

Module: scripts/benchmark_mapping_integration.py
Owner: Manashri (Member 3 - Foveated Grid)
Purpose:
    Profile the end-to-end mapping ingestion pipeline broken down into 4 isolated stages:
    1. Batch foveated indexing time (SIMD coordinate math, quantization, packed-key hashing)
    2. Sparse-cell creation & aggregation time (SparseCell instantiation and observation accumulation)
    3. Mapping handoff time (Conversion to GridCell contracts and SemanticMap packaging)
    4. Total end-to-end ingestion time.

Adheres strictly to the SIH 2026 Anti-Fabrication Rule:
    - All reported empirical numbers originate from live runtime execution.
    - Multiple trials with warmup run.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts import SemanticPointCloud  # noqa: E402
from src.foveated_grid import (  # noqa: E402
    CellKey,
    FoveatedGridIndexer,
    SparseCell,
    SparseFoveatedGrid,
)


def generate_synthetic_pointcloud(num_points: int, seed: int = 42) -> SemanticPointCloud:
    """Generate synthetic SemanticPointCloud contract object with realistic geometry and classes."""
    rng = np.random.default_rng(seed)
    theta = rng.uniform(0.0, 2.0 * np.pi, size=num_points)
    r = rng.uniform(0.5, 99.5, size=num_points)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    z = rng.normal(0.0, 0.15, size=num_points)
    points = np.column_stack([x, y, z]).astype(np.float32)

    classes = rng.choice([0, 1, 2, 3, 5, 6], size=num_points).astype(np.int32)
    conf = rng.uniform(0.85, 0.99, size=num_points).astype(np.float32)

    return SemanticPointCloud(
        points=points,
        semantic_class=classes,
        confidence=conf,
        timestamp=1700000000.0,
        frame_id="lidar_top",
    )


def profile_pipeline(workloads: List[int], num_trials: int = 5) -> Dict[str, Any]:
    """Profile the 4 stages of the mapping ingestion pipeline across point workloads."""
    indexer = FoveatedGridIndexer()
    results = []

    # Warmup run
    warmup_cloud = generate_synthetic_pointcloud(1000, seed=999)
    warmup_grid = SparseFoveatedGrid(indexer=indexer)
    warmup_grid.insert_batch(warmup_cloud)
    _ = warmup_grid.to_semantic_map(timestamp=warmup_cloud.timestamp)
    del warmup_grid

    for n in workloads:
        cloud = generate_synthetic_pointcloud(n, seed=42)
        pts = cloud.points.astype(np.float64)
        classes = cloud.semantic_class
        conf = cloud.confidence

        payloads = [
            {"class": int(classes[i]), "conf": float(conf[i]), "z": float(pts[i, 2])}
            for i in range(n)
        ]

        t_stage1_list = []
        t_stage2_list = []
        t_stage3_list = []
        t_total_list = []
        occupied_cells_list = []

        for _ in range(num_trials):
            # --- STAGE 1: Vectorized Foveated Indexing & Key Sorting ---
            t0 = time.perf_counter()
            valid_mask, packed_keys = indexer.world_to_cell_batch(pts)
            valid_indices = np.where(valid_mask)[0]
            valid_keys = packed_keys[valid_mask]
            sort_idx = np.argsort(valid_keys)
            sorted_keys = valid_keys[sort_idx]
            sorted_pt_indices = valid_indices[sort_idx]
            unique_keys, split_indices = np.unique(sorted_keys, return_index=True)
            num_unique = len(unique_keys)
            n_valid = len(sorted_pt_indices)
            sorted_items = [payloads[idx] for idx in sorted_pt_indices]
            t1 = time.perf_counter()

            # --- STAGE 2: Sparse Cell Instantiation & Accumulation ---
            cells_dict: Dict[CellKey, SparseCell] = {}
            for k_idx in range(num_unique):
                key_val = int(unique_keys[k_idx])
                start_i = int(split_indices[k_idx])
                end_i = int(split_indices[k_idx + 1]) if k_idx + 1 < num_unique else n_valid

                group_items = sorted_items[start_i:end_i]
                cell_key = CellKey.from_packed_uint64(key_val)

                cx, cy = indexer.cell_to_world(cell_key)
                lvl = indexer.get_level(cell_key.level)
                cells_dict[cell_key] = SparseCell(
                    key=cell_key,
                    center_x=cx,
                    center_y=cy,
                    resolution=lvl.resolution,
                    level_name=lvl.name,
                    items=group_items,
                )
            t2 = time.perf_counter()

            # --- STAGE 3: Mapping Handoff (GridCell & SemanticMap Packaging) ---
            grid = SparseFoveatedGrid(indexer=indexer)
            grid._cells = cells_dict
            _ = grid.to_semantic_map(
                sensor_pose=np.eye(4, dtype=np.float64), timestamp=cloud.timestamp
            )
            t3 = time.perf_counter()

            t_stage1_list.append(t1 - t0)
            t_stage2_list.append(t2 - t1)
            t_stage3_list.append(t3 - t2)
            t_total_list.append(t3 - t0)
            occupied_cells_list.append(len(cells_dict))

        # Medians
        med_stage1_ms = float(np.median(t_stage1_list)) * 1000.0
        med_stage2_ms = float(np.median(t_stage2_list)) * 1000.0
        med_stage3_ms = float(np.median(t_stage3_list)) * 1000.0
        med_total_ms = float(np.median(t_total_list)) * 1000.0
        med_cells = int(np.median(occupied_cells_list))
        e2e_rate = (n / (med_total_ms / 1000.0)) if med_total_ms > 0 else 0.0

        results.append(
            {
                "num_points": n,
                "occupied_cells": med_cells,
                "stage1_indexing_ms": med_stage1_ms,
                "stage2_cell_creation_ms": med_stage2_ms,
                "stage3_mapping_handoff_ms": med_stage3_ms,
                "total_e2e_ms": med_total_ms,
                "e2e_rate_pts_sec": e2e_rate,
            }
        )

    env_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
    }

    return {"environment": env_info, "results": results}


def print_report(data: Dict[str, Any]) -> None:
    """Print formatted markdown report of stage-by-stage profiling."""
    env = data["environment"]
    results = data["results"]

    print("\n" + "=" * 80)
    print("      SIH 2026: PHASE 5 MAPPING PIPELINE STAGE-BY-STAGE BENCHMARK      ")
    print("=" * 80)
    print(f"Platform:        {env['platform']} ({env['processor']})")
    print(f"Python Version:  {env['python_version']}")
    print("Trials:          Median of 5 runs per workload")
    print("-" * 80)

    print("\n### STAGE-BY-STAGE TIMING BREAKDOWN\n")
    print(
        "| Points | Occupied Cells | 1. Indexing (ms) | 2. Cell Pop (ms) | 3. Map Handoff (ms) | Total E2E (ms) | Total E2E Rate |"
    )
    print(
        "| -----: | -------------: | ---------------: | ---------------: | ------------------: | -------------: | -------------: |"
    )
    for r in results:
        print(
            f"| {r['num_points']:,} | {r['occupied_cells']:,} "
            f"| {r['stage1_indexing_ms']:.2f} ms "
            f"| {r['stage2_cell_creation_ms']:.2f} ms "
            f"| {r['stage3_mapping_handoff_ms']:.2f} ms "
            f"| **{r['total_e2e_ms']:.2f} ms** "
            f"| **{r['e2e_rate_pts_sec']:,.0f} pts/s** |"
        )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    workloads = [10000, 50000, 100000]
    data = profile_pipeline(workloads)
    print_report(data)

    out_file = PROJECT_ROOT / "outputs" / "mapping_integration_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Results saved to: {out_file}\n")
