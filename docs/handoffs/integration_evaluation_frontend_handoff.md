# SYNTRIX — Official Engineering Handoff: Integration, Evaluation & Frontend

> **Target Reviewer & Release Integrator:** Vedant (Lead Architect & Perception Owner)  
> **Author & Module Owner:** Atharva Hoge (Integration, Evaluation, Telemetry, Server & Frontend)  
> **Owned Workstreams:** `src/integration/`, `src/evaluation/`, `src/visualization/`, `frontend/`  
> **Branch:** `feature/atharva-integration`  
> **Status:** Fully Integrated, Tested (109/109 Tests Green), and Ready for Merge  

---

## 1. Purpose

This document provides the exhaustive, reproducible engineering handoff for the **Integration, Evaluation, Telemetry, Backend/API, and Frontend WebGL Control Center** of the SYNTRIX (LiDAR_Syntrix) project. It establishes the single authoritative end-to-end execution path, defines empirical benchmark results against the Uniform 5cm baseline with explicit provenance tags, validates live API field traceability, and details the 3-tier presentation demo hierarchy for the SIH 2026 jury.

---

## 2. Authoritative E2E Pipeline

The authoritative system execution path flows sequentially across all repository modules:

```text
[1] LiDAR Preprocessing (Amulya — src/preprocessing/)
        ↓  PointCloudFrame (Nx3 points, intensity, sensor pose)
[2] Semantic Point Cloud Perception (Vedant — src/perception/)
        ↓  SemanticPointCloud (Nx3 points, class IDs 0..7, confidences)
[3] Foveated Variable-Resolution Grid (Manashri — src/foveated_grid/)
        ↓  Multi-Ring Spatial Index (0-10m @ 5cm, 10-25m @ 10cm, 25-50m @ 25cm, 50-100m @ 50cm)
[4] 2.5D Elevation & Traversability Mapping (Heet — src/mapping/)
        ↓  SemanticMap (Multi-resolution GridCell hierarchy)
[5] Terrain Traversability & Hazard Detection (Heet — src/mapping/)
        ↓  Hazards Summary (Curbs, Potholes, Overhangs, Obstacles)
[6] System Orchestration & Real-Time Telemetry (Atharva — src/integration/)
        ↓  Telemetry Snapshot (Microsecond stage timings, RAM RSS, FPS)
[7] Evaluation & Distance Stratification (Himisha & Atharva — src/evaluation/)
        ↓  Quantitative Accuracy Metrics (mIoU, Elevation RMSE/MAE)
[8] REST API Server & Three.js WebGL Console (Atharva — src/visualization/ + frontend/)
        ↓  Interactive Autonomous Perception HUD
```

---

## 3. Exact E2E Command

The canonical end-to-end Python pipeline command is:

```bash
python3 -c "from src.integration import PipelineOrchestrator; p = PipelineOrchestrator(); f, sc, sm, tel = p.process_frame(); print('Pipeline OK! Frame points:', f.points.shape[0], 'Active Cells:', sum(len(lvl) for lvl in sm.cells.values()), 'FPS:', tel['fps'])"
```

---

## 4. Pipeline Data Contracts

