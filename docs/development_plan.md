# Project Development Roadmap & Phase Blueprint (Phases A – K)

> **Event:** Smart India Hackathon (SIH 2026)  
> **Status:** Architecture Freeze (Phase 2)  
> **Rule:** Every developer works on their designated feature branch and submits PRs with deterministic unit tests.

---

## 1. Roadmap Overview

```
[Phase A: Foundation] ──► [Phase B: Synthetic E2E Pipeline] ──► [Phase C: Dataset Pipeline]
                                                                        │
┌───────────────────────────────────────────────────────────────────────┘
▼
[Phase D: Perception] ──► [Phase E: Foveated Grid] ──► [Phase F: 2.5D Mapping]
                                                                │
┌───────────────────────────────────────────────────────────────┘
▼
[Phase G: Integration] ──► [Phase H: Optimization] ──► [Phase I: Adaptive Refinement]
                                                                │
┌───────────────────────────────────────────────────────────────┘
▼
[Phase J: UI Control Center] ──► [Phase K: Benchmarking & Final Validation]
```

---

## 2. Phase-by-Phase Specifications

### PHASE A: Foundation Initialized
- **Objective:** Establish the shared engineering foundation, directory skeleton, git repository, core documentation, and base smoke test suite.
- **Dependencies:** None.
- **Responsible Member:** Pair Programming Team (Antigravity + Heet).
- **Expected Artifact:** Clean git repo, `AGENTS.md`, `CONTRACTS.md`, `pyproject.toml`, `configs/default_config.yaml`, and passing smoke tests.
- **Acceptance Criteria:** `pytest tests/ -v` passes 100%; zero untracked temp files; branch pushed to remote repository.
- **Status:** **COMPLETED** (Commit `6f5422c`).

---

### PHASE B: Synthetic End-to-End Pipeline
- **Objective:** Build a deterministic geometric synthetic scene generator and end-to-end mock pipeline so all six developers can run functional tests immediately without waiting for datasets or model weights.
- **Dependencies:** Phase A.
- **Responsible Member:** Amulya (`src/preprocessing/`) with Atharva (`src/integration/`).
- **Expected Artifact:** `src/preprocessing/synthetic.py` generating curbs, potholes, slopes, vehicles, pedestrians, and walls; pipeline integration mock test.
- **Acceptance Criteria:** Deterministic point clouds generated matching `PointCloudFrame` contract; end-to-end mock execution runs in $< 50\text{ ms}$.

---

### PHASE C: Real Dataset Ingestion & Preprocessing
- **Objective:** Ingest SemanticKITTI and nuScenes dataset formats, apply coordinate transforms, range clipping, and outlier removal to produce validated `PointCloudFrame` instances.
- **Dependencies:** Phase B.
- **Responsible Member:** Amulya (`src/preprocessing/`).
- **Expected Artifact:** Dataset loaders (`kitti_loader.py`, `nuscenes_loader.py`), outlier filter module, dataset-to-project class mapping dictionary.
- **Acceptance Criteria:** Successfully loads 100 sequential frames; guarantees zero `NaN`/`Inf` coordinates; validates coordinate frame ($X=\text{forward}, Y=\text{left}, Z=\text{up}$).

---

### PHASE D: Baseline Semantic Perception
- **Objective:** Integrate a lightweight, modular deep learning 3D semantic segmentation model producing per-point class predictions and confidence scores.
- **Dependencies:** Phase C.
- **Responsible Member:** Vedant (`src/perception/`).
- **Expected Artifact:** `BaseSemanticSegmenter` interface, inference engine (e.g. Range-Image CNN / Sparse Conv or ONNX runtime), class probability output matching project taxonomy.
- **Acceptance Criteria:** Generates valid `SemanticPointCloud` contract instances; per-point confidence bounded in $[0.0, 1.0]$; CPU fallback inference functional.

---

### PHASE E: Foveated Spatial Grid Structure
- **Objective:** Implement the multi-ring hierarchical variable-resolution grid, deterministic world-to-cell coordinate mapping, and fast point-to-cell assignment.
- **Dependencies:** Phase B, Phase C.
- **Responsible Member:** Manashri (`src/foveated_grid/`).
- **Expected Artifact:** Spatial indexer (`foveated_indexer.py`) supporting Levels 0–3 ($5\text{ cm}, 10\text{ cm}, 25\text{ cm}, 50\text{ cm}$), ring boundary collision handlers.
- **Acceptance Criteria:** Benchmarked point-to-cell assignment throughput $> 500,000\text{ points/sec}$; exact half-open boundary $[r_k, r_{k+1})$ preservation; unit tests pass for negative coordinates and cell centers.

