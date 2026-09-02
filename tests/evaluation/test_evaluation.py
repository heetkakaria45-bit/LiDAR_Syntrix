"""Unit tests for Evaluation & Benchmarking module."""

import numpy as np
from src.evaluation import (
    BenchmarkRunner,
    compute_distance_stratified_metrics,
    compute_elevation_rmse,
    compute_semantic_iou,
)


def test_semantic_iou_calculation() -> None:
    """Ensure IoU and mIoU are computed accurately."""
    gt = np.array([0, 0, 1, 1, 2, 2], dtype=np.int32)
    pred = np.array([0, 0, 1, 0, 2, 2], dtype=np.int32)

    res = compute_semantic_iou(pred, gt, num_classes=3)
    assert res["mIoU"] > 0.6
    assert res["per_class_iou"][0] < 1.0  # FP for class 0
    assert res["per_class_iou"][2] == 1.0  # Perfect class 2


def test_elevation_rmse_calculation() -> None:
    """Ensure elevation RMSE and MAE calculations match formula."""
    gt_z = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    pred_z = np.array([0.1, -0.1, 0.1, -0.1], dtype=np.float32)

    res = compute_elevation_rmse(pred_z, gt_z)
    assert abs(res["rmse"] - 0.1) < 1e-4
    assert abs(res["mae"] - 0.1) < 1e-4


def test_uniform_vs_foveated_benchmark() -> None:
    """Ensure BenchmarkRunner produces correct cell count and memory comparisons."""
    stats = BenchmarkRunner.compare_uniform_vs_foveated(max_radius=100.0, uniform_resolution=0.05)

    assert stats["uniform_grid"]["total_cells"] == 16000000
    assert stats["foveated_grid"]["total_cells"] < 1000000
    assert stats["comparison"]["memory_savings_pct"] >= 90.0
    assert stats["comparison"]["cell_count_reduction_factor"] >= 15.0
