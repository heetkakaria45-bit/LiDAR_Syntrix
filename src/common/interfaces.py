"""
Abstract Base Classes (ABCs) and Interface Contracts for all Pipeline Stages.

Every stage owner implements their designated interface.
Interfaces are strictly decoupled to allow parallel development and mock testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union
import numpy as np

from src.common.types import (
    FoveationLevelConfig,
    GridCell,
    PointCloudFrame,
    SemanticPointCloud,
    SemanticMap,
    TraversabilityScore,
    TelemetryMetrics,
)


class IPreprocessor(ABC):
    """
    Preprocessing Stage Interface (Owner: Amulya - src/preprocessing/)
    Responsibility: Clean, filter, and normalize raw LiDAR frames.
    """

    @abstractmethod
    def process(self, raw_frame: PointCloudFrame) -> PointCloudFrame:
        """
        Filters NaNs/Infs, crops to operational range, removes ego-vehicle noise.
        """
        raise NotImplementedError

    @abstractmethod
    def downsample(self, frame: PointCloudFrame, voxel_size_m: float) -> PointCloudFrame:
        """Optional uniform or distance-adaptive downsampling."""
        raise NotImplementedError


class ISemanticPerception(ABC):
    """
    Semantic Perception Stage Interface (Owner: Vedant - src/perception/)
    Responsibility: Predict per-point semantic class and confidence.
    Model-independent: PointNet++, SparseConv, or lightweight backbones.
    """

    @abstractmethod
    def infer(self, frame: PointCloudFrame) -> SemanticPointCloud:
        """
        Executes semantic segmentation inference on the input point cloud frame.
        """
        raise NotImplementedError

    @abstractmethod
    def load_model(self, weights_path: str) -> None:
        """Loads model weights/checkpoint."""
        raise NotImplementedError


class IFoveatedGrid(ABC):
    """
    Foveated Spatial Representation Interface (Owner: Manashri - src/foveated_grid/)
    Responsibility: Multi-resolution spatial partitioning, deterministic coordinate
    mapping, boundary handling, fast insertion and spatial queries.
    """

    @abstractmethod
    def get_level_for_distance(self, distance_m: float) -> int:
        """Determines the foveation level index [0..3] for a given Euclidean distance."""
        raise NotImplementedError

    @abstractmethod
    def world_to_cell(self, x_m: float, y_m: float, level: int) -> Tuple[int, int]:
        """Converts continuous metric world coordinates (X, Y) to discrete grid cell indices."""
        raise NotImplementedError

    @abstractmethod
    def cell_to_world(self, ix: int, iy: int, level: int) -> Tuple[float, float]:
        """Converts discrete grid cell indices to continuous cell center coordinates (X, Y)."""
        raise NotImplementedError

    @abstractmethod
    def insert_points(self, semantic_cloud: SemanticPointCloud) -> None:
        """Partitions and indexes points across foveated multi-resolution levels."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Resets the grid data structure."""
        raise NotImplementedError


class ISemantic25DMapper(ABC):
    """
    Semantic 2.5D Mapping Stage Interface (Owner: Heet - src/mapping/)
    Responsibility: Aggregate spatial points into 2.5D cells with elevation (min_z, max_z, mean_z),
    roughness, occupancy, and semantic consensus.
    """

    @abstractmethod
    def update_map(self, semantic_cloud: SemanticPointCloud) -> SemanticMap:
        """Aggregates a semantic point cloud into the 2.5D semantic map."""
        raise NotImplementedError

    @abstractmethod
    def get_map(self) -> SemanticMap:
        """Retrieves the current semantic 2.5D map."""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Resets the map state."""
        raise NotImplementedError


class ITraversabilityAnalyzer(ABC):
    """
    Terrain and Traversability Stage Interface (Owner: Heet - src/mapping/)
    Responsibility: Evaluate step height, slope, roughness, and semantic penalty to determine
    drivability of cells.
    """

    @abstractmethod
    def evaluate_cell(self, cell: GridCell) -> TraversabilityScore:
        """Computes traversability score and cost for a single grid cell."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_map(self, semantic_map: SemanticMap) -> Dict[Tuple[int, int, int], TraversabilityScore]:
        """Computes traversability scores for all cells in the map."""
        raise NotImplementedError


