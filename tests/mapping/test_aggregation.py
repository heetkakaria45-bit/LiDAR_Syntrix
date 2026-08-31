"""Unit tests for Phase 1: Core Cell Aggregation.

Covers:
- Elevation estimation (median, mean, min_z, max_z, outlier robustness)
- Roughness formulation (sigma_z, edge cases)
- Semantic fusion (confidence-weighted voting, dominant class, tie-breaking)
- Occupancy probability estimation (bounded [0, 1])
- GridCell generation and contract compliance
- Edge cases: empty, NaN/Inf, single-point, conf=0, conf=1
"""

import numpy as np
import pytest

from src.contracts import GridCell
from src.mapping.aggregation import (
    aggregate_cell,
    aggregate_semantics,
    compute_elevation_bounds,
    compute_occupancy,
    compute_roughness,
)


class TestElevationAggregation:
    def test_elevation_median_and_bounds_simple(self) -> None:
        z = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        elev, min_z, max_z = compute_elevation_bounds(z, strategy="median")
        assert elev == pytest.approx(3.0)
        assert min_z == pytest.approx(1.0)
        assert max_z == pytest.approx(5.0)

    def test_elevation_outlier_robustness(self) -> None:
        # Ground plane at ~0.0m with an extreme high outlier at +100.0m
        z = np.array([0.01, -0.02, 0.00, 0.02, -0.01, 100.0], dtype=np.float32)
        elev_med, min_z, max_z = compute_elevation_bounds(z, strategy="median")
        elev_mean, _, _ = compute_elevation_bounds(z, strategy="mean")

        # Median remains close to ground ~0.0, while mean is dragged to ~16.6m
        assert abs(elev_med) < 0.05
        assert elev_mean > 10.0
        assert min_z == pytest.approx(-0.02)
        assert max_z == pytest.approx(100.0)

    def test_elevation_strategies(self) -> None:
        z = np.array([1.0, 2.0, 6.0], dtype=np.float32)
        assert compute_elevation_bounds(z, "median")[0] == pytest.approx(2.0)
        assert compute_elevation_bounds(z, "mean")[0] == pytest.approx(3.0)
        assert compute_elevation_bounds(z, "lowest")[0] == pytest.approx(1.0)

    def test_elevation_single_point(self) -> None:
        z = np.array([4.2], dtype=np.float32)
        elev, min_z, max_z = compute_elevation_bounds(z)
        assert elev == pytest.approx(4.2)
        assert min_z == pytest.approx(4.2)
        assert max_z == pytest.approx(4.2)

    def test_elevation_nan_inf_handling(self) -> None:
        z = np.array([np.nan, 2.5, np.inf, -np.inf, 3.5], dtype=np.float32)
        elev, min_z, max_z = compute_elevation_bounds(z)
        assert elev == pytest.approx(3.0)
        assert min_z == pytest.approx(2.5)
        assert max_z == pytest.approx(3.5)

    def test_elevation_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty or all-non-finite"):
            compute_elevation_bounds(np.array([], dtype=np.float32))

        with pytest.raises(ValueError, match="empty or all-non-finite"):
            compute_elevation_bounds(np.array([np.nan, np.inf], dtype=np.float32))


class TestRoughnessMetric:
    def test_roughness_flat_ground(self) -> None:
        z = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        assert compute_roughness(z) == pytest.approx(0.0)

    def test_roughness_single_point_or_empty(self) -> None:
        assert compute_roughness(np.array([1.0], dtype=np.float32)) == pytest.approx(0.0)
        assert compute_roughness(np.array([], dtype=np.float32)) == pytest.approx(0.0)
        assert compute_roughness(np.array([np.nan, 2.0], dtype=np.float32)) == pytest.approx(0.0)

    def test_roughness_sample_std(self) -> None:
        # Standard deviation of [1, 3] with ddof=1 is sqrt(2) ~ 1.4142
        z = np.array([1.0, 3.0], dtype=np.float32)
        assert compute_roughness(z) == pytest.approx(np.sqrt(2.0))


