"""
Mock implementations and Stubs for independent developer workflows.

These stubs adhere strictly to the stage ABCs and validate data contracts without
implementing major production algorithms or fabricating domain outputs.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union
import numpy as np

from src.common.types import (
    FoveationLevelConfig,
    GridCell,
    PointCloudFrame,
    SemanticClass,
    SemanticPointCloud,
    SemanticMap,
    TraversabilityScore,
    TelemetryMetrics,
)
from src.common.interfaces import (
    IBenchmarkEngine,
    IDatasetAdapter,
    IFoveatedGrid,
    IPipelineIntegrator,
    IPreprocessor,
    ISemantic25DMapper,
    ISemanticPerception,
    ISyntheticSceneGenerator,
    ITemporalMapUpdater,
    ITraversabilityAnalyzer,
    IVisualizer,
)
from src.common.config import SystemConfig, load_config


class MockPreprocessor(IPreprocessor):
    """
    Mock LiDAR Preprocessor.
    Validates frame contracts and passes through data without complex filtering.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def process(self, raw_frame: PointCloudFrame) -> PointCloudFrame:
        if not isinstance(raw_frame, PointCloudFrame):
            raise TypeError(f"Expected PointCloudFrame, got {type(raw_frame)}")
        # Contract pass-through: preserves valid coordinates and metadata
        return PointCloudFrame(
            points=raw_frame.points.copy(),
            intensity=raw_frame.intensity.copy() if raw_frame.intensity is not None else None,
            timestamp=raw_frame.timestamp,
            frame_id=raw_frame.frame_id,
            sensor_pose=raw_frame.sensor_pose.copy(),
        )

    def downsample(self, frame: PointCloudFrame, voxel_size_m: float) -> PointCloudFrame:
        if voxel_size_m <= 0:
            raise ValueError(f"voxel_size_m must be > 0, got {voxel_size_m}")
        return self.process(frame)


class MockSemanticPerception(ISemanticPerception):
    """
    Mock Semantic Perception Engine.
    Assigns unclassified default labels (0) to test downstream contract compatibility.
    Does NOT contain trained ML weights or fabricated segmentation heuristics.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()
        self._weights_loaded: bool = False

    def load_model(self, weights_path: str) -> None:
        self._weights_loaded = True

    def infer(self, frame: PointCloudFrame) -> SemanticPointCloud:
        if not isinstance(frame, PointCloudFrame):
            raise TypeError(f"Expected PointCloudFrame, got {type(frame)}")

        N = frame.num_points
        # Default zero-initialization for interface contracts
        default_labels = np.zeros(N, dtype=np.uint8)
        default_confidence = np.ones(N, dtype=np.float32)

        return SemanticPointCloud(
            points=frame.points.copy(),
            semantic_labels=default_labels,
            confidence=default_confidence,
            intensity=frame.intensity.copy() if frame.intensity is not None else None,
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            sensor_pose=frame.sensor_pose.copy(),
        )


class MockFoveatedGrid(IFoveatedGrid):
    """
    Mock Foveated Spatial Indexing.
    Implements pure geometric level lookup and discrete coordinate mapping.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()
        self.levels = self.config.foveation.levels

    def get_level_for_distance(self, distance_m: float) -> int:
        if distance_m < 0.0 or distance_m > self.config.foveation.max_range_m:
            return -1  # Out of operational range

        for lvl in self.levels:
            is_outer = (lvl.level == len(self.levels) - 1)
            if lvl.contains_distance(distance_m, is_outermost=is_outer):
                return lvl.level
        return len(self.levels) - 1

    def world_to_cell(self, x_m: float, y_m: float, level: int) -> Tuple[int, int]:
        if level < 0 or level >= len(self.levels):
            raise IndexError(f"Level {level} out of range (0..{len(self.levels)-1})")
        res = self.levels[level].cell_resolution_m
        ix = int(np.floor(x_m / res))
        iy = int(np.floor(y_m / res))
        return (ix, iy)

    def cell_to_world(self, ix: int, iy: int, level: int) -> Tuple[float, float]:
        if level < 0 or level >= len(self.levels):
            raise IndexError(f"Level {level} out of range (0..{len(self.levels)-1})")
        res = self.levels[level].cell_resolution_m
        cx = (ix + 0.5) * res
        cy = (iy + 0.5) * res
        return (cx, cy)

    def insert_points(self, semantic_cloud: SemanticPointCloud) -> None:
        if not isinstance(semantic_cloud, SemanticPointCloud):
            raise TypeError(f"Expected SemanticPointCloud, got {type(semantic_cloud)}")

    def clear(self) -> None:
        pass


