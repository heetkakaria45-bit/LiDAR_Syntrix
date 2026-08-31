"""
End-to-End Pipeline Interface Smoke Test.

Verifies that standard data contracts flow seamlessly across mock interfaces:
DatasetAdapter -> Preprocessor -> Perception -> Spatial Indexing -> Mapping -> Integrator -> Visualizer -> Benchmark.
"""

import unittest

from src.common.config import load_config
from src.common.mocks import (
    MockBenchmarkEngine,
    MockDatasetAdapter,
    MockFoveatedGrid,
    MockPipelineIntegrator,
    MockPreprocessor,
    MockSemantic25DMapper,
    MockSemanticPerception,
    MockVisualizer,
)
from src.common.types import SemanticMap, TelemetryMetrics


class TestPipelineInterfaceSmoke(unittest.TestCase):
    """Smoke test ensuring full pipeline integration contracts function together."""

    def setUp(self) -> None:
        self.config = load_config()
        self.dataset = MockDatasetAdapter(num_frames=5, points_per_frame=200)
        self.preprocessor = MockPreprocessor(self.config)
        self.perception = MockSemanticPerception(self.config)
        self.grid = MockFoveatedGrid(self.config)
        self.mapper = MockSemantic25DMapper(self.config)
        self.visualizer = MockVisualizer(self.config)
        self.benchmark = MockBenchmarkEngine(self.config)

        self.integrator = MockPipelineIntegrator(
            config=self.config,
            preprocessor=self.preprocessor,
            perception=self.perception,
            mapper=self.mapper,
        )

    def test_single_step_smoke(self) -> None:
        raw_frame = self.dataset.get_frame(0)
        sem_map, telemetry = self.integrator.step(raw_frame)

        self.assertIsInstance(sem_map, SemanticMap)
        self.assertIsInstance(telemetry, TelemetryMetrics)
        self.assertEqual(telemetry.input_point_count, 200)
        self.assertGreater(telemetry.total_latency_ms, 0.0)

        # Visualizer interface call
        self.visualizer.render_frame(sem_map, telemetry)
        self.assertEqual(self.visualizer.last_rendered_cell_count, sem_map.cell_count)

    def test_streaming_smoke(self) -> None:
        stream = (self.dataset.get_frame(i) for i in range(len(self.dataset)))
        results = list(self.integrator.run_stream(stream))

        self.assertEqual(len(results), 5)
        for sem_map, tel in results:
            self.assertIsInstance(sem_map, SemanticMap)
            self.assertIsInstance(tel, TelemetryMetrics)

    def test_benchmark_engine_smoke(self) -> None:
        stream = (self.dataset.get_frame(i) for i in range(len(self.dataset)))
        report = self.benchmark.benchmark_pipeline(self.integrator, stream, num_frames=3)

        self.assertIn("num_frames_evaluated", report)
        self.assertEqual(report["num_frames_evaluated"], 3)
        self.assertIn("avg_latency_ms", report)
        self.assertIn("fps", report)


if __name__ == "__main__":
    unittest.main()
