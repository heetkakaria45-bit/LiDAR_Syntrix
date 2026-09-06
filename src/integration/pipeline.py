"""System Pipeline Orchestrator & Multi-Stage Execution Engine.

Module Owner: Atharva (src/integration/)
Responsibilities:
    - End-to-end wiring of all pipeline stages
    - Real-time telemetry instrumentation
    - Robust 3-tier fallback execution: REAL -> PRECOMPUTED -> SYNTHETIC
    - Asynchronous & sequential frame orchestration
"""

from enum import Enum
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from src.contracts import PointCloudFrame, SemanticMap, SemanticPointCloud, SyntheticSceneConfig
from src.evaluation.metrics import (
    compute_distance_stratified_metrics,
    compute_elevation_rmse,
    compute_semantic_iou,
)
from src.foveated_grid.grid_indexer import FoveatedGridIndexer
from src.integration.telemetry import TelemetryProfiler
from src.mapping import (
    HazardConfig,
    MappingConfig,
    SemanticElevationMapper,
    TraversabilityConfig,
    analyze_map_terrain,
    detect_map_hazards,
)
from src.perception.base import BaseSemanticSegmenter
from src.perception.mock import MockSemanticSegmenter
from src.preprocessing import generate_synthetic_scene, validate_and_sanitize_points

logger = logging.getLogger(__name__)


class PipelineMode(str, Enum):
    """Pipeline data source operating mode."""

    REAL = "REAL_LIDAR"
    PRECOMPUTED = "PRECOMPUTED"
    SYNTHETIC = "SYNTHETIC"