class MockSemantic25DMapper(ISemantic25DMapper):
    """
    Mock Semantic 2.5D Mapper.
    Returns standard SemanticMap container populated with valid contract structures.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()
        self._current_map = SemanticMap(
            resolution_levels=self.config.foveation.levels,
            timestamp=0.0,
            frame_id=0,
        )

    def update_map(self, semantic_cloud: SemanticPointCloud) -> SemanticMap:
        if not isinstance(semantic_cloud, SemanticPointCloud):
            raise TypeError(f"Expected SemanticPointCloud, got {type(semantic_cloud)}")
        self._current_map.timestamp = semantic_cloud.timestamp
        self._current_map.frame_id = semantic_cloud.frame_id
        self._current_map.sensor_pose = semantic_cloud.sensor_pose.copy()
        return self._current_map

    def get_map(self) -> SemanticMap:
        return self._current_map

    def reset(self) -> None:
        self._current_map = SemanticMap(
            resolution_levels=self.config.foveation.levels,
            timestamp=0.0,
            frame_id=0,
        )


class MockTraversabilityAnalyzer(ITraversabilityAnalyzer):
    """
    Mock Traversability Analyzer.
    Evaluates basic geometric and semantic defaults.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def evaluate_cell(self, cell: GridCell) -> TraversabilityScore:
        is_ground = SemanticClass.is_ground(cell.semantic_class)
        is_traversable = is_ground and (cell.roughness <= self.config.mapping.roughness_threshold_m)
        cost = 0.0 if is_traversable else 1.0
        return TraversabilityScore(
            is_traversable=is_traversable,
            cost=cost,
            slope_rad=0.0,
            step_height_m=cell.height_span,
            roughness_m=cell.roughness,
            semantic_penalty=0.0 if is_ground else 1.0,
        )

    def evaluate_map(self, semantic_map: SemanticMap) -> Dict[Tuple[int, int, int], TraversabilityScore]:
        results: Dict[Tuple[int, int, int], TraversabilityScore] = {}
        for key, cell in semantic_map.cells.items():
            results[key] = self.evaluate_cell(cell)
        return results


