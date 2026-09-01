"""Autonomous Perception Control Center Web & REST API Server.

Module Owner: Atharva (src/visualization/)
Features:
    - Zero-dependency built-in HTTP server
    - Serves modern autonomous control center web UI
    - Streams live perception frames, multi-resolution cells & hazards
    - Live telemetry HUD (FPS, memory RSS, per-stage latency)
    - Interactive playback and scene selection API
"""

import json
import mimetypes
import os
from pathlib import Path
import dataclasses
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import mimetypes
import os
from pathlib import Path
import socketserver
import sys
import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse
import numpy as np

from src.contracts import GridCell
from src.evaluation.benchmark import BenchmarkRunner
from src.integration.pipeline import PipelineMode, PipelineOrchestrator
from src.integration.playback import SequencePlayer


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DIR = Path(__file__).parent / "web"


def _find_video_asset() -> Optional[Path]:
    """Find any mp4 or webm video asset in project root."""
    for ext in ("*.mp4", "*.webm"):
        matches = list(PROJECT_ROOT.glob(ext))
        if matches:
            return matches[0]
    return None


from enum import Enum


def _json_sanitize(obj: Any) -> Any:
    """Recursively convert tuples, dataclasses, enums, numpy types, sets and non-string keys to JSON-serializable primitives."""
    if isinstance(obj, Enum):
        return obj.value
    elif dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _json_sanitize(dataclasses.asdict(obj))
    elif isinstance(obj, dict) or hasattr(obj, "items"):
        new_dict = {}
        for k, v in dict(obj).items():
            if isinstance(k, tuple):
                str_k = f"{k[0]}_{k[1]}" if len(k) == 2 else "_".join(str(x) for x in k)
            else:
                str_k = str(k)
            new_dict[str_k] = _json_sanitize(v)
        return new_dict
    elif isinstance(obj, (list, tuple, set)):
        return [_json_sanitize(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif hasattr(obj, "__dict__") and not isinstance(obj, type):
        return _json_sanitize(obj.__dict__)
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


class ControlCenterHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving dashboard frontend and REST endpoints."""

    orchestrator: PipelineOrchestrator
    player: SequencePlayer

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP logs
        return

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/" or path == "/index.html":
            self._serve_file(WEB_DIR / "index.html", "text/html")
        elif path == "/style.css":
            self._serve_file(WEB_DIR / "style.css", "text/css")
        elif path == "/app.js":
            self._serve_file(WEB_DIR / "app.js", "application/javascript")
        elif path == "/video.mp4" or path == "/assets/video.mp4" or path == "/bg_video.mp4":
            self._serve_video_stream()
        elif path == "/car.mp4" or path == "/assets/car.mp4":
            car_path = PROJECT_ROOT / "car.mp4"
            if car_path.exists():
                self._serve_file(car_path, "video/mp4")
            else:
                self.send_error(404, "car.mp4 not found")
        elif path == "/api/status":
            self._send_json({
                "status": "online",
                "mode": self.orchestrator.active_source_mode.value,
                "frame_count": self.orchestrator.frame_count,
            })
        elif path == "/api/architecture":
            self._send_json(self._get_architecture_info())
        elif path == "/api/benchmark":
            stats = BenchmarkRunner.compare_uniform_vs_foveated()
            self._send_json(stats)
        elif path == "/api/frame":
            self._serve_latest_frame()
        elif path == "/api/cell_inspect":
            query_params = parse_qs(parsed_url.query)
            x = float(query_params.get("x", [0.0])[0])
            y = float(query_params.get("y", [0.0])[0])
            self._serve_cell_inspect(x, y)
        else:
            # Check if requesting a static file from WEB_DIR
            potential_file = WEB_DIR / path.lstrip("/")
            if potential_file.is_file() and potential_file.resolve().is_relative_to(WEB_DIR.resolve()):
                mime, _ = mimetypes.guess_type(str(potential_file))
                self._serve_file(potential_file, mime or "application/octet-stream")
            else:
                self.send_error(404, "File Not Found")

    def _serve_video_stream(self) -> None:
        """Stream video asset with HTTP 206 partial content support for smooth scrubbing."""
        video_path = _find_video_asset()
        if not video_path or not video_path.exists():
            self.send_error(404, "Video asset not found in project root")
            return

        file_size = video_path.stat().st_size
        range_header = self.headers.get("Range")

        if not range_header:
            # Serve complete video
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(video_path, "rb") as f:
                # Stream in chunks
                while chunk := f.read(65536):
                    self.wfile.write(chunk)
            return

        # Parse Range header: bytes=start-end
        try:
            bytes_range = range_header.strip().split("=")[1]
            start_str, end_str = bytes_range.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            if end >= file_size:
                end = file_size - 1
            length = end - start + 1

            self.send_response(206)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(video_path, "rb") as f:
                f.seek(start)
                bytes_to_send = length
                while bytes_to_send > 0:
                    read_size = min(65536, bytes_to_send)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    bytes_to_send -= len(chunk)
        except Exception:
            return

    def _get_architecture_info(self) -> Dict[str, Any]:
        """Provide detailed pipeline architecture specifications and live telemetry."""
        return {
            "project": "LiDAR_Syntrix",
            "tagline": "Foveated Semantic 2.5D LiDAR Mapping for Autonomous Navigation",
            "initiative": "Smart India Hackathon 2026 / DRDO Defence R&D",
            "pipeline_stages": [
                {
                    "stage_id": 1,
                    "name": "LiDAR Ingestion & Preprocessing",
                    "owner": "Amulya",
                    "module": "src/preprocessing/",
                    "input": "Raw Point Cloud (PCD / BIN / Sensor)",
                    "output": "PointCloudFrame",
                    "resolution": "Raw sensor points",
                    "status": "ONLINE",
                },
                {
                    "stage_id": 2,
                    "name": "Semantic Point Cloud Perception",
                    "owner": "Vedant",
                    "module": "src/perception/",
                    "input": "PointCloudFrame",
                    "output": "SemanticPointCloud",
                    "resolution": "8-Class Taxonomy Classification",
                    "status": "ONLINE",
                },
                {
                    "stage_id": 3,
                    "name": "Foveated Variable-Resolution Grid",
                    "owner": "Manashri",
                    "module": "src/foveated_grid/",
                    "input": "SemanticPointCloud",
                    "output": "Spatial Multi-Ring Assignments",
                    "resolution": "4 Rings: 5cm (0-10m), 10cm (10-25m), 25cm (25-50m), 50cm (50-100m)",
                    "status": "ONLINE",
                },
                {
                    "stage_id": 4,
                    "name": "2.5D Elevation & Traversability Mapping",
                    "owner": "Heet",
                    "module": "src/mapping/",
                    "input": "Spatial Multi-Ring Assignments",
                    "output": "SemanticMap (GridCell Multi-Resolution)",
                    "resolution": "2.5D Height Surfaces & Terrain Traversability",
                    "status": "ONLINE",
                },
                {
                    "stage_id": 5,
                    "name": "Real-Time Integration & Orchestration",
                    "owner": "Atharva",
                    "module": "src/integration/",
                    "input": "End-to-End Pipeline Wiring",
                    "output": "Live Telemetry Snapshot & Temporal Playback",
                    "resolution": "Real Timers & RSS Memory Profiling",
                    "status": "ONLINE",
                },
                {
                    "stage_id": 6,
                    "name": "Advanced 3D/2.5D Visualization & HUD",
                    "owner": "Atharva",
                    "module": "src/visualization/",
                    "input": "SemanticMap & Live Telemetry",
                    "output": "Interactive Three.js Spatial WebGL Console",
                    "resolution": "Physical 3D World vs 2.5D Computational Overlay",
                    "status": "ONLINE",
                },
                {
                    "stage_id": 7,
                    "name": "Evaluation & Benchmarking",
                    "owner": "Himisha",
                    "module": "src/evaluation/",
                    "input": "Uniform vs Foveated Comparative Runs",
                    "output": "mIoU, Elevation RMSE, Cell Count & Memory Savings",
                    "resolution": ">95% Memory Reduction Verified",
                    "status": "ONLINE",
                },
            ],
        }

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/api/control":
            content_len = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_len)
            try:
                payload = json.loads(post_data.decode("utf-8"))
            except Exception:
                payload = {}

            action = payload.get("action")
            if action == "play":
                self.player.play()
            elif action == "pause":
                self.player.pause()
            elif action == "step":
                self.player.step()
            elif action == "reset":
                self.player.reset()
            elif action == "set_scene":
                scene_type = payload.get("scene_type", "urban")
                self.orchestrator.synthetic_scene_type = scene_type
                self.orchestrator.frame_count = 0
                self.player.step()

            self._send_json({"status": "ok", "action": action})
        else:
            self.send_error(404, "Endpoint Not Found")

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.exists():
            self.send_error(404, "File not found")
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: Any) -> None:
        sanitized = _json_sanitize(data)
        body = json.dumps(sanitized).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_latest_frame(self) -> None:
        # If no frame processed yet, process one frame
        if self.orchestrator.last_frame is None:
            self.orchestrator.process_frame()

        frame = self.orchestrator.last_frame
        sem_cloud = self.orchestrator.last_semantic_cloud
        sem_map = self.orchestrator.last_map

        # Subsample point cloud for web payload if large (> 3000 points)
        n_points = frame.points.shape[0] if frame is not None else 0
        step = max(1, n_points // 3000)
        sub_pts = frame.points[::step].tolist() if frame is not None else []
        sub_classes = (
            sem_cloud.semantic_class[::step].tolist() if sem_cloud is not None else []
        )
        sub_intensities = (
            frame.intensity[::step].tolist()
            if frame is not None and frame.intensity is not None
            else []
        )

        cells_payload = {}
        if sem_map is not None:
            for level_name, level_cells in sem_map.cells.items():
                if isinstance(level_cells, dict):
                    for (gx, gy), c in level_cells.items():
                        cell_key = f"{level_name}_{gx}_{gy}"
                        cells_payload[cell_key] = {
                            "resolution_level": c.resolution_level,
                            "cell_x": c.cell_x,
                            "cell_y": c.cell_y,
                            "elevation": c.elevation,
                            "min_z": c.min_z,
                            "max_z": c.max_z,
                            "semantic_class": c.semantic_class,
                            "confidence": c.confidence,
                            "point_count": c.point_count,
                            "roughness": c.roughness,
                            "uncertainty": getattr(c, "uncertainty", 0.0),
                        }
                elif hasattr(level_cells, "resolution_level"):
                    c = level_cells
                    cells_payload[level_name] = {
                        "resolution_level": c.resolution_level,
                        "cell_x": c.cell_x,
                        "cell_y": c.cell_y,
                        "elevation": c.elevation,
                        "min_z": c.min_z,
                        "max_z": c.max_z,
                        "semantic_class": c.semantic_class,
                        "confidence": c.confidence,
                        "point_count": c.point_count,
                        "roughness": c.roughness,
                        "uncertainty": getattr(c, "uncertainty", 0.0),
                    }

        telemetry = self.orchestrator.profiler.get_telemetry_snapshot(
            point_count=n_points,
            cell_count=len(cells_payload),
        )
        telemetry["pipeline_mode"] = self.orchestrator.active_source_mode.value
        telemetry["frame_count"] = self.orchestrator.frame_count

        response_data = {
            "timestamp": frame.timestamp if frame else time.time(),
            "frame_id": frame.frame_id if frame else "sim",
            "points": sub_pts,
            "semantic_classes": sub_classes,
            "intensity": sub_intensities,
            "cells": cells_payload,
            "map_metadata": sem_map.metadata if sem_map else {},
            "telemetry": telemetry,
        }
        self._send_json(response_data)

    def _serve_cell_inspect(self, x: float, y: float) -> None:
        cell_info = self.orchestrator.grid_indexer.world_to_cell(x, y)
        if cell_info is None:
            self._send_json({"in_bounds": False})
            return

        level_id, cell_ix, cell_iy, cx, cy = cell_info
        ring = self.orchestrator.grid_indexer._rings_by_id[level_id]
        distance = float(np.hypot(x, y))

        self._send_json({
            "in_bounds": True,
            "cursor_pos": [x, y],
            "distance": distance,
            "level_id": level_id,
            "ring_name": ring.name,
            "base_resolution": ring.resolution,
            "cell_index": [cell_ix, cell_iy],
            "cell_center": [cx, cy],
        })


def run_server(
    port: int = 8080,
    host: str = "127.0.0.1",
    orchestrator: Optional[PipelineOrchestrator] = None,
) -> HTTPServer:
    """Launch the Autonomous Perception Control Center Web Server."""
    if orchestrator is None:
        orchestrator = PipelineOrchestrator()

    player = SequencePlayer(orchestrator=orchestrator, target_fps=10.0)

    class CustomServer(socketserver.TCPServer):
        allow_reuse_address = True

    ControlCenterHandler.orchestrator = orchestrator
    ControlCenterHandler.player = player

    server = CustomServer((host, port), ControlCenterHandler)
    print(f"\n=======================================================")
    print(f"  SYNTRiX // Autonomous Perception Control Center")
    print(f"  Server online at: http://{host}:{port}")
    print(f"=======================================================\n")
    return server


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")
    srv = run_server(port=port, host=host)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        srv.shutdown()
        srv.server_close()

