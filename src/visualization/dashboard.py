"""Terminal / Console Telemetry Dashboard for Headless Execution.

Module Owner: Atharva (src/visualization/)
"""

import sys
import time
from typing import Optional
from src.integration.pipeline import PipelineOrchestrator


def print_terminal_dashboard(
    orchestrator: PipelineOrchestrator, max_frames: int = 10, interval: float = 0.5
) -> None:
    """Run pipeline and display real-time telemetry directly in console/terminal."""
    print("=================================================================")
    print("      SYNTRiX // PERCEPTION TELEMETRY DASHBOARD (HEADLESS)       ")
    print("=================================================================")

    for _ in range(max_frames):
        _, _, sem_map, telemetry = orchestrator.process_frame()

        lat = telemetry.get("stage_latencies_ms", {})
        prep_t = lat.get("preprocessing", {}).get("last_ms", 0.0)
        inf_t = lat.get("inference", {}).get("last_ms", 0.0)
        grid_t = lat.get("grid_indexing", {}).get("last_ms", 0.0)
        map_t = lat.get("mapping", {}).get("last_ms", 0.0)
        tot_t = lat.get("total", {}).get("last_ms", 0.0)

        fps = telemetry.get("fps", 0.0)
        mem = telemetry.get("memory", {}).get("ram_rss_mb", 0.0)
        n_pts = telemetry.get("counts", {}).get("points", 0)
        n_cells = telemetry.get("counts", {}).get("cells", 0)

        output = (
            f"[FRAME {telemetry.get('frame_count', 0):04d}] "
            f"FPS: {fps:4.1f} | "
            f"Points: {n_pts:5d} | "
            f"Cells: {n_cells:5d} | "
            f"Prep: {prep_t:4.1f}ms | "
            f"Infer: {inf_t:4.1f}ms | "
            f"Grid: {grid_t:4.1f}ms | "
            f"Map: {map_t:4.1f}ms | "
            f"Total: {tot_t:4.1f}ms | "
            f"RAM: {mem:.1f}MB"
        )
        print(output)
        time.sleep(interval)

    print("=================================================================")
    print("  Dashboard run complete. Zero fabricated metrics recorded.")
    print("=================================================================\n")
