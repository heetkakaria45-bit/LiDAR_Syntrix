"""Foveated Variable-Resolution Grid & Spatial Structures Module.

Module Owner: Manashri (src/foveated_grid/)
Responsibilities:
    - Multi-ring hierarchical data structure
    - Spatial indexing and deterministic coordinate conversion
    - High-speed point-to-cell assignment
    - Multi-resolution boundary collision handling
    - Cache-efficient memory layouts and spatial hashing
"""

from src.foveated_grid.grid_indexer import (
    DEFAULT_RINGS,
    FoveatedGridIndexer,
    FoveationRing,
)

__all__ = [
    "DEFAULT_RINGS",
    "FoveatedGridIndexer",
    "FoveationRing",
]
