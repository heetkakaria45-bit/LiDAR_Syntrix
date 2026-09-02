"""System Integration & Real-Time Optimization Module.

Module Owner: Atharva (src/integration/)
Responsibilities:
    - End-to-end pipeline execution and module wiring
    - Runtime orchestration and asynchronous/threaded pipelines
    - Latency profiling and memory management (anti-fabrication telemetry)
    - Fallback management (REAL -> PRECOMPUTED -> SYNTHETIC)
    - Sequence playback controls
"""

from src.integration.pipeline import PipelineMode, PipelineOrchestrator
from src.integration.playback import SequencePlayer
from src.integration.telemetry import TelemetryProfiler

__all__ = [
    "PipelineMode",
    "PipelineOrchestrator",
    "SequencePlayer",
    "TelemetryProfiler",
]
