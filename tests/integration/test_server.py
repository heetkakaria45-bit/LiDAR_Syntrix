"""Unit tests for Visualization Web & REST Server Endpoints."""

import http.client
import json
import threading
import time
from src.integration.pipeline import PipelineMode, PipelineOrchestrator
from src.visualization.server import run_server


def test_server_endpoints_and_streaming() -> None:
    """Ensure server starts, serves index, streams video with Range headers, and handles API routes."""
    orchestrator = PipelineOrchestrator(mode=PipelineMode.SYNTHETIC)
    port = 8899
    host = "127.0.0.1"

    server = run_server(port=port, host=host, orchestrator=orchestrator)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    time.sleep(0.3)

    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)

        # 1. Test GET / (index.html)
        conn.request("GET", "/")
        res = conn.getresponse()
        assert res.status == 200
        content = res.read().decode("utf-8")
        assert "LiDAR_SYNTRIX" in content
        assert "three-container" in content

        # 2. Test GET /api/status
        conn.request("GET", "/api/status")
        res = conn.getresponse()
        assert res.status == 200
        status_data = json.loads(res.read().decode("utf-8"))
        assert status_data["status"] == "online"
        assert status_data["mode"] == "SYNTHETIC"

        # 3. Test GET /api/architecture
        conn.request("GET", "/api/architecture")
        res = conn.getresponse()
        assert res.status == 200
        arch_data = json.loads(res.read().decode("utf-8"))
        assert len(arch_data["pipeline_stages"]) == 7
        assert arch_data["pipeline_stages"][0]["owner"] == "Amulya"
        assert arch_data["pipeline_stages"][4]["owner"] == "Atharva"

        # 4. Test GET /api/frame
        conn.request("GET", "/api/frame")
        res = conn.getresponse()
        assert res.status == 200
        frame_data = json.loads(res.read().decode("utf-8"))
        assert "points" in frame_data
        assert "cells" in frame_data
        assert "telemetry" in frame_data
        assert frame_data["telemetry"]["pipeline_mode"] == "SYNTHETIC"

        # 5. Test GET /video.mp4 with Range header (HTTP 206 Partial Content)
        conn.request("GET", "/video.mp4", headers={"Range": "bytes=0-1024"})
        res = conn.getresponse()
        assert res.status in (200, 206)
        video_chunk = res.read()
        assert len(video_chunk) > 0

        # 6. Test POST /api/control (step action)
        payload = json.dumps({"action": "step"})
        conn.request("POST", "/api/control", body=payload, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        assert res.status == 200
        ctrl_data = json.loads(res.read().decode("utf-8"))
        assert ctrl_data["status"] == "ok"
        assert ctrl_data["action"] == "step"

        conn.close()
    finally:
        server.shutdown()
        server.server_close()
