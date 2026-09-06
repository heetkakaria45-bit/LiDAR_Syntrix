"""Comparative Benchmark Suite: Uniform High-Resolution vs. Foveated Multi-Ring Grid.

Module Owner: Himisha (src/evaluation/)
"""

from typing import Any, Dict, List, Optional
import numpy as np


class BenchmarkRunner:
    """Automated benchmark runner for quantitative performance, accuracy and memory comparisons."""

    @staticmethod
    def compare_uniform_vs_foveated(
        max_radius: float = 100.0,
        uniform_resolution: float = 0.05,
        bytes_per_cell: int = 64,
    ) -> Dict[str, Any]:
        """Compute theoretical memory footprint and cell allocation metrics.

        Contrasts:
            - Uniform 5 cm grid covering [-100, 100]m x [-100, 100]m
            - Foveated Multi-Ring grid (5cm, 10cm, 25cm, 50cm)

        All metrics are strictly tagged with provenance ('CALCULATED' or 'THEORETICAL').
        """
        # 1. Uniform grid (200m x 200m @ 5cm)
        uniform_dim = int(np.ceil((2.0 * max_radius) / uniform_resolution))
        uniform_total_cells = uniform_dim * uniform_dim  # 16,000,000 cells
        uniform_memory_mb = (uniform_total_cells * bytes_per_cell) / (1024 * 1024)

        # 2. Foveated multi-ring grid
        ring_specs = [
            {"name": "near", "r_min": 0.0, "r_max": 10.0, "res": 0.05},
            {"name": "mid_near", "r_min": 10.0, "r_max": 25.0, "res": 0.10},
            {"name": "mid", "r_min": 25.0, "r_max": 50.0, "res": 0.25},
            {"name": "far", "r_min": 50.0, "r_max": 100.0, "res": 0.50},
        ]

        foveated_cells_by_ring = {}
        total_foveated_cells = 0

        for r in ring_specs:
            annulus_area = np.pi * (r["r_max"] ** 2 - r["r_min"] ** 2)
            cell_area = r["res"] ** 2
            ring_cells = int(np.ceil(annulus_area / cell_area))
            foveated_cells_by_ring[r["name"]] = ring_cells
            total_foveated_cells += ring_cells

        foveated_memory_mb = (total_foveated_cells * bytes_per_cell) / (1024 * 1024)
        memory_reduction_pct = (
            (uniform_memory_mb - foveated_memory_mb) / uniform_memory_mb
        ) * 100.0

        return {
            "provenance": {
                "uniform_memory": "THEORETICAL",
                "foveated_cell_count": "CALCULATED",
                "memory_savings": "CALCULATED",
            },
            "uniform_grid": {
                "resolution_m": uniform_resolution,
                "dimension": [uniform_dim, uniform_dim],
                "total_cells": uniform_total_cells,
                "memory_mb": round(uniform_memory_mb, 2),
                "metric_type": "THEORETICAL",
            },
            "foveated_grid": {
                "total_cells": total_foveated_cells,
                "cells_by_ring": foveated_cells_by_ring,
                "memory_mb": round(foveated_memory_mb, 2),
                "metric_type": "CALCULATED",
            },
            "comparison": {
                "cell_count_reduction_factor": round(
                    uniform_total_cells / total_foveated_cells, 1
                ),
                "memory_savings_pct": round(memory_reduction_pct, 2),
                "metric_type": "CALCULATED",
            },
        }

    @staticmethod
    def run_live_pipeline_benchmark(
        orchestrator: Any,
        num_frames: int = 5,
    ) -> Dict[str, Any]:
        """Execute live measured benchmark across N frames on the active pipeline.

        Returns strictly MEASURED runtime metrics.
        """
        import time

        latencies_ms = []
        stage_timings_acc: Dict[str, List[float]] = {}
        eval_metrics_list = []

        for _ in range(max(1, num_frames)):
            t_start = time.perf_counter()
            _, _, sem_map, telemetry = orchestrator.process_frame()
            dt_ms = (time.perf_counter() - t_start) * 1000.0
            latencies_ms.append(dt_ms)

            stages = telemetry.get("stage_latencies_ms", {})
            for stage_name, stage_info in stages.items():
                if isinstance(stage_info, dict):
                    stage_val = stage_info.get("last_ms", stage_info.get("mean_ms", 0.0))
                else:
                    stage_val = float(stage_info)
                if stage_name not in stage_timings_acc:
                    stage_timings_acc[stage_name] = []
                stage_timings_acc[stage_name].append(stage_val)

            if "evaluation" in sem_map.metadata:
                eval_metrics_list.append(sem_map.metadata["evaluation"])

        mean_latency = float(np.mean(latencies_ms))
        mean_fps = round(1000.0 / max(mean_latency, 1e-4), 1)
        mean_stages = {
            k: round(float(np.mean(v)), 2) for k, v in stage_timings_acc.items()
        }

        theoretical_comp = BenchmarkRunner.compare_uniform_vs_foveated()

        return {
            "provenance": {
                "mean_fps": "MEASURED",
                "mean_latency_ms": "MEASURED",
                "stage_latencies_ms": "MEASURED",
                "memory_rss_mb": "MEASURED",
                "theoretical_comparison": "CALCULATED",
            },
            "live_measurements": {
                "frames_evaluated": len(latencies_ms),
                "mean_fps": mean_fps,
                "mean_latency_ms": round(mean_latency, 2),
                "min_latency_ms": round(float(np.min(latencies_ms)), 2),
                "max_latency_ms": round(float(np.max(latencies_ms)), 2),
                "stage_latencies_ms": mean_stages,
                "memory_rss_mb": telemetry.get("memory_rss_mb", 0.0),
                "metric_type": "MEASURED",
            },
            "theoretical_comparison": theoretical_comp,
        }
