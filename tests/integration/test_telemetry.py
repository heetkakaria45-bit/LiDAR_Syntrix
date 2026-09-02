"""Unit tests for Telemetry Profiler and Anti-Fabrication Measurements."""

import time
from src.integration.telemetry import TelemetryProfiler


def test_telemetry_profiler_timing() -> None:
    """Ensure profiler records actual measured elapsed time."""
    profiler = TelemetryProfiler()

    profiler.start_stage("test_stage")
    time.sleep(0.01)  # 10ms
    elapsed = profiler.stop_stage("test_stage")

    assert elapsed >= 8.0  # At least ~8ms measured
    snap = profiler.get_telemetry_snapshot()
    assert snap["stage_latencies_ms"]["test_stage"]["last_ms"] > 0.0


def test_telemetry_memory_tracking() -> None:
    """Ensure process memory RSS is reported and positive."""
    profiler = TelemetryProfiler()
    mem = profiler.get_memory_usage_mb()

    assert "ram_rss_mb" in mem
    assert mem["ram_rss_mb"] > 0.0