class ITemporalMapUpdater(ABC):
    """
    Temporal Map Update Stage Interface (Owner: Heet - src/mapping/)
    Responsibility: Fuse successive map frames over time, update observation counts,
    and apply temporal decay/filtering.
    """

    @abstractmethod
    def integrate_frame(self, current_map: SemanticMap, new_cloud: SemanticPointCloud) -> SemanticMap:
        """Temporally integrates a new semantic frame into the running map."""
        raise NotImplementedError


class IPipelineIntegrator(ABC):
    """
    Real-Time Pipeline Integration Interface (Owner: Atharva - src/integration/)
    Responsibility: Orchestrate end-to-end execution from raw input to updated map
    and telemetry logging.
    """

    @abstractmethod
    def step(self, raw_frame: PointCloudFrame) -> Tuple[SemanticMap, TelemetryMetrics]:
        """Executes a single end-to-end pipeline step and returns updated map + telemetry."""
        raise NotImplementedError

    @abstractmethod
    def run_stream(self, frame_iterator: Iterator[PointCloudFrame]) -> Generator[Tuple[SemanticMap, TelemetryMetrics], None, None]:
        """Executes the pipeline over a streaming sequence of frames."""
        raise NotImplementedError


class IVisualizer(ABC):
    """
    Perception Control Center Visualization Interface (Owner: Atharva - src/visualization/)
    Responsibility: Render multi-layer views (live LiDAR, semantics, elevation, traversability,
    foveation zones, uniform vs foveated telemetry).
    """

    @abstractmethod
    def render_frame(self, semantic_map: SemanticMap, telemetry: TelemetryMetrics) -> None:
        """Renders the current map state and telemetry."""
        raise NotImplementedError

    @abstractmethod
    def set_view_mode(self, mode_name: str) -> None:
        """Switches display mode (e.g. ELEVATION, SEMANTICS, TRAVERSABILITY, FOVEATION)."""
        raise NotImplementedError


class IBenchmarkEngine(ABC):
    """
    Benchmarking & Validation Stage Interface (Owner: Himisha - src/evaluation/)
    Responsibility: Measure pipeline latency, FPS, memory, compare Uniform vs Foveated grids,
    and output reproducible metrics. Zero fabrication.
    """

    @abstractmethod
    def benchmark_pipeline(
        self,
        integrator: IPipelineIntegrator,
        dataset: Iterator[PointCloudFrame],
        num_frames: int = 100,
    ) -> Dict[str, Any]:
        """Executes standardized benchmark suite over a test sequence."""
        raise NotImplementedError

    @abstractmethod
    def compare_uniform_vs_foveated(
        self,
        test_frames: List[PointCloudFrame],
    ) -> Dict[str, Any]:
        """Runs side-by-side comparison between uniform high-resolution grid and foveated grid."""
        raise NotImplementedError


class IDatasetAdapter(ABC):
    """
    Dataset Adapter Interface (Common)
    Responsibility: Load external datasets (SemanticKITTI, nuScenes, Waymo) and map them
    to standard PointCloudFrame and SemanticPointCloud with project taxonomy.
    """

    @abstractmethod
    def __len__(self) -> int:
        """Total number of frames."""
        raise NotImplementedError

    @abstractmethod
    def get_frame(self, index: int) -> PointCloudFrame:
        """Retrieves raw PointCloudFrame at given index."""
        raise NotImplementedError

    @abstractmethod
    def map_semantic_label(self, raw_label: int) -> int:
        """Maps dataset-specific semantic label to project SemanticClass ID (0-7)."""
        raise NotImplementedError


class ISyntheticSceneGenerator(ABC):
    """
    Deterministic Synthetic Scene Interface (Common / Evaluation)
    Responsibility: Generate deterministic geometric scenes (curbs, slopes, potholes, obstacles).
    """

    @abstractmethod
    def generate_scene(self, scene_type: str, **params: Any) -> PointCloudFrame:
        """Generates synthetic PointCloudFrame for testing."""
        raise NotImplementedError