| Stage | Input Contract | Output Contract | Function / Method | File Location | Shape & Dtype |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Ingestion / Preprocessing** | Raw binary/PCD/Synthetic | `PointCloudFrame` | `validate_and_sanitize_points()` | `src/preprocessing/filters.py` | `points`: `(N, 3), float32`<br>`intensity`: `(N,), float32` |
| **2. Semantic Perception** | `PointCloudFrame` | `SemanticPointCloud` | `BaseSemanticSegmenter.infer()` | `src/perception/base.py`<br>`src/perception/mock.py` | `semantic_class`: `(N,), int32`<br>`confidence`: `(N,), float32` |
| **3. Foveated Grid Indexing** | `SemanticPointCloud.points` | Spatial Ring Assignments | `FoveatedGridIndexer.assign_points()` | `src/foveated_grid/grid_indexer.py` | `Dict[ring_name, Dict[key, pt_indices]]` |
| **4. 2.5D Semantic Mapping** | `SemanticPointCloud` + Ring Assignments | `SemanticMap` | `SemanticElevationMapper.map_point_cloud()` | `src/mapping/mapper.py`<br>`src/mapping/aggregation.py` | `cells`: `Dict[str, Dict[Tuple[int, int], GridCell]]` |
| **5. Hazard Reasoning** | `SemanticMap` | Terrain & Hazard Summaries | `analyze_map_terrain()`, `detect_map_hazards()` | `src/mapping/terrain.py`<br>`src/mapping/hazards.py` | `curbs`, `potholes`, `overhangs`, `obstacles` |
| **6. System Orchestration** | Pipeline components | Telemetry Snapshot | `PipelineOrchestrator.process_frame()` | `src/integration/pipeline.py` | `telemetry`: `Dict[str, Any]` |
| **7. Evaluation** | Predicted vs Ground Truth | Evaluation Metrics | `compute_semantic_iou()`, `compute_distance_stratified_metrics()` | `src/evaluation/metrics.py` | `mIoU`, `elevation_rmse`, `stratified` |
| **8. Web Visualization** | `SemanticMap` + `Telemetry` | WebGL HUD / REST API | `ControlCenterHandler`, React components | `src/visualization/server.py`<br>`frontend/src/` | REST JSON Payloads (`/api/frame`, `/api/benchmark`) |

---

## 5. Evaluation Integration

Evaluation is natively wired into `PipelineOrchestrator.process_frame()`. When ground truth is present, evaluation executes synchronously and embeds results directly into `semantic_map.metadata["evaluation"]` and `telemetry["evaluation"]`.

- **Perception Model Status:** Deterministic Synthetic/Mock (`MockSemanticSegmenter`).
- **Ground Truth Source:** Deterministic procedural scene geometry (`generate_synthetic_scene`).
- **No Latency Penalty:** Evaluation is guarded by ground truth presence and executes in $< 1.5\text{ ms}$.

---

## 6. Evaluation Metrics & Results

- **Semantic mIoU:** Evaluated across 8 project classes ($0$: Road, $1$: Sidewalk, $2$: Vehicle, $3$: Pedestrian, $4$: Vegetation, $5$: Terrain, $6$: Structure, $7$: Other Obstacle).
- **Distance-Stratified Elevation RMSE:**
  - `Near (0-10m)`: $1.1\text{ cm}$ RMSE
  - `Mid-Near (10-25m)`: $2.5\text{ cm}$ RMSE
  - `Mid (25-50m)`: $5.2\text{ cm}$ RMSE
  - `Far (50-100m)`: $10.8\text{ cm}$ RMSE

---

## 7. Uniform 5cm vs Foveated Benchmark

The repository implements a head-to-head empirical comparison in `src/evaluation/benchmark.py:BenchmarkRunner.run_comparative_benchmark()`.

- **Baseline:** Uniform $5\text{cm}$ ($0.05\text{m}$) high-resolution grid over the full $200\text{m} \times 200\text{m}$ domain.
- **SYNTRIX:** Foveated Multi-Ring Grid ($5\text{cm}$ @ $0\text{--}10\text{m}$, $10\text{cm}$ @ $10\text{--}25\text{m}$, $25\text{cm}$ @ $25\text{--}50\text{m}$, $50\text{cm}$ @ $50\text{--}100\text{m}$).

---

## 8. Benchmark Methodology

- **Input Point Cloud:** Standardized 12,000-point deterministic urban scene (seed 42).
- **Spatial Extent:** $X \in [-100\text{m}, +100\text{m}], Y \in [-100\text{m}, +100\text{m}]$.
- **Host Execution:** Apple M-series (`macOS-26.5.2-arm64`), Python 3.14.2 Standard CPython.
- **Timing:** 1 warmup run + 5 timed iterations measured with `time.perf_counter()`.
- **Fair Conditions:** Identical points, identical cell aggregation logic (`aggregate_cell`), identical thread priority.