class TestSemanticAggregation:
    def test_semantic_weighted_majority(self) -> None:
        # 3 points voting for class 0 (DRIVABLE_GROUND) with low conf 0.4 -> total = 1.2
        # 1 point voting for class 2 (VEHICLE) with high conf 0.95 -> total = 0.95
        # Class 0 should win with dominant_class=0
        classes = np.array([0, 0, 0, 2], dtype=np.int32)
        conf = np.array([0.4, 0.4, 0.4, 0.95], dtype=np.float32)

        dom_class, agg_conf, probs = aggregate_semantics(classes, conf)
        assert dom_class == 0
        assert agg_conf == pytest.approx(0.4)
        assert probs[0] > probs[2]
        assert np.sum(probs) == pytest.approx(1.0)

    def test_semantic_higher_confidence_wins(self) -> None:
        # 1 point class 0 conf 0.2 vs 1 point class 3 (PEDESTRIAN) conf 0.9
        classes = np.array([0, 3], dtype=np.int32)
        conf = np.array([0.2, 0.9], dtype=np.float32)

        dom_class, agg_conf, probs = aggregate_semantics(classes, conf)
        assert dom_class == 3
        assert agg_conf == pytest.approx(0.9)
        assert probs[3] > probs[0]

    def test_semantic_zero_confidence_fallback(self) -> None:
        # When all confidences are 0.0, fallback to majority count
        classes = np.array([1, 1, 6], dtype=np.int32)
        conf = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        dom_class, agg_conf, probs = aggregate_semantics(classes, conf)
        assert dom_class == 1
        assert agg_conf == pytest.approx(0.0)
        assert probs[1] == pytest.approx(2.0 / 3.0)

    def test_semantic_empty_input(self) -> None:
        dom_class, agg_conf, probs = aggregate_semantics(
            np.array([], dtype=np.int32), np.array([], dtype=np.float32)
        )
        assert dom_class == 7  # Default OTHER_OBSTACLE
        assert agg_conf == pytest.approx(0.0)
        assert probs.shape == (8,)


class TestOccupancyEstimation:
    def test_occupancy_bounds(self) -> None:
        assert compute_occupancy(0) == pytest.approx(0.0)
        assert compute_occupancy(1) > 0.0
        assert compute_occupancy(1) < compute_occupancy(5)
        assert compute_occupancy(100) <= 1.0

    def test_occupancy_saturation(self) -> None:
        # For ref_points=3.0, N=3 -> 1 - exp(-1) ~ 0.6321
        occ = compute_occupancy(3, ref_points=3.0)
        assert occ == pytest.approx(1.0 - np.exp(-1.0), rel=1e-3)


class TestAggregateCell:
    def test_full_cell_aggregation(self) -> None:
        z = np.array([0.10, 0.12, 0.11, 0.15], dtype=np.float32)
        classes = np.array([0, 0, 0, 0], dtype=np.int32)
        conf = np.array([0.9, 0.95, 0.85, 0.9], dtype=np.float32)

        cell = aggregate_cell(
            resolution_level="near",
            cell_x=1.25,
            cell_y=-0.75,
            points_z=z,
            classes=classes,
            confidences=conf,
            timestamp=123.456,
        )

        assert isinstance(cell, GridCell)
        assert cell.resolution_level == "near"
        assert cell.cell_x == pytest.approx(1.25)
        assert cell.cell_y == pytest.approx(-0.75)
        assert cell.min_z == pytest.approx(0.10)
        assert cell.max_z == pytest.approx(0.15)
        assert cell.semantic_class == 0
        assert cell.point_count == 4
        assert cell.occupancy > 0.7
        assert cell.timestamp == pytest.approx(123.456)
        assert cell.roughness > 0.0
        assert cell.semantic_probabilities is not None

    def test_aggregate_cell_empty_or_all_nan(self) -> None:
        z = np.array([np.nan, np.nan], dtype=np.float32)
        classes = np.array([0, 0], dtype=np.int32)
        conf = np.array([0.5, 0.5], dtype=np.float32)

        cell = aggregate_cell(
            resolution_level="near",
            cell_x=0.0,
            cell_y=0.0,
            points_z=z,
            classes=classes,
            confidences=conf,
            timestamp=100.0,
        )
        assert cell is None
