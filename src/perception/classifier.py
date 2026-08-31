"""
Calibrated Probabilistic Geometric & Statistical Point Cloud Classifier.
Module Owner: Vedant (src/perception/)

Computes normalized class probabilities across the 8-class frozen taxonomy:
    0: DRIVABLE_GROUND
    1: NON_DRIVABLE_TERRAIN
    2: VEHICLE
    3: PEDESTRIAN
    4: CYCLIST
    5: POLE
    6: WALL_BUILDING
    7: OTHER_OBSTACLE
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np

from src.common.types import SemanticClass


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Computes numerically stable softmax along the last dimension."""
    if logits.size == 0:
        return np.zeros((0, 8), dtype=np.float32)
    scaled = logits / max(temperature, 1e-4)
    max_l = np.max(scaled, axis=1, keepdims=True)
    exp_l = np.exp(scaled - max_l)
    return exp_l / np.sum(exp_l, axis=1, keepdims=True)


class CalibratedGeometricClassifier:
    """
    High-speed, vectorized probabilistic semantic classifier.
    Computes class logits based on geometric signatures, elevation gradients,
    height above estimated ground, and spatial aspect ratios.
    """

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = temperature
        self.num_classes = 8

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """
        Computes (N, 8) normalized probability matrix from (N, 10) feature array.

        Features:
            0: x, 1: y, 2: z, 3: r_xy, 4: elev_angle, 5: azim_angle,
            6: dz (height above ground), 7: column_span, 8: column_density, 9: intensity
        """
        N = features.shape[0]
        if N == 0:
            return np.zeros((0, self.num_classes), dtype=np.float32)

        x = features[:, 0]
        y = features[:, 1]
        z = features[:, 2]
        r_xy = features[:, 3]
        dz = features[:, 6]
        span = features[:, 7]
        density = features[:, 8]
        intensity = features[:, 9]

        # Allocate logits for 8 classes
        logits = np.zeros((N, self.num_classes), dtype=np.float32)

        # ----------------------------------------------------------------------
        # 1. DRIVABLE_GROUND (Class 0)
        # Conditions: Very low dz (< 0.15m), low column span (< 0.3m), lateral proximity to road center
        # ----------------------------------------------------------------------
        ground_score = np.exp(- (dz / 0.12) ** 2) * np.exp(- (span / 0.35) ** 2)
        road_centering = np.exp(- (np.abs(y) / 6.0) ** 2) # Higher probability near center trajectory
        logits[:, 0] = 4.0 * ground_score + 1.5 * road_centering

        # ----------------------------------------------------------------------
        # 2. NON_DRIVABLE_TERRAIN (Class 1)
        # Conditions: Low-to-moderate dz (< 0.4m), rougher terrain, lateral margins
        # ----------------------------------------------------------------------
        offroad_lateral = 1.0 - np.exp(- (np.abs(y) / 5.0) ** 2)
        terrain_score = np.exp(- ((dz - 0.15) / 0.25) ** 2) * np.exp(- (span / 0.6) ** 2)
        logits[:, 1] = 2.5 * terrain_score + 2.0 * offroad_lateral * np.exp(- (dz / 0.3) ** 2)

        # ----------------------------------------------------------------------
        # 3. VEHICLE (Class 2)
        # Conditions: dz in [0.3m, 2.5m], column span in [0.8m, 3.0m], bounded spatial volume
        # ----------------------------------------------------------------------
        vehicle_dz_mask = (dz >= 0.25) & (dz <= 2.8)
        vehicle_span_mask = (span >= 0.8) & (span <= 3.5)
        vehicle_height_score = np.exp(- ((dz - 1.2) / 0.8) ** 2)
        vehicle_span_score = np.exp(- ((span - 1.8) / 1.0) ** 2)
        logits[:, 2] = np.where(
            vehicle_dz_mask & vehicle_span_mask,
            3.5 * vehicle_height_score + 2.0 * vehicle_span_score + 0.5 * density,
            -2.0
        )

        # ----------------------------------------------------------------------
        # 4. PEDESTRIAN (Class 3)
        # Conditions: dz in [0.2m, 2.1m], column span in [1.0m, 2.1m], lower density / narrow profile
        # ----------------------------------------------------------------------
        ped_dz_mask = (dz >= 0.15) & (dz <= 2.1)
        ped_span_mask = (span >= 0.8) & (span <= 2.2)
        ped_score = np.exp(- ((dz - 1.0) / 0.6) ** 2) * np.exp(- ((span - 1.6) / 0.5) ** 2)
        # Pedestrians typically have narrower cluster footprints than vehicles
        logits[:, 3] = np.where(
            ped_dz_mask & ped_span_mask,
            2.8 * ped_score + 1.0 * (1.0 - density),
            -3.0
        )

        # ----------------------------------------------------------------------
        # 5. CYCLIST (Class 4)
        # Conditions: dz in [0.2m, 2.0m], span in [0.8m, 2.0m], moderate speed/profile
        # ----------------------------------------------------------------------
        cyclist_dz_mask = (dz >= 0.2) & (dz <= 2.0)
        cyclist_score = np.exp(- ((dz - 0.9) / 0.6) ** 2) * np.exp(- ((span - 1.4) / 0.6) ** 2)
        logits[:, 4] = np.where(
            cyclist_dz_mask,
            1.8 * cyclist_score,
            -3.5
        )

        # ----------------------------------------------------------------------
        # 6. POLE (Class 5)
        # Conditions: Tall column span (> 2.2m), narrow horizontal profile, dz from base to top
        # ----------------------------------------------------------------------
        pole_span_mask = span >= 2.2
        pole_score = np.exp(- ((span - 4.5) / 2.0) ** 2) + np.clip((span - 2.0) / 3.0, 0.0, 2.0)
        logits[:, 5] = np.where(
            pole_span_mask & (dz >= 0.2),
            2.5 * pole_score + 1.0 * (1.0 - density),
            -2.5
        )

        # ----------------------------------------------------------------------
        # 7. WALL_BUILDING (Class 6)
        # Conditions: Very tall column span (> 2.5m), high point density, lateral/far field
        # ----------------------------------------------------------------------
        wall_span_mask = span >= 2.5
        wall_score = np.clip(span / 4.0, 0.0, 3.0) + 1.5 * density
        logits[:, 6] = np.where(
            wall_span_mask & (dz >= 0.5),
            2.8 * wall_score + 1.0 * (np.abs(y) / 10.0),
            -2.0
        )

        # ----------------------------------------------------------------------
        # 8. OTHER_OBSTACLE (Class 7)
        # Conditions: Low obstacles, curbs, debris, or ambiguous elevated returns
        # ----------------------------------------------------------------------
        other_dz_mask = (dz >= 0.15) & (dz <= 0.8)
        logits[:, 7] = np.where(
            other_dz_mask & (span <= 0.9),
            2.0 * np.exp(- ((dz - 0.3) / 0.3) ** 2),
            0.1
        )

        # Compute normalized probabilities using softmax
        probs = softmax(logits, temperature=self.temperature)
        return probs

    def predict(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Infers dominant semantic class ID, confidence, and full class probabilities.

        Returns:
            labels: (N,) uint8 semantic class IDs in [0..7]
            confidence: (N,) float32 max class probability in [0.0, 1.0]
            probs: (N, 8) float32 probability distribution
        """
        N = features.shape[0]
        if N == 0:
            return (
                np.zeros(0, dtype=np.uint8),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, self.num_classes), dtype=np.float32),
            )

        probs = self.predict_proba(features)
        labels = np.argmax(probs, axis=1).astype(np.uint8)
        confidence = np.max(probs, axis=1).astype(np.float32)

        return labels, confidence, probs