---

## 9. Benchmark Results

```json
{
  "metadata": {
    "benchmark_name": "Uniform_vs_Foveated_Evaluation",
    "scene_type": "urban",
    "point_count": 12000,
    "num_iterations": 5,
    "hardware": {
      "platform": "macOS-26.5.2-arm64-arm-64bit-Mach-O",
      "processor": "arm",
      "machine": "arm64",
      "python_version": "3.14.2"
    }
  },
  "uniform_vs_foveated": {
    "uniform_cell_count": 9059,
    "foveated_cell_count": 6542,
    "cell_reduction_ratio": 1.38,
    "memory_uniform_mb": 0.55,
    "memory_foveated_mb": 0.40,
    "memory_reduction_pct": 27.8,
    "processing_time_uniform_ms": 53.74,
    "processing_time_foveated_ms": 59.21,
    "speedup_factor": 0.91
  }
}
```

---

## 10. Provenance Classification

| Metric Category | Metrics Included | Provenance Tag | Definition |
| :--- | :--- | :---: | :--- |
| **Measured Runtime** | Active cell counts (9,059 vs 6,542), mapping latencies (53.74 ms vs 59.21 ms), RAM RSS (69.02 MB), FPS (9.5 FPS) | **MEASURED** | Directly measured from live host execution |
| **Derived Ratios** | Active cell ratio ($1.38:1$), active cell memory savings ($27.8\%$) | **CALCULATED** | Arithmetically derived from measured counts |
| **Dense Grid Area** | Full $200\text{m} \times 200\text{m}$ grid reduction ($16\text{M} \to 738\text{k}$ cells, $95.39\%$ memory reduction) | **THEORETICAL** | Continuous geometric annulus integral |
| **Operational Goals** | Closed-loop vehicle refresh rate ($10\text{--}30\text{ FPS}$) | **TARGET** | Target performance specification |

---

## 11. Telemetry Methodology

- **Timing Source:** Wall-clock microsecond timer (`time.perf_counter()`).
- **Stages Profiled:** `preprocessing`, `inference`, `grid_indexing`, `mapping`, `hazard_analysis`, and `total`.
- **Memory Source:** OS Resident Set Size via `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`.
- **Sliding Window:** Last 100 observations stored for minimum, maximum, and rolling mean computation.

---

## 12. API Endpoints

| Endpoint | Method | Response Description | Data Source |
| :--- | :---: | :--- | :--- |
| **`/api/status`** | `GET` | `{"status": "online", "mode": "SYNTHETIC", "frame_count": 1}` | Live pipeline state |
| **`/api/architecture`** | `GET` | 7-stage architectural specifications & ownership registry | Architecture metadata |
| **`/api/frame`** | `GET` | Subsampled 3D points, semantic labels, multi-ring cells, hazards, telemetry | `PipelineOrchestrator.process_frame()` |
| **`/api/benchmark`** | `GET` | Dynamic comparative benchmark payload (Uniform vs Foveated) | `BenchmarkRunner.run_comparative_benchmark()` |
| **`/api/cell_inspect`** | `GET` | `x, y` query $\to$ Ring ID, cell center, resolution, elevation bounds, roughness | `grid_indexer.world_to_cell()` |
| **`/api/control`** | `POST` | `{"action": "play"|"pause"|"step"|"reset"|"set_scene"}` | `SequencePlayer` |

---

## 13. API Field Traceability

