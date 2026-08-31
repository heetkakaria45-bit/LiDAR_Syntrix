"""
Autonomous Perception Control Center UI Interface Scaffolding.
Module Owner: Atharva (src/visualization/)

Responsibility:
    - Render multi-layer live LiDAR & 2.5D Semantic Map views:
      1. Live LiDAR view
      2. Semantic view
      3. Elevation view
      4. Traversability view
      5. Foveation view
      6. Uniform vs foveated comparison
      7. Performance telemetry
      8. Cell/Fovea inspector
      9. Semantic confidence
      10. Resolution-decision explanation
      11. Object information
      12. Temporal playback if feasible
    - Consume real system outputs (both live streams and prerecorded datasets).
"""

from __future__ import annotations

from typing import Optional

from src.common.config import SystemConfig, load_config
from src.common.interfaces import IVisualizer
from src.common.types import SemanticMap, TelemetryMetrics


class PerceptionControlCenter(IVisualizer):
    """
    Perception Control Center UI scaffold.
    To be fully implemented by Atharva in Phase J.
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or load_config()
        self.current_view_mode = self.config.visualization.default_view_mode

    def render_frame(self, semantic_map: SemanticMap, telemetry: TelemetryMetrics) -> None:
        """Renders display frame. GUI rendering loop scheduled for Phase J."""
        pass

    def set_view_mode(self, mode_name: str) -> None:
        self.current_view_mode = mode_name
