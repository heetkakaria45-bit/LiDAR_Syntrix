"""Visualization & Interactive Dashboard Module.

Module Owner: Atharva (src/visualization/)
Responsibilities:
    - 2.5D elevation and traversability map rendering
    - Multi-resolution foveated grid visualization
    - Semantic point cloud and 8-class color mapping
    - Interactive 3D / top-down autonomous control center
    - Real-time web visualization server and REST API
    - Terminal telemetry dashboard
"""

from src.visualization.dashboard import print_terminal_dashboard
from src.visualization.server import run_server

__all__ = [
    "print_terminal_dashboard",
    "run_server",
]
