"""Foveated Grid Indexer & Core Spatial Coordinate Mapping.

Module Owner: Manashri
Responsibilities:
    - Distance-based foveation ring resolution lookup
    - Deterministic world-to-cell coordinate mapping
    - Cell-to-world center coordinate reconstruction
    - Half-open ring boundary enforcement [r_k, r_{k+1})
    - Configuration ingestion without hardcoded spatial constants
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

import numpy as np
import yaml


class CellKey(NamedTuple):
    """Canonical, hashable cell identifier representing a discrete spatial grid cell.

    Attributes:
        level: Foveation ring level ID (e.g. 0, 1, 2, 3).
        i: Discrete X column index (forward axis).
        j: Discrete Y row index (left axis).
    """

    level: int
    i: int
    j: int

    def to_packed_uint64(self) -> int:
        """Pack (level, i, j) into a unique 64-bit unsigned integer key."""
        return ((self.level & 0xFFFF) << 48) | ((self.i & 0xFFFFFF) << 24) | (self.j & 0xFFFFFF)

    @classmethod
    def from_packed_uint64(cls, packed: int) -> CellKey:
        """Unpack 64-bit integer into canonical CellKey(level, i, j)."""
        level = (packed >> 48) & 0xFFFF
        i = (packed >> 24) & 0xFFFFFF
        j = packed & 0xFFFFFF
        return cls(level=level, i=i, j=j)


@dataclass(frozen=True)
class FoveationLevelConfig:
    """Configuration for a single concentric foveation distance ring."""

    level_id: int
    name: str
    min_range: float  # Inclusive lower radial boundary (meters)
    max_range: float  # Exclusive upper radial boundary (meters)
    resolution: float  # Cell grid width / height delta (meters)
    semantic_priority: float = 1.0
    description: str = ""

    @property
    def x_min(self) -> float:
        """Minimum physical X bounding coordinate for this ring (meters)."""
        return -self.max_range

    @property
    def y_min(self) -> float:
        """Minimum physical Y bounding coordinate for this ring (meters)."""
        return -self.max_range

    @property
    def grid_size_x(self) -> int:
        """Number of discrete cells along X axis spanning full bounding square."""
        return int(math.ceil((2.0 * self.max_range) / self.resolution))

    @property
    def grid_size_y(self) -> int:
        """Number of discrete cells along Y axis spanning full bounding square."""
        return int(math.ceil((2.0 * self.max_range) / self.resolution))


def load_foveation_config(
    config_source: Optional[Union[Dict[str, Any], Path, str]] = None,
) -> Tuple[List[FoveationLevelConfig], float]:
    """Load foveation level definitions and global maximum sensing radius.

    Args:
        config_source: Config dict, YAML file Path, string path, or None (loads default).

    Returns:
        Tuple of (sorted list of FoveationLevelConfig, max_radius float).
    """
    if config_source is None:
        # Default config path relative to repo root
        default_path = (
            Path(__file__).resolve().parent.parent.parent / "configs" / "default_config.yaml"
        )
        if not default_path.is_file():
            raise FileNotFoundError(f"Default configuration file not found at {default_path}")
        with open(default_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    elif isinstance(config_source, (str, Path)):
        cfg_path = Path(config_source)
        if not cfg_path.is_file():
            raise FileNotFoundError(f"Configuration file not found at {cfg_path}")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    elif isinstance(config_source, dict):
        cfg = config_source
    else:
        raise TypeError(f"Unsupported config source type: {type(config_source).__name__}")

    foveation_dict = cfg.get("foveation_levels", {})
    if not foveation_dict:
        raise ValueError("Configuration missing 'foveation_levels' definition")

    map_cfg = cfg.get("map", {})
    max_radius = float(map_cfg.get("max_radius", 100.0))

    levels: List[FoveationLevelConfig] = []
    for key, lvl_data in foveation_dict.items():
        lvl = FoveationLevelConfig(
            level_id=int(lvl_data.get("level_id", 0)),
            name=str(lvl_data.get("name", key)),
            min_range=float(lvl_data["min_range"]),
            max_range=float(lvl_data["max_range"]),
            resolution=float(lvl_data["resolution"]),
            semantic_priority=float(lvl_data.get("semantic_priority", 1.0)),
            description=str(lvl_data.get("description", "")),
        )
        levels.append(lvl)

    # Sort strictly by min_range / level_id
    levels.sort(key=lambda lvl: (lvl.min_range, lvl.level_id))

    # Validate monotonicity
    for idx in range(len(levels) - 1):
        if levels[idx].max_range != levels[idx + 1].min_range:
            raise ValueError(
                f"Foveation level boundary gap/overlap between level {levels[idx].name} "
                f"(max={levels[idx].max_range}) and {levels[idx + 1].name} "
                f"(min={levels[idx + 1].min_range})"
            )
        if levels[idx].resolution >= levels[idx + 1].resolution:
            raise ValueError(
                f"Foveation resolution must coarsen outward: level {levels[idx].name} "
                f"({levels[idx].resolution}m) vs {levels[idx + 1].name} "
                f"({levels[idx + 1].resolution}m)"
            )

    return levels, max_radius


class FoveatedGridIndexer:
    """Hierarchical Variable-Resolution Spatial Indexer.

    Provides deterministic, constant-time mappings between continuous Cartesian
    world coordinates (X=forward, Y=left, Z=up) and multi-resolution discrete
    cell identifiers (level, i, j).
    """

    def __init__(
        self,
        config: Optional[Union[Dict[str, Any], Path, str]] = None,
        levels: Optional[List[FoveationLevelConfig]] = None,
        max_radius: Optional[float] = None,
    ) -> None:
        """Initialize the foveated grid indexer from configuration or explicit level configs.

        Args:
            config: Optional config dict or path to YAML config file.
            levels: Optional list of FoveationLevelConfig (overrides config if provided).
            max_radius: Optional maximum sensing radius in meters.
        """
        if levels is not None:
            self._levels = sorted(levels, key=lambda lvl: (lvl.min_range, lvl.level_id))
            self._max_radius = (
                float(max_radius)
                if max_radius is not None
                else (self._levels[-1].max_range if self._levels else 100.0)
            )
        else:
            loaded_levels, loaded_max_radius = load_foveation_config(config)
            self._levels = loaded_levels
            self._max_radius = float(max_radius) if max_radius is not None else loaded_max_radius

        self._level_by_id: Dict[int, FoveationLevelConfig] = {
            lvl.level_id: lvl for lvl in self._levels
        }

    @property
    def levels(self) -> List[FoveationLevelConfig]:
        """List of active foveation level configurations ordered near-to-far."""
        return list(self._levels)

    @property
    def max_radius(self) -> float:
        """Maximum outer mapping radius in meters."""
        return self._max_radius

    def get_level(self, level_id: int) -> FoveationLevelConfig:
        """Retrieve level configuration by integer level ID."""
        if level_id not in self._level_by_id:
            raise KeyError(f"Unknown foveation level ID: {level_id}")
        return self._level_by_id[level_id]

    def get_level_for_distance(self, distance: float) -> Optional[FoveationLevelConfig]:
        """Determine the foveation level for a given 2D radial distance.

        Adheres strictly to the half-open radial interval convention [r_k, r_{k+1}).

        Args:
            distance: Horizontal radial distance r = sqrt(x^2 + y^2) in meters.

        Returns:
            Matching FoveationLevelConfig, or None if distance is negative or out of bounds.
        """
        if distance < 0.0 or distance >= self._max_radius:
            return None

        for lvl in self._levels:
            if lvl.min_range <= distance < lvl.max_range:
                return lvl

        return None

    def resolution_for_distance(self, distance: float) -> Optional[float]:
        """Look up the spatial grid resolution (delta in meters) for a given distance.

        Uses the half-open radial interval convention [r_k, r_{k+1}).

        Args:
            distance: Horizontal radial distance r = sqrt(x^2 + y^2) in meters.

        Returns:
            Cell resolution in meters (e.g. 0.05, 0.10, 0.25, 0.50),
            or None if distance is out of range [0.0, max_radius).
        """
        lvl = self.get_level_for_distance(distance)
        return lvl.resolution if lvl is not None else None

    def world_to_cell(self, x: float, y: float) -> Optional[CellKey]:
        """Map continuous 2D world coordinates to a canonical discrete CellKey.

        Conventions:
            - Radial distance: r = sqrt(x^2 + y^2)
            - Ring assignment: [r_k, r_{k+1})
            - Cell indexing formula:
                i = floor((x - x_min) / delta)
                j = floor((y - y_min) / delta)
              where x_min = -max_range and y_min = -max_range for the matching level.

        Args:
            x: Forward Cartesian coordinate in meters (vehicle heading).
            y: Left Cartesian coordinate in meters (lateral axis).

        Returns:
            CellKey(level, i, j) if (x, y) is within [0, max_radius), else None.
        """
        r = math.hypot(x, y)
        lvl = self.get_level_for_distance(r)
        if lvl is None:
            return None

        delta = lvl.resolution
        x_min = lvl.x_min
        y_min = lvl.y_min

        # Deterministic floor quantization handling positive and negative coords.
        # round(..., 9) guards against IEEE-754 float precision errors (e.g. 10.1 / 0.05 = 201.99999999999997)
        i = int(math.floor(round((x - x_min) / delta, 9)))
        j = int(math.floor(round((y - y_min) / delta, 9)))

        return CellKey(level=lvl.level_id, i=i, j=j)

    def cell_to_world(self, cell: Union[CellKey, Tuple[int, int, int]]) -> Tuple[float, float]:
        """Reconstruct the physical continuous 2D cell center coordinates from a CellKey.

        Center coordinate formula:
            x_center = x_min + (i + 0.5) * delta
            y_center = y_min + (j + 0.5) * delta
        where x_min = -max_range and y_min = -max_range for the cell's foveation level.

        Args:
            cell: CellKey instance or (level, i, j) tuple.

        Returns:
            Tuple of (x_center, y_center) in meters in the map/vehicle frame.

        Raises:
            KeyError: If cell's level ID is not configured.
        """
        level_id, i, j = cell[0], cell[1], cell[2]
        lvl = self.get_level(level_id)

        delta = lvl.resolution
        x_min = lvl.x_min
        y_min = lvl.y_min

        x_center = x_min + (i + 0.5) * delta
        y_center = y_min + (j + 0.5) * delta

        return (x_center, y_center)

    def world_to_cell_batch(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Vectorized conversion of continuous 2D/3D point array to discrete CellKey packed uint64.

        Adheres strictly to half-open radial intervals [r_k, r_{k+1}) and deterministic
        coordinate floor quantization.

        Args:
            points: np.ndarray of shape (N, 2) or (N, >=2) where column 0 is X and column 1 is Y.

        Returns:
            Tuple of (valid_mask (N,) bool, packed_keys (N,) np.uint64).
        """
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[1] < 2:
            raise ValueError(f"points array must have shape (N, >=2), got {pts.shape}")

        x = pts[:, 0]
        y = pts[:, 1]
        r = np.hypot(x, y)

        valid_mask = (r >= 0.0) & (r < self._max_radius)
        packed_keys = np.zeros(len(pts), dtype=np.uint64)

        for lvl in self._levels:
            lvl_mask = valid_mask & (r >= lvl.min_range) & (r < lvl.max_range)
            if not np.any(lvl_mask):
                continue

            x_l = x[lvl_mask]
            y_l = y[lvl_mask]
            delta = lvl.resolution
            x_min = lvl.x_min
            y_min = lvl.y_min

            # round(..., 9) guards against IEEE-754 float precision errors
            i_l = np.floor(np.round((x_l - x_min) / delta, 9)).astype(np.uint64)
            j_l = np.floor(np.round((y_l - y_min) / delta, 9)).astype(np.uint64)
            level_id = np.uint64(lvl.level_id)

            packed = ((level_id & 0xFFFF) << 48) | ((i_l & 0xFFFFFF) << 24) | (j_l & 0xFFFFFF)
            packed_keys[lvl_mask] = packed

        return valid_mask, packed_keys


