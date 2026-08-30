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

from typing import Dict, List, Optional, Tuple
import numpy as np

from src.contracts import GridCell


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
        2. Dominant class = argmax_c score(c). If all scores are zero, defaults to the most frequent class.
        3. Aggregated confidence = mean confidence of points predicting the dominant class.
        4. Normalize class scores to obtain a valid probability distribution over all 8 classes.

    Args:
        classes: 1D integer array of class IDs (0..7).
        confidences: 1D float array of prediction confidences in [0.0, 1.0].
        num_classes: Number of project semantic taxonomy classes (default: 8).

    Returns:
        (dominant_class, aggregated_confidence, semantic_probabilities)
    """
    if classes.size == 0:
        uniform_probs = np.full((num_classes,), 1.0 / num_classes, dtype=np.float32)
        return 7, 0.0, uniform_probs  # 7: OTHER_OBSTACLE

    # Ensure finite confidences clipped to [0.0, 1.0]
    safe_conf = np.nan_to_num(confidences, nan=0.0, posinf=1.0, neginf=0.0)
    safe_conf = np.clip(safe_conf, 0.0, 1.0)

    class_scores = np.zeros(num_classes, dtype=np.float64)
    for c, conf in zip(classes, safe_conf):
        if 0 <= c < num_classes:
            class_scores[c] += float(conf)

    total_score = float(np.sum(class_scores))
    if total_score > 0.0:
        probs = (class_scores / total_score).astype(np.float32)
        dominant_class = int(np.argmax(class_scores))
    else:
        # Fallback to majority count if all confidences are zero
        counts = np.bincount(classes[classes < num_classes], minlength=num_classes)
        dominant_class = int(np.argmax(counts))
        probs = np.zeros(num_classes, dtype=np.float32)
        if np.sum(counts) > 0:
            probs = (counts / np.sum(counts)).astype(np.float32)

    # Aggregated confidence: average confidence of points voting for dominant_class
    dom_mask = classes == dominant_class
    if np.any(dom_mask):
        agg_conf = float(np.mean(safe_conf[dom_mask]))
    else:
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
        For N=1: ~0.28, N=3: ~0.63, N=5: ~0.81, N>=10: ~0.97.
        Result is strictly guaranteed to lie in [0.0, 1.0].

    Args:
        point_count: Total valid LiDAR points within the cell.
        ref_points: Saturation scaling parameter (default: 3.0).

    Returns:
        Occupancy probability in [0.0, 1.0].
    """
    if point_count <= 0:
        return 0.0
    occ = 1.0 - np.exp(-float(point_count) / float(ref_points))
    return float(np.clip(occ, 0.0, 1.0))


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
    valid_mask = np.isfinite(points_z)
    if not np.any(valid_mask):
        return None

    z_valid = points_z[valid_mask]
    c_valid = classes[valid_mask]
    conf_valid = confidences[valid_mask]
    point_count = int(z_valid.size)

    elevation, min_z, max_z = compute_elevation_bounds(z_valid, strategy=strategy)
    roughness = compute_roughness(z_valid)
    dominant_class, agg_conf, probs = aggregate_semantics(c_valid, conf_valid)
    occupancy = compute_occupancy(point_count, ref_points=ref_points)

    # Uncertainty can be derived from semantic entropy or elevation dispersion
    # Normalized semantic entropy: H / log(8)
    epsilon = 1e-7
    entropy = -np.sum(probs * np.log(probs + epsilon)) / np.log(8.0)
    uncertainty = float(np.clip(entropy, 0.0, 1.0))

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
