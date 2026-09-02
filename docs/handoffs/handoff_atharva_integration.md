# Module Handoff & Interface Specification: Integration & Visualization

- **Module Path:** `src/integration/` & `src/visualization/`
- **Owner:** Atharva
- **Role:** System Integration, Real-Time Orchestration & Advanced UI
- **Status:** Phase 2 Architecture Frozen

---

## 1. Responsibilities
- Orchestrate end-to-end pipeline: Preprocessing $\rightarrow$ Perception $\rightarrow$ Spatial Grid $\rightarrow$ 2.5D Mapping $\rightarrow$ UI Render.
- Manage 3-tier fallback execution: `REAL_LIDAR` $\rightarrow$ `PRECOMPUTED` $\rightarrow$ `SYNTHETIC`.
- Measure anti-fabrication latency and memory telemetry (RSS MB, per-stage ms, FPS).
- Provide interactive Autonomous Perception Control Center (Web UI and terminal dashboard).
- Provide one-command demo launcher (`python scripts/run_demo.py`).

## 2. Integration API
```python
from src.integration import PipelineMode, PipelineOrchestrator, SequencePlayer
from src.visualization import run_server

orchestrator = PipelineOrchestrator(mode=PipelineMode.SYNTHETIC)
input_frame, sem_cloud, sem_map, telemetry = orchestrator.process_frame()

# Web visualizer server
server = run_server(port=8080, orchestrator=orchestrator)
```

## 3. Verification Command
```bash
pytest tests/integration/ -v
```
