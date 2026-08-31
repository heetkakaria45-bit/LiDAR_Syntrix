"""Core Cell Aggregation Algorithms for 2.5D Semantic Elevation Mapping.

Module Owner: Heet (Member 4)
Responsibilities:
    - Elevation aggregation (median, min_z, max_z, mean, lowest)
    - Semantic label fusion via confidence-weighted voting
    - Interpretable surface roughness (sample standard deviation of Z)
    - Calibrated occupancy probability
    - GridCell generation conforming to CONTRACTS.md
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.contracts import GridCell

_LOG_NUM_CLASSES = math.log(8.0)


def compute_elevation_bounds(
    z_coords: np.ndarray,
    strategy: str = "median",
) -> Tuple[float, float, float]:
    """Compute robust elevation, min_z, and max_z for a collection of Z coordinates.

    Args:
        z_coords: 1D array of valid float Z coordinates.
        strategy: Aggregation strategy ('median', 'mean', or 'lowest').

    Returns:
        (elevation, min_z, max_z) as floats.

    Raises:
        ValueError: If z_coords is empty or contains no finite values.
    """
    n = z_coords.size
    if n == 0:
        raise ValueError("Cannot compute elevation bounds on empty or all-non-finite Z array.")

    # Fast path for single-point array
    if n == 1:
        v = float(z_coords[0])
        if not math.isfinite(v):
            raise ValueError("Cannot compute elevation bounds on empty or all-non-finite Z array.")
        return v, v, v

    # Fast path for 2-point array
    if n == 2:
        v0 = float(z_coords[0])
        v1 = float(z_coords[1])
        f0 = math.isfinite(v0)
        f1 = math.isfinite(v1)
        if f0 and f1:
            min_z = v0 if v0 < v1 else v1
            max_z = v0 if v0 > v1 else v1
            if strategy == "lowest":
                elevation = min_z
            elif strategy == "mean" or strategy == "median":
                elevation = (v0 + v1) / 2.0
            else:
                elevation = (v0 + v1) / 2.0
            return elevation, min_z, max_z
        elif f0:
            return v0, v0, v0
        elif f1:
            return v1, v1, v1
        else:
            raise ValueError("Cannot compute elevation bounds on empty or all-non-finite Z array.")

    valid = z_coords[np.isfinite(z_coords)]
    if valid.size == 0:
        raise ValueError("Cannot compute elevation bounds on empty or all-non-finite Z array.")

    min_z = float(np.min(valid))
    max_z = float(np.max(valid))

    if strategy == "median":
        elevation = float(np.median(valid))
    elif strategy == "mean":
        elevation = float(np.mean(valid))
    elif strategy == "lowest":
        elevation = min_z
    else:
        elevation = float(np.median(valid))

    return elevation, min_z, max_z


def compute_roughness(z_coords: np.ndarray) -> float:
    """Compute terrain micro-roughness from localized Z variation.

    Metric:
        Sample standard deviation of height (sigma_z).
        For N <= 1, roughness is defined as 0.0.

    Rationale:
        At the micro-scale of foveated grid cells (5 cm to 50 cm), road surface
        roughness is directly quantified by elevation dispersion. The sample
        standard deviation provides a computationally efficient O(N) metric
        without requiring matrix inversion from plane fitting.

    Args:
        z_coords: 1D array of Z coordinates.

    Returns:
        Roughness value in meters (>= 0.0).
    """
    n = z_coords.size
    if n <= 1:
        return 0.0

    if n == 2:
        v0 = float(z_coords[0])
        v1 = float(z_coords[1])
        if math.isfinite(v0) and math.isfinite(v1):
            return abs(v0 - v1) * 0.7071067811865476  # 1 / sqrt(2)
        return 0.0

    valid = z_coords[np.isfinite(z_coords)]
    if valid.size <= 1:
        return 0.0
    return float(np.std(valid, ddof=1))


def aggregate_semantics(
    classes: np.ndarray,
    confidences: np.ndarray,
    num_classes: int = 8,
) -> Tuple[int, float, np.ndarray]:
    """Fuse semantic class predictions across points in a cell using weighted voting.

    Method:
        1. Accumulate score for class c: score(c) = sum(confidence_i for point_i where class == c).
        2. Dominant class = argmax_c score(c). If all scores zero, defaults to most frequent class.
        3. Aggregated confidence = mean confidence of points predicting the dominant class.
        4. Normalize class scores to obtain a valid probability distribution over all 8 classes.

    Args:
        classes: 1D integer array of class IDs (0..7).
        confidences: 1D float array of prediction confidences in [0.0, 1.0].
        num_classes: Number of project semantic taxonomy classes (default: 8).

    Returns:
        (dominant_class, aggregated_confidence, semantic_probabilities)
    """
    n = classes.size
    if n == 0:
        uniform_probs = np.full((num_classes,), 1.0 / num_classes, dtype=np.float32)
        return 7, 0.0, uniform_probs  # 7: OTHER_OBSTACLE

    if n == 1:
        c = int(classes[0])
        conf = float(confidences[0])
        if math.isnan(conf) or conf < 0.0:
            conf = 0.0
        elif conf > 1.0:
            conf = 1.0
        if not (0 <= c < num_classes):
            c = 7
        probs = np.zeros(num_classes, dtype=np.float32)
        probs[c] = 1.0
        return c, conf, probs

    # Fast direct accumulation for N >= 2 avoiding heavy np.nan_to_num wrapper
    class_scores = [0.0] * num_classes
    class_conf_sums = [0.0] * num_classes
    class_counts = [0] * num_classes
    total_score = 0.0

    for i in range(n):
        c = int(classes[i])
        conf = float(confidences[i])
        if math.isnan(conf) or conf < 0.0:
            conf = 0.0
        elif conf > 1.0:
            conf = 1.0

        if 0 <= c < num_classes:
            class_scores[c] += conf
            total_score += conf
            class_conf_sums[c] += conf
            class_counts[c] += 1

    if total_score > 0.0:
        inv_tot = 1.0 / total_score
        probs = np.array([s * inv_tot for s in class_scores], dtype=np.float32)
        # Find dominant class (first max index for deterministic tie breaking)
        dominant_class = int(np.argmax(class_scores))
        dom_count = class_counts[dominant_class]
        agg_conf = float(class_conf_sums[dominant_class] / dom_count) if dom_count > 0 else 0.0
    else:
        # Fallback to majority count if all confidences are zero
        dominant_class = int(np.argmax(class_counts)) if any(class_counts) else 7
        sum_c = sum(class_counts)
        if sum_c > 0:
            inv_c = 1.0 / sum_c
            probs = np.array([c * inv_c for c in class_counts], dtype=np.float32)
        else:
            probs = np.zeros(num_classes, dtype=np.float32)
        agg_conf = 0.0

    return dominant_class, agg_conf, probs


def compute_occupancy(
    point_count: int,
    ref_points: float = 3.0,
) -> float:
    """Compute normalized spatial occupancy probability from accumulated points.

    Interpretation:
        Occupancy probability P(occ) reflects the statistical certainty that a
        spatial volume is occupied by physical reflecting matter under the sensor beam.
        We use an exponential saturation model:
            P(occ) = 1.0 - exp(-N / N_ref)
        Where N is point count, and N_ref is reference points needed for ~63% occupancy.
        Result is strictly guaranteed to lie in [0.0, 1.0].

    Args:
        point_count: Total valid LiDAR points within the cell.
        ref_points: Saturation scaling parameter (default: 3.0).

    Returns:
        Occupancy probability in [0.0, 1.0].
    """
    if point_count <= 0:
        return 0.0
    occ = 1.0 - math.exp(-float(point_count) / float(ref_points))
    return float(min(1.0, max(0.0, occ)))


def aggregate_cell(
    resolution_level: str,
    cell_x: float,
    cell_y: float,
    points_z: np.ndarray,
    classes: np.ndarray,
    confidences: np.ndarray,
    timestamp: float,
    strategy: str = "median",
    ref_points: float = 3.0,
    observation_count: int = 1,
) -> Optional[GridCell]:
    """Aggregate all point observations within a single spatial cell into a GridCell.

    Args:
        resolution_level: Foveation ring label ('near', 'mid_near', 'mid', 'far').
        cell_x: Center X coordinate in map frame (meters).
        cell_y: Center Y coordinate in map frame (meters).
        points_z: 1D array of Z elevations.
        classes: 1D array of semantic classes.
        confidences: 1D array of confidence scores.
        timestamp: Timestamp of the observation frame.
        strategy: Elevation aggregation strategy ('median', 'mean', 'lowest').
        ref_points: Occupancy scaling parameter.
        observation_count: Number of temporal observations (default: 1).

    Returns:
        Fully populated GridCell, or None if points_z contains no valid points.
    """
    n = points_z.size
    if n == 0:
        return None

    # Optimized single-point fast path (covers ~70% of LiDAR cells)
    if n == 1:
        z0 = float(points_z[0])
        if not math.isfinite(z0):
            return None
        c0 = int(classes[0])
        conf0 = float(confidences[0])
        if math.isnan(conf0) or conf0 < 0.0:
            conf0 = 0.0
        elif conf0 > 1.0:
            conf0 = 1.0
        if not (0 <= c0 < 8):
            c0 = 7
        probs = np.zeros(8, dtype=np.float32)
        probs[c0] = 1.0
        occ = 1.0 - math.exp(-1.0 / ref_points)
        return GridCell(
            resolution_level=resolution_level,
            cell_x=float(cell_x),
            cell_y=float(cell_y),
            elevation=z0,
            min_z=z0,
            max_z=z0,
            semantic_class=c0,
            confidence=conf0,
            occupancy=float(min(1.0, max(0.0, occ))),
            point_count=1,
            roughness=0.0,
            timestamp=float(timestamp),
            velocity=None,
            observation_count=observation_count,
            uncertainty=0.0,
            semantic_probabilities=probs,
        )

    # General path: check validity
    valid_mask = np.isfinite(points_z)
    if not np.any(valid_mask):
        return None

    if np.all(valid_mask):
        z_valid = points_z
        c_valid = classes
        conf_valid = confidences
    else:
        z_valid = points_z[valid_mask]
        c_valid = classes[valid_mask]
        conf_valid = confidences[valid_mask]

    point_count = int(z_valid.size)
    if point_count == 0:
        return None

    # Re-check single valid point after filtering
    if point_count == 1:
        z0 = float(z_valid[0])
        c0 = int(c_valid[0])
        conf0 = float(conf_valid[0])
        if math.isnan(conf0) or conf0 < 0.0:
            conf0 = 0.0
        elif conf0 > 1.0:
            conf0 = 1.0
        if not (0 <= c0 < 8):
            c0 = 7
        probs = np.zeros(8, dtype=np.float32)
        probs[c0] = 1.0
        occ = 1.0 - math.exp(-1.0 / ref_points)
        return GridCell(
            resolution_level=resolution_level,
            cell_x=float(cell_x),
            cell_y=float(cell_y),
            elevation=z0,
            min_z=z0,
            max_z=z0,
            semantic_class=c0,
            confidence=conf0,
            occupancy=float(min(1.0, max(0.0, occ))),
            point_count=1,
            roughness=0.0,
            timestamp=float(timestamp),
            velocity=None,
            observation_count=observation_count,
            uncertainty=0.0,
            semantic_probabilities=probs,
        )

    elevation, min_z, max_z = compute_elevation_bounds(z_valid, strategy=strategy)
    roughness = compute_roughness(z_valid)
    dominant_class, agg_conf, probs = aggregate_semantics(c_valid, conf_valid)
    occupancy = compute_occupancy(point_count, ref_points=ref_points)

    # Uncertainty from semantic entropy
    ent = 0.0
    for p in probs:
        if p > 1e-7:
            ent -= float(p) * math.log(float(p))
    uncertainty = float(min(1.0, max(0.0, ent / _LOG_NUM_CLASSES)))

    return GridCell(
        resolution_level=resolution_level,
        cell_x=float(cell_x),
        cell_y=float(cell_y),
        elevation=elevation,
        min_z=min_z,
        max_z=max_z,
        semantic_class=dominant_class,
        confidence=agg_conf,
        occupancy=occupancy,
        point_count=point_count,
        roughness=roughness,
        timestamp=float(timestamp),
        velocity=None,
        observation_count=observation_count,
        uncertainty=uncertainty,
        semantic_probabilities=probs,
    )
