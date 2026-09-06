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
    assert "provenance" in stats


def test_live_pipeline_benchmark_execution() -> None:
    """Ensure BenchmarkRunner executes live benchmark and measures runtime stats."""
    from src.integration.pipeline import PipelineOrchestrator

    orchestrator = PipelineOrchestrator()
    live_stats = BenchmarkRunner.run_live_pipeline_benchmark(orchestrator, num_frames=2)

    assert "live_measurements" in live_stats
    meas = live_stats["live_measurements"]
    assert meas["frames_evaluated"] == 2
    assert meas["mean_fps"] > 0.0
    assert meas["mean_latency_ms"] > 0.0
    assert meas["metric_type"] == "MEASURED"
    assert "provenance" in live_stats


def test_comparative_benchmark_fair_baseline(tmp_path) -> None:
    """Ensure run_comparative_benchmark executes fair comparison and outputs JSON results."""
    out_file = str(tmp_path / "bench_test.json")
    results = BenchmarkRunner.run_comparative_benchmark(
        scene_type="flat_road", num_runs=2, save_to_file=True, output_path=out_file
    )

    assert "uniform_vs_foveated" in results
    uvf = results["uniform_vs_foveated"]
    assert uvf["uniform_cell_count"] > 0
    assert uvf["foveated_cell_count"] > 0
    assert uvf["cell_reduction_ratio"] > 1.0
    assert uvf["processing_time_uniform_ms"] > 0.0
    assert uvf["processing_time_foveated_ms"] > 0.0
    assert "distance_bins" in results
    assert len(results["distance_bins"]) == 4
    assert "metadata" in results
    assert "provenance" in results
    assert results["metadata"]["hardware"]["platform"] != ""
