"""Unit Tests for Dataset Ingestion and Point Cloud Loaders.

Module Owner: Amulya (Member 2)

Tests:
    - SemanticKITTI / KITTI .bin binary file loading
    - Ingestion error handling (corrupted file size, missing file)
    - In-memory raw array loading into PointCloudFrame
    - Empty file handling
"""

from pathlib import Path
import numpy as np
import pytest

from src.contracts import PointCloudFrame
from src.preprocessing.loaders import load_kitti_bin, load_raw_points


def test_load_kitti_bin_valid(tmp_path: Path) -> None:
    """Test loading a mock KITTI binary file containing N x 4 float32 values."""
    bin_file = tmp_path / "000000.bin"
    n_points = 250
    # Shape: (250, 4) with [x, y, z, intensity]
    rng = np.random.default_rng(42)
    fake_cloud = rng.uniform(-20.0, 20.0, (n_points, 4)).astype(np.float32)
    fake_cloud.tofile(bin_file)

    frame = load_kitti_bin(bin_file, frame_id="kitti_velo", timestamp=123.456)

    assert isinstance(frame, PointCloudFrame)
    assert frame.points.shape == (n_points, 3)
    assert frame.points.dtype == np.float32
    assert frame.intensity is not None
    assert frame.intensity.shape == (n_points,)
    assert frame.intensity.dtype == np.float32
    assert frame.frame_id == "kitti_velo"
    assert frame.timestamp == 123.456
    np.testing.assert_allclose(frame.points, fake_cloud[:, :3])
    np.testing.assert_allclose(frame.intensity, fake_cloud[:, 3])


def test_load_kitti_bin_corrupted_size(tmp_path: Path) -> None:
    """Test that a binary file with byte length not divisible by 16 raises ValueError."""
    bad_file = tmp_path / "bad.bin"
    # Write 13 bytes (not divisible by 16)
    with open(bad_file, "wb") as f:
        f.write(b"x" * 13)

    with pytest.raises(ValueError, match="Corrupted KITTI binary file"):
        load_kitti_bin(bad_file)


def test_load_kitti_bin_missing_file() -> None:
    """Test that a non-existent file path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="LiDAR binary file not found"):
        load_kitti_bin("non_existent_file_path_12345.bin")


def test_load_kitti_bin_empty_file(tmp_path: Path) -> None:
    """Test that an empty 0-byte file returns a valid empty PointCloudFrame."""
    empty_file = tmp_path / "empty.bin"
    empty_file.touch()

    frame = load_kitti_bin(empty_file)
    assert isinstance(frame, PointCloudFrame)
    assert frame.points.shape == (0, 3)
    assert frame.intensity is not None and frame.intensity.shape == (0,)


def test_load_raw_points() -> None:
    """Test creating a PointCloudFrame directly from numpy arrays."""
    pts = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    intensity = np.array([0.2, 0.8], dtype=np.float32)

    frame = load_raw_points(pts, intensity, frame_id="custom_lidar", timestamp=50.0)

    assert isinstance(frame, PointCloudFrame)
    assert frame.points.shape == (2, 3)
    assert frame.intensity is not None and frame.intensity.shape == (2,)
    assert frame.frame_id == "custom_lidar"
    assert frame.timestamp == 50.0
