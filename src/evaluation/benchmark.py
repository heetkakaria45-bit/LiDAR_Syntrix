"""Comparative Benchmark Suite: Uniform High-Resolution vs. Foveated Multi-Ring Grid.

Module Owner: Himisha (src/evaluation/)
"""

from typing import Any, Dict, List, Optional
import numpy as np


class BenchmarkRunner:
    """Automated benchmark runner for quantitative performance and memory comparisons."""

    @staticmethod
    def compare_uniform_vs_foveated(
        max_radius: float = 100.0,
        uniform_resolution: float = 0.05,
    ) -> Dict[str, Any]:
        """Compute theoretical memory footprint and cell allocation metrics.

        Contrasts:
            - Uniform 5 cm grid covering [-100, 100]m x [-100, 100]m
            - Foveated Multi-Ring grid (5cm, 10cm, 25cm, 50cm)
        """
        # 1. Uniform grid (200m x 200m @ 5cm)
        uniform_dim = int(np.ceil((2.0 * max_radius) / uniform_resolution))
        uniform_total_cells = uniform_dim * uniform_dim  # 16,000,000 cells
        # Assuming ~64 bytes per dense cell struct (elevation, class, occupancy, conf, etc.)
        bytes_per_cell = 64
        uniform_memory_mb = (uniform_total_cells * bytes_per_cell) / (1024 * 1024)

        # 2. Foveated multi-ring grid
        # Ring 0: 0-10m @ 5cm -> circle area pi * 10^2 = 314 m^2 -> 314 / (0.05^2) = 125,663 cells
        # Ring 1: 10-25m @ 10cm -> pi*(25^2 - 10^2) = 1,649 m^2 -> 1,649 / (0.10^2) = 164,933 cells
        # Ring 2: 25-50m @ 25cm -> pi*(50^2 - 25^2) = 5,890 m^2 -> 5,890 / (0.25^2) = 94,247 cells
        # Ring 3: 50-100m @ 50cm -> pi*(100^2 - 50^2) = 23,561 m^2 -> 23,561 / (0.50^2) = 94,247 cells
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
            "uniform_grid": {
                "resolution_m": uniform_resolution,
                "dimension": [uniform_dim, uniform_dim],
                "total_cells": uniform_total_cells,
                "memory_mb": round(uniform_memory_mb, 2),
            },
            "foveated_grid": {
                "total_cells": total_foveated_cells,
                "cells_by_ring": foveated_cells_by_ring,
                "memory_mb": round(foveated_memory_mb, 2),
            },
            "comparison": {
                "cell_count_reduction_factor": round(
                    uniform_total_cells / total_foveated_cells, 1
                ),
                "memory_savings_pct": round(memory_reduction_pct, 2),
            },
        }