class MockTemporalMapUpdater(ITemporalMapUpdater):
    """
    Mock Temporal Map Updater.
    Updates map timestamp and retains cells.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def integrate_frame(self, current_map: SemanticMap, new_cloud: SemanticPointCloud) -> SemanticMap:
        current_map.timestamp = new_cloud.timestamp
        current_map.frame_id = new_cloud.frame_id
        return current_map


class MockPipelineIntegrator(IPipelineIntegrator):
    """
    Mock Pipeline Integrator for end-to-end contract smoke testing.
    Executes mock stages sequentially and logs real wall-clock timing.
    """

    def __init__(
        self,
        config: Optional[SystemConfig] = None,
        preprocessor: Optional[IPreprocessor] = None,
        perception: Optional[ISemanticPerception] = None,
        mapper: Optional[ISemantic25DMapper] = None,
    ) -> None:
        self.config = config or load_config()
        self.preprocessor = preprocessor or MockPreprocessor(self.config)
        self.perception = perception or MockSemanticPerception(self.config)
        self.mapper = mapper or MockSemantic25DMapper(self.config)

    def step(self, raw_frame: PointCloudFrame) -> Tuple[SemanticMap, TelemetryMetrics]:
        t0 = time.perf_counter()

        t_p0 = time.perf_counter()
        clean_frame = self.preprocessor.process(raw_frame)
        t_p1 = time.perf_counter()

        t_i0 = time.perf_counter()
        sem_cloud = self.perception.infer(clean_frame)
        t_i1 = time.perf_counter()

        t_m0 = time.perf_counter()
        updated_map = self.mapper.update_map(sem_cloud)
        t_m1 = time.perf_counter()

        t_total = time.perf_counter() - t0

        telemetry = TelemetryMetrics(
            preprocessing_latency_ms=(t_p1 - t_p0) * 1000.0,
            inference_latency_ms=(t_i1 - t_i0) * 1000.0,
            projection_latency_ms=0.0,
            mapping_latency_ms=(t_m1 - t_m0) * 1000.0,
            rendering_latency_ms=0.0,
            total_latency_ms=t_total * 1000.0,
            fps=(1.0 / t_total) if t_total > 0 else 0.0,
            input_point_count=raw_frame.num_points,
            grid_cell_count=updated_map.cell_count,
            timestamp=raw_frame.timestamp,
        )

        return updated_map, telemetry

    def run_stream(self, frame_iterator: Iterator[PointCloudFrame]) -> Generator[Tuple[SemanticMap, TelemetryMetrics], None, None]:
        for frame in frame_iterator:
            yield self.step(frame)


class MockVisualizer(IVisualizer):
    """Mock visualizer for testing interface calls without spawning GUI windows."""

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()
        self.current_mode = self.config.visualization.default_view_mode
        self.last_rendered_cell_count: int = 0

    def render_frame(self, semantic_map: SemanticMap, telemetry: TelemetryMetrics) -> None:
        self.last_rendered_cell_count = semantic_map.cell_count

    def set_view_mode(self, mode_name: str) -> None:
        self.current_mode = mode_name


class MockBenchmarkEngine(IBenchmarkEngine):
    """Mock benchmark engine implementing interface contracts."""

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()

    def benchmark_pipeline(
        self,
        integrator: IPipelineIntegrator,
        dataset: Iterator[PointCloudFrame],
        num_frames: int = 10,
    ) -> Dict[str, Any]:
        count = 0
        total_lat = 0.0
        for frame in dataset:
            if count >= num_frames:
                break
            _, tel = integrator.step(frame)
            total_lat += tel.total_latency_ms
            count += 1

        avg_lat = total_lat / count if count > 0 else 0.0
        return {
            "num_frames_evaluated": count,
            "avg_latency_ms": avg_lat,
            "fps": (1000.0 / avg_lat) if avg_lat > 0 else 0.0,
        }

    def compare_uniform_vs_foveated(
        self,
        test_frames: List[PointCloudFrame],
    ) -> Dict[str, Any]:
        return {
            "frames_tested": len(test_frames),
            "uniform_grid_cells_approx": 0,
            "foveated_grid_cells_approx": 0,
            "memory_reduction_ratio": 0.0,
        }


class MockDatasetAdapter(IDatasetAdapter):
    """Mock dataset adapter providing deterministic test frames."""

    def __init__(self, num_frames: int = 5, points_per_frame: int = 1000) -> None:
        self.num_frames = num_frames
        self.points_per_frame = points_per_frame

    def __len__(self) -> int:
        return self.num_frames

    def get_frame(self, index: int) -> PointCloudFrame:
        if index < 0 or index >= self.num_frames:
            raise IndexError(f"Index {index} out of bounds (0..{self.num_frames-1})")
        # Generates deterministic coordinates: X in [1, 50], Y in [-20, 20], Z in [-1, 2]
        np.random.seed(42 + index)
        x = np.random.uniform(0.5, 60.0, size=(self.points_per_frame, 1)).astype(np.float32)
        y = np.random.uniform(-25.0, 25.0, size=(self.points_per_frame, 1)).astype(np.float32)
        z = np.random.uniform(-1.5, 2.0, size=(self.points_per_frame, 1)).astype(np.float32)
        points = np.hstack([x, y, z])
        intensity = np.random.uniform(0, 255, size=(self.points_per_frame,)).astype(np.float32)

        return PointCloudFrame(
            points=points,
            intensity=intensity,
            timestamp=float(index) * 0.1,
            frame_id=index,
        )

    def map_semantic_label(self, raw_label: int) -> int:
        # Default identity mapping bounded to taxonomy
        return min(max(raw_label, 0), 7)


class MockSyntheticSceneGenerator(ISyntheticSceneGenerator):
    """Deterministic synthetic scene generator stub for test fixtures."""

    def generate_scene(self, scene_type: str, **params: Any) -> PointCloudFrame:
        num_points = params.get("num_points", 500)
        # Generate basic geometric ground plane
        xs = np.linspace(0.0, 50.0, int(np.sqrt(num_points)), dtype=np.float32)
        ys = np.linspace(-20.0, 20.0, int(np.sqrt(num_points)), dtype=np.float32)
        xx, yy = np.meshgrid(xs, ys)
        pts = np.vstack([xx.ravel(), yy.ravel(), np.zeros(xx.size, dtype=np.float32)]).T
        return PointCloudFrame(points=pts, timestamp=0.0, frame_id="synthetic_0")