---

### PHASE F: 2.5D Semantic Mapping & Hazard Detection
- **Objective:** Fuse elevation statistics and semantic labels per cell; implement deterministic geometric algorithms for curb, pothole, and overhang hazard detection.
- **Dependencies:** Phase D, Phase E.
- **Responsible Member:** Heet (`src/mapping/`).
- **Expected Artifact:** `ElevationAggregator`, `SemanticBayesianFilter`, `HazardDetector` (curb step discontinuity, pothole depth filter, overhang clearance).
- **Acceptance Criteria:** Generates complete `SemanticMap`; detects curbs between $8\text{ cm}$ and $25\text{ cm}$ step height; detects potholes $> 5\text{ cm}$ depth; distinguishes traversable overhead structures ($> 2.2\text{ m}$).

---

### PHASE G: Real-Time Pipeline Integration & Orchestration
- **Objective:** Wire all six stages into a high-throughput, multithreaded asynchronous perception pipeline with real-time performance telemetry.
- **Dependencies:** Phases C, D, E, F.
- **Responsible Member:** Atharva (`src/integration/`).
- **Expected Artifact:** `PipelineOrchestrator`, double-buffered frame pipeline, live telemetry profiler recording per-stage latency and RAM/VRAM usage.
- **Acceptance Criteria:** Full pipeline runs asynchronously without deadlocks; zero-copy NumPy memory passing; end-to-end telemetry recorded without performance fabrication.

---

### PHASE H: Performance Optimization & Hardware Acceleration
- **Objective:** Profile and eliminate execution bottlenecks across the spatial indexer, vectorization, and inference routines.
- **Dependencies:** Phase G.
- **Responsible Members:** All Team Members (coordinated by Atharva).
- **Expected Artifact:** Vectorized NumPy / Numba / Cython inner loops; GPU memory pooling; reduced point-to-cell projection latency.
- **Acceptance Criteria:** End-to-end pipeline operates at $\ge 15\text{ FPS}$ on test workstation; memory footprint remains $\le 500\text{ MB}$.

---

### PHASE I: Adaptive Semantic & Uncertainty Refinement
- **Objective:** Implement dynamic, multi-factor cell refinement triggering fine-grained sub-cells for high-priority semantic objects (pedestrians, vehicles) or uncertain terrain at extended ranges.
- **Dependencies:** Phase E, Phase F, Phase H.
- **Responsible Members:** Manashri, Heet, and Vedant.
- **Expected Artifact:** `AdaptiveRefiner` implementing $\text{Resolution} = f(\text{distance}, \text{semantic\_importance}, \text{uncertainty})$.
- **Acceptance Criteria:** Detectable pedestrian at $70\text{ m}$ refines locally from $50\text{ cm}$ to $10\text{ cm}$ without increasing cell resolution in adjacent ground cells.

---

### PHASE J: Autonomous Perception Control Center UI
- **Objective:** Build the interactive, mission-critical 12-view visualization application displaying real-time elevation, traversability, foveation bands, and side-by-side uniform comparisons.
- **Dependencies:** Phase G, Phase I.
- **Responsible Member:** Atharva (`src/visualization/`).
- **Expected Artifact:** WebGL / Three.js or native VisPy desktop control center; interactive cell inspector; temporal playback controls.
- **Acceptance Criteria:** Renders 12 specified views from live pipeline stream or recorded `.bin` files; zero lag induced on perception thread; interactive inspector displays real cell attributes.

---

### PHASE K: Benchmarking, Validation & Final SIH Demonstration
- **Objective:** Execute exhaustive quantitative comparative benchmarks (Uniform vs. Foveated) and assemble demonstration materials.
- **Dependencies:** All previous phases.
- **Responsible Member:** Himisha (`src/evaluation/`).
- **Expected Artifact:** Automated benchmark suite, distance-stratified accuracy tables (mIoU, elevation RMSE), memory reduction proof ($\ge 90\%$), final presentation visuals.
- **Acceptance Criteria:** All numbers generated and verified by automated reproduction scripts; hardware specifications documented; zero fabricated statistics; complete SIH 2026 submission package ready.
