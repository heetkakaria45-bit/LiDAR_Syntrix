"""LiDAR Point Cloud Preprocessing Pipeline.

Module Owner: Amulya
Responsibilities:
    - PointCloudFrame validation and sanity checks
    - Executing RangeFilter -> OutlierFilter -> VoxelDownsampler -> GroundFilter
    - Producing standardized PreprocessedPointCloud and PreprocessingStats contracts
    - Invariant enforcement: output <= input, ground + non_ground == output
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import yaml

from src.contracts import PointCloudFrame, PreprocessedPointCloud, PreprocessingStats
from src.preprocessing.filters import GroundFilter, OutlierFilter, RangeFilter, VoxelDownsampler


class PreprocessingPipeline:
    """End-to-End LiDAR Preprocessing & Point Cloud Quality Pipeline."""

    def __init__(
        self,
        config: Optional[Union[Dict[str, Any], Path, str]] = None,
        range_filter: Optional[RangeFilter] = None,
        outlier_filter: Optional[OutlierFilter] = None,
        voxel_downsampler: Optional[VoxelDownsampler] = None,
        ground_filter: Optional[GroundFilter] = None,
    ) -> None:
        """Initialize pipeline from configuration dict/file or explicit filter instances."""
        cfg_dict: Optional[Dict[str, Any]] = None
        if config is not None:
            cfg_dict = self._load_config(config)
        else:
            try:
                root_cfg = Path(__file__).resolve().parent.parent.parent / "configs" / "default_config.yaml"
                if root_cfg.is_file():
                    with open(root_cfg, "r", encoding="utf-8") as f:
                        cfg_dict = yaml.safe_load(f)
            except Exception:
                cfg_dict = None

        if cfg_dict and "preprocessing" in cfg_dict:
            p_cfg = cfg_dict["preprocessing"]

            # Range Filter
            rf_cfg = p_cfg.get("range_filter", {})
            self.range_filter = range_filter or RangeFilter(
                min_range=float(rf_cfg.get("min_range", 0.5)),
                max_range=float(rf_cfg.get("max_range", 100.0)),
            )

            # Outlier Filter
            of_cfg = p_cfg.get("outlier_removal", {})
            self.outlier_filter = outlier_filter or OutlierFilter(
                enabled=bool(of_cfg.get("enabled", True)),
                radius=float(of_cfg.get("radius", 1.0)),
                min_neighbors=int(of_cfg.get("min_neighbors", 1)),
            )

            # Voxel Downsampler
            vd_cfg = p_cfg.get("voxel_downsample", {})
            self.voxel_downsampler = voxel_downsampler or VoxelDownsampler(
                enabled=bool(vd_cfg.get("enabled", True)),
                voxel_size=float(vd_cfg.get("voxel_size", vd_cfg.get("leaf_size", 0.05))),
            )

            # Ground Filter
            gf_cfg = p_cfg.get("ground_filter", {})
            self.ground_filter = ground_filter or GroundFilter(
                enabled=bool(gf_cfg.get("enabled", True)),
                height_threshold=float(gf_cfg.get("height_threshold", 0.20)),
            )
        else:
            self.range_filter = range_filter or RangeFilter(min_range=0.5, max_range=100.0)
            self.outlier_filter = outlier_filter or OutlierFilter(enabled=True, radius=1.0, min_neighbors=1)
            self.voxel_downsampler = voxel_downsampler or VoxelDownsampler(enabled=True, voxel_size=0.05)
            self.ground_filter = ground_filter or GroundFilter(enabled=True, height_threshold=0.20)

    def _load_config(self, config_source: Union[Dict[str, Any], Path, str]) -> Dict[str, Any]:
        """Load configuration dictionary from dict or YAML file."""
        if isinstance(config_source, dict):
            return config_source
        p = Path(config_source)
        if not p.is_file():
            # Try finding configs/default_config.yaml relative to project root
            root_cfg = Path(__file__).resolve().parent.parent.parent / "configs" / "default_config.yaml"
            if root_cfg.is_file():
                p = root_cfg
            else:
                raise FileNotFoundError(f"Configuration file not found at {config_source}")
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def process(
        self,
        frame_or_points: Union[PointCloudFrame, np.ndarray],
        intensity: Optional[np.ndarray] = None,
        frame_id: str = "frame_0000",
        timestamp: Optional[float] = None,
    ) -> PreprocessedPointCloud:
        """Execute full preprocessing pipeline on a raw LiDAR frame.

        Pipeline Stages:
            1. Input Validation & NaN/Inf Sanitization
            2. Radial Range Filtering [min_range, max_range]
            3. Outlier / Isolated Noise Removal
            4. Voxel Grid Downsampling
            5. Geometric Ground / Non-Ground Separation

        Args:
            frame_or_points: PointCloudFrame dataclass or (N, 3) numpy array.
            intensity: Optional (N,) intensity array (if passing numpy array).
            frame_id: Frame identifier string.
            timestamp: Timestamp in seconds.

        Returns:
            PreprocessedPointCloud contract with complete PreprocessingStats.
        """
        start_time = time.perf_counter()

        # 1. Unpack & Validate Input
        if isinstance(frame_or_points, PointCloudFrame):
            raw_pts = frame_or_points.points
            raw_int = frame_or_points.intensity
            f_id = frame_or_points.frame_id
            t_stamp = frame_or_points.timestamp
            sensor_pose = frame_or_points.sensor_pose
        else:
            raw_pts = np.asarray(frame_or_points, dtype=np.float32)
            raw_int = np.asarray(intensity, dtype=np.float32) if intensity is not None else None
            f_id = frame_id
            t_stamp = timestamp if timestamp is not None else time.time()
            sensor_pose = np.eye(4, dtype=np.float64)

        if raw_pts.ndim != 2 or raw_pts.shape[1] != 3:
            raise ValueError(f"points must have shape (N, 3), got {raw_pts.shape}")

        raw_count = len(raw_pts)

        # Handle empty point cloud gracefully
        if raw_count == 0:
            stats = PreprocessingStats(
                raw_points=0,
                range_filtered_points=0,
                outlier_filtered_points=0,
                voxel_downsampled_points=0,
                ground_points=0,
                non_ground_points=0,
                processing_time_ms=(time.perf_counter() - start_time) * 1000.0,
                reduction_percentage=0.0,
            )
            return PreprocessedPointCloud(
                points=np.empty((0, 3), dtype=np.float32),
                ground_mask=np.empty((0,), dtype=bool),
                timestamp=t_stamp,
                frame_id=f_id,
                stats=stats,
                intensity=None,
                sensor_pose=sensor_pose,
            )

        # Sanitize non-finite values (NaN / Inf)
        finite_mask = np.all(np.isfinite(raw_pts), axis=1)
        valid_pts = raw_pts[finite_mask]
        valid_int = raw_int[finite_mask] if raw_int is not None else None

        # 2. Range Filtering
        range_pts, range_int, _ = self.range_filter.filter(valid_pts, valid_int)
        range_count = len(range_pts)

        # 3. Outlier Removal
        outlier_pts, outlier_int, _ = self.outlier_filter.filter(range_pts, range_int)
        outlier_count = len(outlier_pts)

        # 4. Voxel Downsampling
        voxel_pts, voxel_int, _ = self.voxel_downsampler.filter(outlier_pts, outlier_int)
        voxel_count = len(voxel_pts)

        # 5. Ground / Non-Ground Separation
        ground_pts, non_ground_pts, ground_mask = self.ground_filter.filter(voxel_pts, voxel_int)
        ground_count = len(ground_pts)
        non_ground_count = len(non_ground_pts)

        # Invariant Verification: ground + non_ground == voxel_count
        assert ground_count + non_ground_count == voxel_count, (
            f"Invariant violation: ground ({ground_count}) + non_ground ({non_ground_count}) "
            f"!= total processed ({voxel_count})"
        )
        assert voxel_count <= raw_count, (
            f"Invariant violation: output ({voxel_count}) > input ({raw_count})"
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        reduction_pct = 100.0 * (1.0 - (voxel_count / max(1, raw_count)))

        stats = PreprocessingStats(
            raw_points=raw_count,
            range_filtered_points=range_count,
            outlier_filtered_points=outlier_count,
            voxel_downsampled_points=voxel_count,
            ground_points=ground_count,
            non_ground_points=non_ground_count,
            processing_time_ms=elapsed_ms,
            reduction_percentage=reduction_pct,
        )

        return PreprocessedPointCloud(
            points=voxel_pts,
            ground_mask=ground_mask,
            timestamp=t_stamp,
            frame_id=f_id,
            stats=stats,
            intensity=voxel_int,
            sensor_pose=sensor_pose,
        )
