"""Performance Telemetry & Real-Time Profiler.

Module Owner: Atharva (src/integration/)
Strict Principle:
    All metrics recorded must be actual measurements. No fabricated numbers.
"""

from collections import deque
import os
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    import resource
    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False


class TelemetryProfiler:
    """Real-time profiler tracking per-stage latency, FPS, memory usage, and throughput."""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._stage_starts: Dict[str, float] = {}
        self._stage_latencies: Dict[str, deque] = {
            "preprocessing": deque(maxlen=history_size),
            "inference": deque(maxlen=history_size),
            "grid_indexing": deque(maxlen=history_size),
            "mapping": deque(maxlen=history_size),
            "hazard_analysis": deque(maxlen=history_size),
            "rendering": deque(maxlen=history_size),
            "total": deque(maxlen=history_size),
        }
        self._frame_times = deque(maxlen=history_size)
        self._process = psutil.Process(os.getpid()) if _HAS_PSUTIL else None
        self.last_frame_timestamp = time.perf_counter()

    def start_stage(self, stage_name: str) -> None:
        """Mark start timestamp of a pipeline stage."""
        self._stage_starts[stage_name] = time.perf_counter()

    def stop_stage(self, stage_name: str) -> float:
        """Mark completion of a stage and record measured latency in milliseconds."""
        start = self._stage_starts.get(stage_name)
        if start is None:
            return 0.0
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if stage_name not in self._stage_latencies:
            self._stage_latencies[stage_name] = deque(maxlen=self.history_size)
        self._stage_latencies[stage_name].append(elapsed_ms)
        return elapsed_ms

    def record_frame_end(self, total_duration_ms: Optional[float] = None) -> None:
        """Record the end of a full frame processing cycle."""
        now = time.perf_counter()
        delta = now - self.last_frame_timestamp
        self.last_frame_timestamp = now
        if delta > 0:
            self._frame_times.append(delta)
        if total_duration_ms is not None:
            self._stage_latencies["total"].append(total_duration_ms)

    def get_current_fps(self) -> float:
        """Compute real measured Frames Per Second over recent history."""
        if not self._frame_times:
            return 0.0
        mean_frame_time = sum(self._frame_times) / len(self._frame_times)
        return float(1.0 / mean_frame_time) if mean_frame_time > 0 else 0.0

    def get_memory_usage_mb(self) -> Dict[str, float]:
        """Get actual process resident set size (RSS) and virtual memory in MB."""
        if _HAS_PSUTIL and self._process is not None:
            try:
                mem_info = self._process.memory_info()
                return {
                    "ram_rss_mb": round(mem_info.rss / (1024 * 1024), 2),
                    "ram_vms_mb": round(mem_info.vms / (1024 * 1024), 2),
                }
            except Exception:
                pass

        if _HAS_RESOURCE:
            try:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                # On macOS, ru_maxrss is in bytes; on Linux, in kilobytes
                scale = 1024 * 1024 if sys.platform == "darwin" else 1024
                rss_mb = usage.ru_maxrss / scale
                return {
                    "ram_rss_mb": round(rss_mb, 2),
                    "ram_vms_mb": round(rss_mb, 2),
                }
            except Exception:
                pass

        return {"ram_rss_mb": 0.0, "ram_vms_mb": 0.0}

    def get_telemetry_snapshot(
        self, point_count: int = 0, cell_count: int = 0
    ) -> Dict[str, Any]:
        """Generate a complete structured telemetry snapshot for UI and benchmarks."""
        stage_summary: Dict[str, Dict[str, float]] = {}

        for stage, history in self._stage_latencies.items():
            if len(history) > 0:
                vals = list(history)
                stage_summary[stage] = {
                    "last_ms": round(vals[-1], 2),
                    "mean_ms": round(sum(vals) / len(vals), 2),
                    "max_ms": round(max(vals), 2),
                    "min_ms": round(min(vals), 2),
                }
            else:
                stage_summary[stage] = {"last_ms": 0.0, "mean_ms": 0.0, "max_ms": 0.0, "min_ms": 0.0}

        return {
            "fps": round(self.get_current_fps(), 1),
            "memory": self.get_memory_usage_mb(),
            "stage_latencies_ms": stage_summary,
            "counts": {
                "points": point_count,
                "cells": cell_count,
            },
            "timestamp": time.time(),
        }
