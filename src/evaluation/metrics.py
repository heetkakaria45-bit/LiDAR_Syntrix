"""Evaluation Metrics for Semantic Segmentation and 2.5D Elevation Mapping.

Module Owner: Himisha (src/evaluation/)
Responsibilities:
    - Quantitative benchmarking (mIoU, Precision, Recall, F1)
    - Geometric elevation error analysis (RMSE, MAE)
    - Distance-stratified accuracy evaluation (0-10m, 10-25m, 25-50m, 50-100m)
    - Anti-fabrication deterministic evaluation protocols
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def compute_semantic_iou(
    pred_classes: np.ndarray,
    gt_classes: np.ndarray,
    num_classes: int = 8,
) -> Dict[str, Any]:
    """Compute per-class Intersection-over-Union (IoU) and mean IoU (mIoU).

    Args:
        pred_classes: 1D array of predicted class integers (0..7).
        gt_classes: 1D array of ground truth class integers (0..7).
        num_classes: Total taxonomy classes (default: 8).

    Returns:
        Dictionary containing per-class IoU, precision, recall, and overall mIoU.
    """
    ious: Dict[int, float] = {}
    precisions: Dict[int, float] = {}
    recalls: Dict[int, float] = {}
    valid_ious: List[float] = []

    for c in range(num_classes):
        tp = int(np.sum((pred_classes == c) & (gt_classes == c)))
        fp = int(np.sum((pred_classes == c) & (gt_classes != c)))
        fn = int(np.sum((pred_classes != c) & (gt_classes == c)))

        denominator = tp + fp + fn
        if denominator == 0:
            iou = 1.0  # Perfect agreement on empty class
        else:
            iou = float(tp / denominator)
            valid_ious.append(iou)

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 1.0

        ious[c] = iou
        precisions[c] = prec
        recalls[c] = rec

    miou = float(np.mean(valid_ious)) if valid_ious else 1.0

    return {
        "per_class_iou": ious,
        "per_class_precision": precisions,
        "per_class_recall": recalls,
        "mIoU": miou,
    }


def compute_elevation_rmse(
    pred_elevations: np.ndarray,
    gt_elevations: np.ndarray,
) -> Dict[str, float]:
    """Compute Elevation Root Mean Square Error (RMSE) and Mean Absolute Error (MAE).

    Args:
        pred_elevations: Estimated surface Z coordinates in meters.
        gt_elevations: Ground truth surface Z coordinates in meters.

    Returns:
        Dict with 'rmse' and 'mae' in meters.
    """
    if pred_elevations.size == 0 or gt_elevations.size == 0:
        return {"rmse": 0.0, "mae": 0.0}

    errors = pred_elevations - gt_elevations
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mae = float(np.mean(np.abs(errors)))

    return {"rmse": rmse, "mae": mae}


def compute_distance_stratified_metrics(
    distances: np.ndarray,
    pred_elevations: np.ndarray,
    gt_elevations: np.ndarray,
    bins: Optional[List[Tuple[float, float, str]]] = None,
) -> Dict[str, Dict[str, float]]:
    """Compute elevation accuracy stratified across concentric distance bins."""
    if bins is None:
        bins = [
            (0.0, 10.0, "near_0_10m"),
            (10.0, 25.0, "mid_near_10_25m"),
            (25.0, 50.0, "mid_25_50m"),
            (50.0, 100.0, "far_50_100m"),
        ]

    results: Dict[str, Dict[str, float]] = {}

    for min_d, max_d, label in bins:
        mask = (distances >= min_d) & (distances < max_d)
        if np.any(mask):
            errs = compute_elevation_rmse(pred_elevations[mask], gt_elevations[mask])
            results[label] = {
                "rmse": errs["rmse"],
                "mae": errs["mae"],
                "point_count": int(np.sum(mask)),
            }
        else:
            results[label] = {"rmse": 0.0, "mae": 0.0, "point_count": 0}

    return results
