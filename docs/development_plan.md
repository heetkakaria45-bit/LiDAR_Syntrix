# Development Roadmap & Execution Plan

This roadmap defines the chronological development phases (Phases A through K) for the **Foveated Semantic 2.5D LiDAR Mapping** project.

---

## Phase Breakdown Matrix

| Phase | Phase Name | Responsible Member | Dependencies | Primary Artifact |
| :---: | :--- | :--- | :--- | :--- |
| **A** | Foundation & Architecture | All (Lead: Atharva) | None | Core contracts, config, documentation, scaffolding |
| **B** | Synthetic End-to-End Pipeline | Himisha (Supported by All) | Phase A | Deterministic synthetic scene generator & mock pipeline |
| **C** | Real Dataset Integration | Amulya | Phase A | SemanticKITTI / nuScenes / Waymo dataset adapters |
| **D** | Baseline Semantic Perception | Vedant | Phase C | Point cloud semantic segmentation inference engine |
| **E** | Foveated Spatial Grid | Manashri | Phase A, B | Multi-resolution spatial hashing & indexing structures |
| **F** | 2.5D Semantic Mapping | Heet | Phase D, E | Elevation aggregation, roughness, traversability engine |
| **G** | Runtime Integration | Atharva | Phase D, E, F | Synchronous & streaming end-to-end pipeline runner |
| **H** | Performance Optimization | Manashri, Vedant, Atharva | Phase G | C++/Cython/Numba kernels, memory optimization |
| **I** | Adaptive Semantic Refinement | Manashri, Vedant | Phase E, F | Distance + semantic + uncertainty dynamic foveation |
| **J** | Final UI / Control Center Demo | Atharva | Phase G | Autonomous Perception Control Center (12 view modes) |
| **K** | Benchmarking & Validation | Himisha | Phase G, H, I | Uniform vs Foveated comparative benchmark suite |

---

## Detailed Phase Specifications

### Phase A — Foundation (Current Phase)
* **Objective:** Establish frozen system architecture, coordinate system, semantic taxonomy, foveation levels, shared data contracts, central configuration, minimal scaffolding, and smoke test suite.
* **Dependencies:** None.
* **Responsible Member:** All members (Architecture Lead: Atharva).
* **Expected Artifact:** `config/config.yaml`, `AGENTS.md`, `CONTRACTS.md`, `docs/`, `src/common/`, passing test foundation.
* **Acceptance Criteria:**
  1. All contracts and schemas load without external dependencies.
  2. Coordinate system is frozen to $X$=forward, $Y$=left, $Z$=up (in meters).
  3. Foveation levels (0..3) and Semantic taxonomy (0..7) are strictly defined.
  4. Unit and smoke tests execute with 100% pass rate.
  5. Zero major algorithmic modules implemented; zero Git modifications.

---

### Phase B — Synthetic End-to-End Pipeline
* **Objective:** Build deterministic synthetic 3D geometric scene generator (flat road, slope, curb, pothole, vehicles, pedestrians, poles, walls, overhangs) to validate pipeline flow without external dataset dependencies.
* **Dependencies:** Phase A contracts.
* **Responsible Member:** **Himisha** (`src/evaluation/`).
* **Expected Artifact:** `src/evaluation/synthetic.py`, synthetic test suite in `tests/synthetic/`.
* **Acceptance Criteria:**
  1. Deterministic generation of 10+ standard geometric obstacle scenarios.
  2. Synthesized point clouds conform strictly to `PointCloudFrame`.
  3. Provides reproducible ground-truth labels for early automated testing.

---

### Phase C — Real Dataset Integration
* **Objective:** Implement dataset loaders and label adapters for standard autonomous driving datasets (e.g. SemanticKITTI, nuScenes).
* **Dependencies:** Phase A contracts.
* **Responsible Member:** **Amulya** (`src/preprocessing/`).
* **Expected Artifact:** `src/preprocessing/dataset_adapter.py`, `src/preprocessing/kitti_adapter.py`.
* **Acceptance Criteria:**
  1. Correctly maps external dataset labels to project 8-class taxonomy.
  2. Validates point coordinates, intensities, and sensor poses into FLU meter frame.
  3. Unit tests verify exact label conversion mappings.

---

### Phase D — Baseline Semantic Perception
* **Objective:** Implement model-independent semantic segmentation inference wrapper (supporting PointNet++, SparseConv, or lightweight ONNX models).
* **Dependencies:** Phase C (Real Dataset Integration).
* **Responsible Member:** **Vedant** (`src/perception/`).
* **Expected Artifact:** `src/perception/engine.py`, model checkpoint loader, inference tests.
* **Acceptance Criteria:**
  1. Input `PointCloudFrame` produces valid `SemanticPointCloud`.
  2. All output labels are in range $[0..7]$ with confidences in $[0.0, 1.0]$.
  3. Achieves target inference latency baseline on standard test hardware.