- `points`: [`src/preprocessing/filters.py:validate_and_sanitize_points`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/preprocessing/filters.py)
- `semantic_classes`: [`src/perception/base.py:BaseSemanticSegmenter.infer`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/perception/base.py)
- `cells`: [`src/mapping/mapper.py:SemanticElevationMapper.map_point_cloud`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/mapping/mapper.py)
- `map_metadata.hazards_summary`: [`src/mapping/hazards.py:detect_map_hazards`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/mapping/hazards.py)
- `telemetry.stage_latencies_ms`: [`src/integration/telemetry.py:TelemetryProfiler`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/integration/telemetry.py)
- `telemetry.memory.ram_rss_mb`: [`src/integration/telemetry.py:TelemetryProfiler`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/integration/telemetry.py)

---

## 14. Frontend Data Sources

- **Point Cloud Viewport:** Consumes live `/api/frame -> points` (`MEASURED`).
- **Occupied Grid Cells:** Consumes live `/api/frame -> cells` (`MEASURED`).
- **Volumetric Hazard Light Beams:** Consumes live `/api/frame -> map_metadata.hazards` (`MEASURED`).
- **Telemetry HUD:** Consumes live `/api/frame -> telemetry` (`MEASURED`).
- **Benchmark Modal:** Consumes live `/api/benchmark` (`MEASURED` + `CALCULATED`).
- **DRDO Cell Inspector:** Consumes live `/api/cell_inspect?x=..&y=..` (`CALCULATED`).
- **UGV Vehicle Chassis:** Static PBR visual asset (`STATIC VISUAL`).

---

## 15. Primary Demo Startup

```bash
python3 -m src.visualization.server --port 8080
# Open browser at http://localhost:8080/
```

---

## 16. Backup Demo Startup

```bash
python3 scripts/run_demo.py --port 8080
# Serves pre-validated outputs from outputs/benchmark_results.json
```

---

## 17. Offline Demo Startup

```bash
cd frontend && npm run dev
# Engages client-side SimulationEngine fallback with zero server dependencies
```

---

## 18. Dependencies

- **Core Dependencies:** Python 3.10+, NumPy, PyYAML, Pytest (strictly lightweight baseline).
- **Frontend Dependencies:** Node.js, React 18, Three.js, Lucide-React, Recharts, TailwindCSS, Vite.
- **Hardware Agnostic:** Guarded optional imports prevent hardware locks.

---

## 19. Test Results

- `pytest tests/ -v`: **109 / 109 tests passing in 3.10s (100% green)**.
- `pytest tests/integration/ tests/evaluation/ -v`: **12 / 12 tests passing in 2.49s**.
- `npm run --prefix frontend build`: **2,223 modules transformed in 1.75s (0 errors, 0 warnings)**.

---

## 20. Known Limitations

1. **Temporal Tracking:** PARTIALLY IMPLEMENTED (Data contracts define observation count and uncertainty; multi-frame Kalman fusion is future work).
2. **Velocity Estimation:** NOT IMPLEMENTED (Out of scope for Phase 2).
3. **Real Edge Hardware Validation:** NOT VALIDATED (Host CPU tested; physical Jetson validation is future work).
4. **Adverse Weather Validation:** NOT VALIDATED (Rain/fog point cloud scattering is future work).
5. **Real LiDAR Sensor Validation:** PARTIALLY IMPLEMENTED (Ingestion and range sanitization filters implemented; physical sensor not connected in CI).
6. **ROS 2 Live Integration:** PARTIALLY IMPLEMENTED (Message bridges defined; live DDS daemon is future work).
7. **Long-Duration Deployment:** NOT VALIDATED.
8. **GPU Inference Validation:** NOT VALIDATED (CPU-only guarded architecture active).

---

## 21. Merge Instructions / Handoff

1. Target branch for merge: `main` (or integration staging).
2. Merging lead: **Vedant** (Lead Architect & Perception Owner).
3. Status: Clean working tree on `feature/atharva-integration`, all 109 unit/integration/evaluation tests passing, zero P0/P1 blockers.

---
*Signed off by Atharva Hoge — Integration, Evaluation & Frontend Lead (SIH 2026)*
