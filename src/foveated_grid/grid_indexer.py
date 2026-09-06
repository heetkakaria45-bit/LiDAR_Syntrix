"""Backward Compatibility Grid Indexer Interface.

Module Owner: Manashri
Re-exports canonical symbols from src.foveated_grid.foveated_indexer to ensure
complete backward compatibility for all pipeline and test consumers.
"""

from __future__ import annotations

from src.foveated_grid.foveated_indexer import (
    CellKey,
    FoveatedGridIndexer,
    FoveationLevelConfig,
    assign_points,
    cell_to_world,
    get_level_for_distance,
    load_foveation_config,
    resolution_for_distance,
    world_to_cell,
)

__all__ = [
    "CellKey",
    "FoveationLevelConfig",
    "FoveatedGridIndexer",
    "load_foveation_config",
    "resolution_for_distance",
    "get_level_for_distance",
    "world_to_cell",
    "cell_to_world",
    "assign_points",
]
