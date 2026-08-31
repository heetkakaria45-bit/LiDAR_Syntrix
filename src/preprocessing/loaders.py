"""Dataset and Point Cloud Ingestion Loaders.

Module Owner: Amulya (Preprocessing)

Provides efficient loaders for:
    - SemanticKITTI / KITTI Velodyne binary files (.bin: float32 [x, y, z, intensity])
    - In-memory raw point and intensity arrays
    - Standardized PointCloudFrame creation complying with CONTRACTS.md
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union
import numpy as np

from src.contracts import PointCloudFrame
from src.preprocessing.filters import validate_and_sanitize_points


def load_kitti_bin(
    file_path: Union[str, Path],
    frame_id: str = "lidar_top",
    timestamp: float = 0.0,
    sensor_pose: Optional[np.ndarray] = None,
    sanitize: bool = True,
) -> PointCloudFrame:
    """Load a SemanticKITTI / KITTI binary (.bin) LiDAR frame.

    KITTI binary format:
        Contiguous binary array of float32 values. Each point has 4 components:
        [x, y, z, intensity/remission].

    Coordinate convention:
        KITTI Velodyne coordinate system:
            +X: Forward
            +Y: Left
            +Z: Up
        Units: Meters
        This matches the frozen project coordinate convention directly.

    Args:
        file_path: Path to the .bin point cloud file.
        frame_id: Reference frame identifier (default: "lidar_top").
        timestamp: Capture epoch timestamp in seconds.
        sensor_pose: Optional 4x4 rigid transformation matrix [R | t].
                     Defaults to 4x4 identity matrix.
        sanitize: If True, filters out non-finite (NaN, Inf) values.

    Returns:
        frame: Validated PointCloudFrame instance.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If file size is not a multiple of 16 bytes (4 float32 values per point)
                    or if data cannot be parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"LiDAR binary file not found: {file_path}")

    file_size = os.path.getsize(path)
    if file_size % 16 != 0:
        raise ValueError(
            f"Corrupted KITTI binary file: size {file_size} bytes is not a multiple of "
            f"16 bytes (4 float32 values per point)."
        )

    # Fast binary ingestion using numpy
    raw_data = np.fromfile(path, dtype=np.float32)
    if raw_data.size == 0:
        empty_pts = np.zeros((0, 3), dtype=np.float32)
        empty_int = np.zeros((0,), dtype=np.float32)
        pose = np.eye(4, dtype=np.float64) if sensor_pose is None else sensor_pose
        return PointCloudFrame(
            points=empty_pts,
            intensity=empty_int,
            timestamp=timestamp,
            frame_id=frame_id,
            sensor_pose=pose,
        )

    cloud_data = raw_data.reshape(-1, 4)
    points = cloud_data[:, :3].astype(np.float32, copy=False)
    intensity = cloud_data[:, 3].astype(np.float32, copy=False)

    if sanitize:
        points, intensity = validate_and_sanitize_points(points, intensity)

    pose = np.eye(4, dtype=np.float64) if sensor_pose is None else sensor_pose

    return PointCloudFrame(
        points=points,
        intensity=intensity,
        timestamp=timestamp,
        frame_id=frame_id,
        sensor_pose=pose,
    )


def load_raw_points(
    points: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    frame_id: str = "lidar_top",
    timestamp: float = 0.0,
    sensor_pose: Optional[np.ndarray] = None,
    sanitize: bool = True,
) -> PointCloudFrame:
    """Create a validated PointCloudFrame from in-memory numpy arrays.

    Args:
        points: (N, 3) array of point coordinates in meters.
        intensity: Optional (N,) array of reflection intensities.
        frame_id: Frame identifier string.
        timestamp: Frame timestamp in seconds.
        sensor_pose: Optional (4, 4) sensor pose matrix.
        sanitize: If True, removes NaN and Inf values.

    Returns:
        frame: Standardized PointCloudFrame instance.

    Raises:
        ValueError: If input arrays fail dimensional or type validation.
    """
    if sanitize:
        points, intensity = validate_and_sanitize_points(points, intensity)
    else:
        if not isinstance(points, np.ndarray):
            points = np.asarray(points, dtype=np.float32)
        if intensity is not None and not isinstance(intensity, np.ndarray):
            intensity = np.asarray(intensity, dtype=np.float32)

    pose = np.eye(4, dtype=np.float64) if sensor_pose is None else sensor_pose

    return PointCloudFrame(
        points=points,
        intensity=intensity,
        timestamp=timestamp,
        frame_id=frame_id,
        sensor_pose=pose,
    )
