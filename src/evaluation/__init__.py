"""Evaluation & Benchmarking Module.

Module Owner: Himisha (src/evaluation/)
Responsibilities:
    - Quantitative benchmarking: mIoU, precision, recall, elevation RMSE
    - Distance-binned spatial error analysis
    - Real-time pipeline latency & resource profiling
    - Uniform vs. Foveated comparative validation studies
"""

from src.evaluation.benchmark import BenchmarkRunner
from src.evaluation.metrics import (
    compute_distance_stratified_metrics,
    compute_elevation_rmse,
    compute_semantic_iou,
)

__all__ = [
    "BenchmarkRunner",
    "compute_distance_stratified_metrics",
    "compute_elevation_rmse",
    "compute_semantic_iou",
]