# Standalone module-level helper functions for convenient functional usage
_GLOBAL_INDEXER: Optional[FoveatedGridIndexer] = None


def _get_global_indexer() -> FoveatedGridIndexer:
    """Lazily instantiate and cache default singleton indexer."""
    global _GLOBAL_INDEXER
    if _GLOBAL_INDEXER is None:
        _GLOBAL_INDEXER = FoveatedGridIndexer()
    return _GLOBAL_INDEXER


def resolution_for_distance(
    distance: float, indexer: Optional[FoveatedGridIndexer] = None
) -> Optional[float]:
    """Look up cell resolution for radial distance using default or provided indexer."""
    idx = indexer or _get_global_indexer()
    return idx.resolution_for_distance(distance)


def world_to_cell(
    x: float, y: float, indexer: Optional[FoveatedGridIndexer] = None
) -> Optional[CellKey]:
    """Map world coordinates (x, y) to CellKey using default or provided indexer."""
    idx = indexer or _get_global_indexer()
    return idx.world_to_cell(x, y)


def cell_to_world(
    cell: Union[CellKey, Tuple[int, int, int]],
    indexer: Optional[FoveatedGridIndexer] = None,
) -> Tuple[float, float]:
    """Reconstruct world cell center (x_center, y_center) using default or provided indexer."""
    idx = indexer or _get_global_indexer()
    return idx.cell_to_world(cell)
