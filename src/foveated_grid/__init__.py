"""Foveated Variable-Resolution Grid & Spatial Structures Module."""

from src.foveated_grid.foveated_indexer import (
    CellKey,
    FoveatedGridIndexer as LegacyFoveatedGridIndexer,
    FoveationLevelConfig,
    cell_to_world,
    load_foveation_config,
    resolution_for_distance,
    world_to_cell,
)
from src.foveated_grid.sparse_grid import (
    BatchInsertResult,
    SparseCell,
    SparseFoveatedGrid,
    ingest_point_cloud,
)
from src.foveated_grid.grid_indexer import (
    DEFAULT_RINGS,
    FoveatedGridIndexer,
    FoveationRing,
)

__all__ = [
    "CellKey",
    "FoveationLevelConfig",
    "LegacyFoveatedGridIndexer",
    "SparseCell",
    "SparseFoveatedGrid",
    "BatchInsertResult",
    "ingest_point_cloud",
    "load_foveation_config",
    "resolution_for_distance",
    "world_to_cell",
    "cell_to_world",
    "DEFAULT_RINGS",
    "FoveatedGridIndexer",
    "FoveationRing",
]
