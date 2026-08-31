"""Foveated Grid & Spatial Indexing Data Structure Module.

Module Owner: Manashri
Responsibilities:
    - Hierarchical variable-resolution multi-ring grid data structure
    - Spatial indexing (nested multi-resolution Cartesian rings with sparse hashing)
    - High-throughput scalar and vectorized batch point-to-cell mapping
    - Boundary alignment and resolution transition management
    - Memory-efficient sparse spatial representation
    - Downstream integration with 2.5D Semantic Mapping engine
"""

from src.foveated_grid.foveated_indexer import (
    CellKey,
    FoveatedGridIndexer,
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

__all__ = [
    "CellKey",
    "FoveationLevelConfig",
    "FoveatedGridIndexer",
    "SparseCell",
    "SparseFoveatedGrid",
    "BatchInsertResult",
    "ingest_point_cloud",
    "load_foveation_config",
    "resolution_for_distance",
    "world_to_cell",
    "cell_to_world",
]