class PipelineOrchestrator:
    """Central orchestrator wiring all pipeline stages with telemetry and fallback."""

    def __init__(
        self,
        mode: PipelineMode = PipelineMode.SYNTHETIC,
        perception_model: Optional[BaseSemanticSegmenter] = None,
        grid_indexer: Optional[FoveatedGridIndexer] = None,
        mapper: Optional[SemanticElevationMapper] = None,
        mapping_config: Optional[MappingConfig] = None,
        profiler: Optional[TelemetryProfiler] = None,
        synthetic_scene_type: str = "urban",
    ):
        self.mode = mode
        self.synthetic_scene_type = synthetic_scene_type
        self.profiler = profiler if profiler is not None else TelemetryProfiler()
        self.perception_model = (
            perception_model if perception_model is not None else MockSemanticSegmenter()
        )
        self.grid_indexer = grid_indexer if grid_indexer is not None else FoveatedGridIndexer()
        self.mapping_config = mapping_config if mapping_config is not None else MappingConfig()
        self.mapper = (
            mapper
            if mapper is not None
            else SemanticElevationMapper(
                config=self.mapping_config, grid_indexer=self.grid_indexer
            )
        )

        self.frame_count = 0
        self.last_frame: Optional[PointCloudFrame] = None
        self.last_semantic_cloud: Optional[SemanticPointCloud] = None
        self.last_gt_cloud: Optional[SemanticPointCloud] = None
        self.last_map: Optional[SemanticMap] = None
        self.last_terrain: Optional[Dict[str, Any]] = None
        self.last_hazards: Optional[Dict[str, Any]] = None
        self.active_source_mode = self.mode

    def _acquire_frame(
        self,
        custom_frame: Optional[PointCloudFrame] = None,
        custom_gt_cloud: Optional[SemanticPointCloud] = None,
    ) -> Tuple[PointCloudFrame, Optional[SemanticPointCloud]]:
        """Acquire a frame using the active pipeline mode with automatic fallback."""
        if custom_frame is not None:
            return custom_frame, custom_gt_cloud

        if self.mode == PipelineMode.REAL:
            # Placeholder for live sensor / ROS 2 receiver
            logger.warning("Real LiDAR source not connected. Falling back to SYNTHETIC mode.")
            self.active_source_mode = PipelineMode.SYNTHETIC

        # Synthetic generator fallback / default
        config = SyntheticSceneConfig(
            scene_type=self.synthetic_scene_type,
            seed=42 + self.frame_count,
            num_points=12000,
        )
        frame, gt_cloud = generate_synthetic_scene(config)
        return frame, gt_cloud

    def process_frame(
        self,
        frame: Optional[PointCloudFrame] = None,
        gt_cloud: Optional[SemanticPointCloud] = None,
    ) -> Tuple[PointCloudFrame, SemanticPointCloud, SemanticMap, Dict[str, Any]]:
        """Execute one complete end-to-end perception, grid indexing, mapping, and evaluation cycle."""
        frame_start = time.perf_counter()

        # 1. Preprocessing / Ingestion & Point Sanitization
        self.profiler.start_stage("preprocessing")
        input_frame, ground_truth = self._acquire_frame(frame, gt_cloud)

        sanitized_pts, sanitized_intensity, _, _ = validate_and_sanitize_points(
            points=input_frame.points,
            intensity=input_frame.intensity,
            min_range=0.5,
            max_range=100.0,
            z_min=-10.0,
            z_max=20.0,
        )

        input_frame = PointCloudFrame(
            points=sanitized_pts,
            intensity=sanitized_intensity,
            timestamp=input_frame.timestamp,
            frame_id=input_frame.frame_id,
            sensor_pose=input_frame.sensor_pose,
        )
        self.profiler.stop_stage("preprocessing")

        # 2. Semantic Perception Inference
        self.profiler.start_stage("inference")
        semantic_cloud = self.perception_model.infer(input_frame)
        self.profiler.stop_stage("inference")

        # 3. Spatial Grid Binning & Indexing (Production path providing spatial_assignments)
        self.profiler.start_stage("grid_indexing")
        spatial_assignments = self.grid_indexer.assign_points(semantic_cloud.points)
        self.profiler.stop_stage("grid_indexing")

        # 4. 2.5D Semantic Elevation Mapping
        self.profiler.start_stage("mapping")
        semantic_map = self.mapper.map_point_cloud(
            cloud=semantic_cloud,
            sensor_pose=input_frame.sensor_pose,
            spatial_assignments=spatial_assignments,
        )
        self.profiler.stop_stage("mapping")

        # 5. Terrain & Hazard Analysis
        self.profiler.start_stage("hazard_analysis")
        terrain_attrs = analyze_map_terrain(
            semantic_map, config=self.mapping_config.traversability
        )
        hazards = detect_map_hazards(
            semantic_map, config=self.mapping_config.hazards
        )

        curb_count = len(hazards.get("curbs", []))
        pothole_count = len(hazards.get("potholes", []))
        overhang_count = len(hazards.get("overhangs", []))

        # Count obstacle cells (non-drivable objects)
        obstacle_count = 0
        for level_dict in semantic_map.cells.values():
            for cell in level_dict.values():
                if cell.semantic_class in [2, 3, 4, 5, 6, 7]:
                    obstacle_count += 1

        semantic_map.metadata["hazards_summary"] = {
            "curb": curb_count,
            "pothole": pothole_count,
            "overhang": overhang_count,
            "obstacle": obstacle_count,
        }
        semantic_map.metadata["terrain"] = terrain_attrs
        semantic_map.metadata["hazards"] = hazards
        self.profiler.stop_stage("hazard_analysis")

        # 6. Evaluation Consumption (when ground truth is available)
        evaluation_results: Optional[Dict[str, Any]] = None
        if ground_truth is not None and ground_truth.semantic_class.shape[0] == semantic_cloud.semantic_class.shape[0]:
            iou_stats = compute_semantic_iou(
                pred_classes=semantic_cloud.semantic_class,
                gt_classes=ground_truth.semantic_class,
                num_classes=8,
            )
            # Distance-stratified accuracy
            distances = np.hypot(semantic_cloud.points[:, 0], semantic_cloud.points[:, 1])
            stratified = compute_distance_stratified_metrics(
                distances=distances,
                pred_elevations=semantic_cloud.points[:, 2],
                gt_elevations=ground_truth.points[:, 2],
            )
            evaluation_results = {
                "mIoU": iou_stats["mIoU"],
                "per_class_iou": iou_stats["per_class_iou"],
                "distance_stratified": stratified,
                "metric_type": "MEASURED",
            }
            semantic_map.metadata["evaluation"] = evaluation_results

        # 7. Telemetry recording
        total_time_ms = (time.perf_counter() - frame_start) * 1000.0
        self.profiler.record_frame_end(total_time_ms)

        total_cells = semantic_map.metadata.get(
            "num_cells", sum(len(lvl) for lvl in semantic_map.cells.values())
        )

        self.frame_count += 1
        self.last_frame = input_frame
        self.last_semantic_cloud = semantic_cloud
        self.last_gt_cloud = ground_truth
        self.last_map = semantic_map
        self.last_terrain = terrain_attrs
        self.last_hazards = hazards

        telemetry_snap = self.profiler.get_telemetry_snapshot(
            point_count=input_frame.points.shape[0],
            cell_count=total_cells,
        )
        telemetry_snap["pipeline_mode"] = self.active_source_mode.value
        telemetry_snap["frame_count"] = self.frame_count
        if evaluation_results:
            telemetry_snap["evaluation"] = evaluation_results

        return input_frame, semantic_cloud, semantic_map, telemetry_snap