---

### Phase E — Foveated Spatial Grid
* **Objective:** Design, benchmark, and implement multi-resolution spatial indexing data structures (spatial hashing / Morton codes / quadtree) with exact boundary handling.
* **Dependencies:** Phase A contracts, Phase B synthetic scenes.
* **Responsible Member:** **Manashri** (`src/foveated_grid/`).
* **Expected Artifact:** `src/foveated_grid/grid.py`, `src/foveated_grid/indexing.py`.
* **Acceptance Criteria:**
  1. Deterministic world-to-cell and cell-to-world round-trip precision ($< 10^{-6}\,m$).
  2. Correct handling of boundary points across all 4 zones ($0..10m, 10..25m, 25..50m, 50..100m$).
  3. Symmetric negative coordinate handling across all four quadrants.
  4. Insertion throughput $> 100,000$ points/sec.

---

### Phase F — 2.5D Semantic Mapping
* **Objective:** Implement elevation aggregation ($min\_z, max\_z, mean\_z$), surface roughness estimation, semantic voting/confidence aggregation, and geometric traversability scoring (step height, slope, roughness).
* **Dependencies:** Phase D (Perception), Phase E (Foveated Grid).
* **Responsible Member:** **Heet** (`src/mapping/`).
* **Expected Artifact:** `src/mapping/mapper.py`, `src/mapping/traversability.py`, `src/mapping/temporal.py`.
* **Acceptance Criteria:**
  1. Successfully distinguishes ground from obstacles using elevation and semantics.
  2. Accurately detects curbs ($0.15\,m$ step height) and negative obstacles (potholes).
  3. Computes continuous traversability cost $[0.0, 1.0]$.
  4. Temporal updater integrates multi-frame point observations.

---

### Phase G — Runtime Integration
* **Objective:** Connect all stage implementations into an end-to-end real-time pipeline runner with synchronous and streaming modes.
* **Dependencies:** Phases D, E, F.
* **Responsible Member:** **Atharva** (`src/integration/`).
* **Expected Artifact:** `src/integration/pipeline.py`, integration test suite in `tests/integration/`.
* **Acceptance Criteria:**
  1. End-to-end execution without memory leaks across 500+ sequential frames.
  2. Live telemetry timer collection for all pipeline stages.
  3. Full compatibility with live sensor streams and recorded dataset iterators.

---

### Phase H — Performance Optimization
* **Objective:** Optimize critical bottlenecks (spatial hashing, point aggregation, traversability analysis) using vectorization, Numba, or C++ extensions.
* **Dependencies:** Phase G.
* **Responsible Member:** **Manashri**, **Vedant**, **Atharva**.
* **Expected Artifact:** Optimized computational kernels, profiling benchmarks.
* **Acceptance Criteria:**
  1. End-to-end pipeline execution $> 20\,FPS$ ($< 50\,ms$ total latency).
  2. Host memory footprint remains bounded within $< 2\,GB$.

---

### Phase I — Adaptive Semantic Refinement
* **Objective:** Implement extension hook for dynamic resolution assignment:
  $$\text{Resolution} = f(\text{distance}, \text{semantic\_importance}, \text{uncertainty})$$
  Allocating high resolution to critical dynamic objects (pedestrians, vehicles) even at extended ranges.
* **Dependencies:** Phase E, Phase F.
* **Responsible Member:** **Manashri**, **Vedant**.
* **Expected Artifact:** `src/foveated_grid/adaptive.py`.
* **Acceptance Criteria:**
  1. Selectively refines cell resolution for high-importance semantic targets.
  2. Maintains deterministic boundary safety and overall cell budget constraints.

---

### Phase J — Final UI / Control Center Demo
* **Objective:** Build the interactive Autonomous Perception Control Center supporting all 12 operational views and real-time telemetry.
* **Dependencies:** Phase G.
* **Responsible Member:** **Atharva** (`src/visualization/`).
* **Expected Artifact:** `src/visualization/control_center.py`.
* **Acceptance Criteria:**
  1. Live interactive rendering across 12 distinct viewing modes.
  2. Displays real-time latency graphs, FPS, cell counts, and memory meters.
  3. Cell/fovea click inspector shows exact elevation, roughness, and class confidences.

---

### Phase K — Benchmarking and Validation
* **Objective:** Execute comprehensive quantitative evaluation comparing Uniform High-Resolution Grid ($0.05\,m$) against the Foveated 2.5D Semantic Grid.
* **Dependencies:** Phase G, H, I.
* **Responsible Member:** **Himisha** (`src/evaluation/`).
* **Expected Artifact:** `src/evaluation/benchmark_suite.py`, benchmark report artifact.
* **Acceptance Criteria:**
  1. Measures exact latency, memory, cell count, and compression ratio.
  2. Proves memory and compute savings of foveated representation over uniform high-res grid.
  3. Strictly zero fabricated metrics; all results verified by automated test logs.
