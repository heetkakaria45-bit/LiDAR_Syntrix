"""Playback Controller for Temporal LiDAR Sequences and Demonstrations.

Module Owner: Atharva (src/integration/)
"""

import threading
import time
from typing import Callable, Optional
from src.integration.pipeline import PipelineOrchestrator


class SequencePlayer:
    """Controls playback of LiDAR perception sequences (Play, Pause, Step, Reset)."""

    def __init__(
        self,
        orchestrator: PipelineOrchestrator,
        target_fps: float = 10.0,
        on_frame_callback: Optional[Callable] = None,
    ):
        self.orchestrator = orchestrator
        self.target_fps = target_fps
        self.on_frame_callback = on_frame_callback
        self.is_playing = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def step(self) -> None:
        """Process one single frame forward."""
        frame, sem_cloud, sem_map, telemetry = self.orchestrator.process_frame()
        if self.on_frame_callback:
            self.on_frame_callback(frame, sem_cloud, sem_map, telemetry)

    def play(self) -> None:
        """Start continuous playback in background thread."""
        if self.is_playing:
            return
        self.is_playing = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Pause continuous playback."""
        self.is_playing = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def reset(self) -> None:
        """Reset sequence and frame counter."""
        self.pause()
        self.orchestrator.frame_count = 0

    def _run_loop(self) -> None:
        while self.is_playing and not self._stop_event.is_set():
            start_t = time.perf_counter()
            self.step()
            dt = time.perf_counter() - start_t
            desired_interval = 1.0 / max(self.target_fps, 1.0)
            sleep_t = max(0.0, desired_interval - dt)
            time.sleep(sleep_t)
