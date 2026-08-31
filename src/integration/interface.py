"""
Pipeline Integration Interface Scaffolding.
Module Owner: Atharva (src/integration/)

Responsibility:
    - Orchestrate end-to-end processing pipeline:
      Raw LiDAR -> Preprocessing -> Perception -> Foveated Spatial Indexing -> 2.5D Mapping -> Traversability.
    - Measure component latencies and system telemetry (Zero fabrication).
    - Provide synchronous step() and streaming run_stream() interfaces.
"""

from __future__ import annotations

import time
from typing import Generator, Iterator, Optional, Tuple

from src.common.config import SystemConfig, load_config
from src.common.interfaces import (
    IFoveatedGrid,
    IPipelineIntegrator,
    IPreprocessor,
    ISemantic25DMapper,
    ISemanticPerception,
)
from src.common.types import (
    PointCloudFrame,
    SemanticMap,
    TelemetryMetrics,
)


class PipelineIntegrator(IPipelineIntegrator):
    """
    End-to-End Pipeline Integrator scaffold.
    To be fully wired by Atharva in Phase G.
    """

    def __init__(
        self,
        config: Optional[SystemConfig] = None,
        preprocessor: Optional[IPreprocessor] = None,
        perception: Optional[ISemanticPerception] = None,
        foveated_grid: Optional[IFoveatedGrid] = None,
        mapper: Optional[ISemantic25DMapper] = None,
    ) -> None:
        self.config = config or load_config()
        self.preprocessor = preprocessor
        self.perception = perception
        self.foveated_grid = foveated_grid
        self.mapper = mapper

    def step(self, raw_frame: PointCloudFrame) -> Tuple[SemanticMap, TelemetryMetrics]:
        """
        Executes one full synchronous pipeline step.
        Full module coordination scheduled for Phase G.
        """
        if not isinstance(raw_frame, PointCloudFrame):
            raise TypeError(f"Expected PointCloudFrame, got {type(raw_frame)}")

        t0 = time.perf_counter()

        # Step 1: Preprocessing
        if self.preprocessor is not None:
            clean_frame = self.preprocessor.process(raw_frame)
        else:
            clean_frame = raw_frame

        # Step 2: Semantic Perception
        if self.perception is not None:
            sem_cloud = self.perception.infer(clean_frame)
        else:
            raise RuntimeError("Perception module not bound.")

        # Step 3: Foveated Spatial Insertion (optional indexing)
        if self.foveated_grid is not None:
            self.foveated_grid.insert_points(sem_cloud)

        # Step 4: 2.5D Mapping
        if self.mapper is not None:
            updated_map = self.mapper.update_map(sem_cloud)
        else:
            raise RuntimeError("Mapping module not bound.")

        dt = time.perf_counter() - t0
        telemetry = TelemetryMetrics(
            total_latency_ms=dt * 1000.0,
            fps=(1.0 / dt) if dt > 0 else 0.0,
            input_point_count=raw_frame.num_points,
            grid_cell_count=updated_map.cell_count,
            timestamp=raw_frame.timestamp,
        )

        return updated_map, telemetry

    def run_stream(self, frame_iterator: Iterator[PointCloudFrame]) -> Generator[Tuple[SemanticMap, TelemetryMetrics], None, None]:
        for frame in frame_iterator:
            yield self.step(frame)
