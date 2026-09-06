# SYNTRIX — Official Engineering Handoff: Integration, Evaluation & Frontend

> **Target Reviewer & Release Integrator:** Vedant (Lead Architect & Perception Owner)  
> **Author & Module Owner:** Atharva Hoge  
> **Owned Workstreams:** `src/integration/`, `src/evaluation/`, `src/visualization/`, `frontend/`  
> **Branch:** `feature/atharva-integration`  
> **Status:** Fully Integrated, Tested (109/109 Tests Green), and Ready for Merge  

---

## 1. CANONICAL END-TO-END PIPELINE

The single authoritative execution pipeline flows sequentially across all 6 team submodules:

```
[1] LiDAR Ingestion & Preprocessing (Amulya — src/preprocessing/)
        ↓  PointCloudFrame (Nx3 coordinates, intensity, sensor pose)
[2] Semantic Point Cloud Perception (Vedant — src/perception/)
        ↓  SemanticPointCloud (Nx3 coordinates, class IDs 0..7, confidences)
[3] Foveated Variable-Resolution Spatial Grid (Manashri — src/foveated_grid/)
        ↓  Multi-Ring Spatial Index (Ring 0: 5cm @ 0-10m, Ring 1: 10cm @ 10-25m, Ring 2: 25cm @ 25-50m, Ring 3: 50cm @ 50-100m)
[4] 2.5D Semantic Elevation Mapping (Heet — src/mapping/)
        ↓  SemanticMap (Multi-resolution GridCell hierarchy)
[5] Terrain Traversability & Hazard Detection (Heet — src/mapping/)
        ↓  Hazards & Obstacles (Curbs, Potholes, Overhangs, Step Drops)
[6] System Orchestration & Real-Time Telemetry (Atharva — src/integration/)
        ↓  Telemetry Snapshot (Microsecond stage timings, RAM RSS, FPS)
[7] Evaluation & Distance Stratification (Himisha & Atharva — src/evaluation/)
        ↓  Quantitative Metrics (mIoU, Elevation RMSE/MAE across distance rings)
[8] Interactive 3D WebGL Console & HUD (Atharva — src/visualization/ + frontend/)
```

### Exact Canonical Commands
```bash
# 1. Execute end-to-end Python pipeline test run
python3 -c "from src.integration import PipelineOrchestrator; p = PipelineOrchestrator(); f, sc, sm, tel = p.process_frame(); print('Pipeline OK! Frame points:', f.points.shape[0], 'Active Cells:', len(sm.cells), 'FPS:', tel['fps'])"

# 2. Launch the Autonomous Perception Control Center Web Server (port 8080)
python3 -m src.visualization.server --port 8080
```

---

## 2. STAGE-BY-STAGE DATA FLOW SPECIFICATION

| Stage | Input Data | Output Data | Function / Method | File Path | Data Format & Shapes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Preprocessing** | Raw binary/PCD/Synthetic points | `PointCloudFrame` | `validate_and_sanitize_points()` | [`src/preprocessing/filters.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/preprocessing/filters.py) | `points`: `(N, 3), float32`<br>`intensity`: `(N,), float32`<br>`sensor_pose`: `(4, 4), float64` |
| **2. Perception** | `PointCloudFrame` | `SemanticPointCloud` | `BaseSemanticSegmenter.infer()` | [`src/perception/base.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/perception/base.py)<br>[`src/perception/mock.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/perception/mock.py) | `points`: `(N, 3), float32`<br>`semantic_class`: `(N,), int32` ($0\text{--}7$)<br>`confidence`: `(N,), float32` ($0.0\text{--}1.0$) |
| **3. Foveated Grid** | `SemanticPointCloud.points` | Spatial Ring Assignments | `FoveatedGridIndexer.assign_points()` | [`src/foveated_grid/grid_indexer.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/foveated_grid/grid_indexer.py) | `Dict[ring_name, Dict[(gx, gy), (cx, cy, pt_indices_array)]]` |
| **4. 2.5D Mapping** | `SemanticPointCloud` + Spatial Assignments | `SemanticMap` | `SemanticElevationMapper.map_point_cloud()` | [`src/mapping/mapper.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/mapping/mapper.py)<br>[`src/mapping/aggregation.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/mapping/aggregation.py) | `cells`: `Dict[str, Dict[Tuple[int, int], GridCell]]`<br>`resolution_levels`: `Dict[str, float]` |
| **5. Hazard Detection**| `SemanticMap` | Terrain & Hazard Summaries | `analyze_map_terrain()`, `detect_map_hazards()` | [`src/mapping/terrain.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/mapping/terrain.py)<br>[`src/mapping/hazards.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/mapping/hazards.py) | `curbs`: List of step drops<br>`potholes`: List of depressions<br>`overhangs`: List of elevated structures |
| **6. Orchestration** | Pipeline components | Telemetry snapshot & synced frame | `PipelineOrchestrator.process_frame()` | [`src/integration/pipeline.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/integration/pipeline.py)<br>[`src/integration/telemetry.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/integration/telemetry.py) | `telemetry`: `Dict[str, Any]` (FPS, stage timings, RAM RSS) |
| **7. Evaluation** | Predicted classes & surface elevations vs. Ground Truth | Evaluation metrics | `compute_semantic_iou()`, `compute_elevation_rmse()`, `compute_distance_stratified_metrics()` | [`src/evaluation/metrics.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/evaluation/metrics.py) | `mIoU`: `float`<br>`elevation_rmse`: `float`<br>`distance_stratified`: `Dict[str, Dict]` |
| **8. Visualization** | `SemanticMap` + `Telemetry` | Three.js WebGL rendering & REST API | `ControlCenterHandler`, React components | [`src/visualization/server.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/visualization/server.py)<br>[`frontend/src/`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/frontend/src/) | JSON REST Payloads (`/api/frame`, `/api/benchmark`, `/api/cell_inspect`) |

---

## 3. EVALUATION & ACCURACY METRICS SPECIFICATION

All evaluation functions reside in [`src/evaluation/metrics.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/evaluation/metrics.py):

### 3.1. Semantic Intersection-over-Union (mIoU)
- **Input:** `pred_classes` (`np.ndarray (N,), int32`), `gt_classes` (`np.ndarray (N,), int32`), `num_classes = 8`.
- **Formula:**
  $$\text{IoU}_c = \frac{TP_c}{TP_c + FP_c + FN_c}, \quad \text{mIoU} = \frac{1}{|C_{\text{valid}}|} \sum_{c \in C_{\text{valid}}} \text{IoU}_c$$
- **Output:** Dictionary containing `per_class_iou`, `per_class_precision`, `per_class_recall`, `mIoU`.
- **Units:** Percentage ($0.0\text{--}100.0\%$) or float ($0.0\text{--}1.0$).

### 3.2. Elevation Root Mean Square Error (RMSE) & Mean Absolute Error (MAE)
- **Input:** `pred_elevations` (`np.ndarray (M,), float32`), `gt_elevations` (`np.ndarray (M,), float32`).
- **Formula:**
  $$\text{RMSE} = \sqrt{\frac{1}{M} \sum_{i=1}^M (z_{\text{pred}, i} - z_{\text{gt}, i})^2}, \quad \text{MAE} = \frac{1}{M} \sum_{i=1}^M |z_{\text{pred}, i} - z_{\text{gt}, i}|$$
- **Output:** `{"rmse": float, "mae": float}`.
- **Units:** Meters ($\text{m}$) or Centimeters ($\text{cm}$).

### 3.3. Distance-Stratified Error Analysis
- **Input:** `distances = hypot(x, y)` (`np.ndarray (N,)`), `pred_elevations`, `gt_elevations`.
- **Concentric Distance Bins:**
  1. `Ring 0 (Near)`: $0\text{m} \le r < 10\text{m}$ (Resolution: $5\text{cm}$)
  2. `Ring 1 (Mid-Near)`: $10\text{m} \le r < 25\text{m}$ (Resolution: $10\text{cm}$)
  3. `Ring 2 (Mid)`: $25\text{m} \le r < 50\text{m}$ (Resolution: $25\text{cm}$)
  4. `Ring 3 (Far)`: $50\text{m} \le r \le 100\text{m}$ (Resolution: $50\text{cm}$)
- **Output:** Per-ring RMSE, MAE, and allocated point count.

---

## 4. UNIFORM 5CM FAIR BASELINE SPECIFICATION

To ensure a scientifically rigorous and non-biased comparison, the baseline was implemented in [`src/evaluation/benchmark.py:run_comparative_benchmark`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/evaluation/benchmark.py):

- **Spatial Domain:** $X \in [-100\text{m}, +100\text{m}]$, $Y \in [-100\text{m}, +100\text{m}]$ (200m sensing diameter).
- **Uniform Grid Resolution:** Uniform $0.05\text{m}$ ($5\text{cm}$) across the entire spatial domain.
- **Active vs. Dense Cell Allocation:**
  - *Theoretical Dense Grid:* $(200 / 0.05)^2 = 16,000,000\text{ cells} \implies 1,024\text{ MB}$ (at $64\text{ bytes/cell}$).
  - *Observed Active Grid:* $9,059\text{ active cells}$ for 12,000 raw points $\implies 0.55\text{ MB}$.
- **Comparison Methodology:**
  1. Exactly the same input point cloud frame (same seed, same noise, same geometry).
  2. Executed on the identical host CPU under identical thread priority.
  3. Same cell aggregation logic (`aggregate_cell`: min_z, max_z, median elevation, weighted majority semantic class).
  4. Measured over $N=5$ warmup/timed runs with wall-clock microsecond timers.

---

## 5. BENCHMARK RESULTS & PROVENANCE BREAKDOWN

The automated benchmark was executed on the host system:
- **Host Platform:** macOS-26.5.2-arm64 (Apple Silicon)
- **Python Version:** 3.14.2 Standard CPython
- **Test Dataset:** Deterministic Urban Scene (12,000 LiDAR points: road, sidewalk, parked vehicle, pedestrian, pole)
- **Warmup & Timing:** 1 warmup run + 5 timed iterations measured via `time.perf_counter()`
- **Output Artifact:** [`outputs/benchmark_results.json`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/outputs/benchmark_results.json)

### Comparative Benchmark Summary

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
  "provenance": {
    "processing_time_uniform_ms": "MEASURED",
    "processing_time_foveated_ms": "MEASURED",
    "speedup_factor": "MEASURED",
    "uniform_cell_count": "MEASURED",
    "foveated_cell_count": "MEASURED",
    "cell_reduction_ratio": "CALCULATED",
    "memory_reduction_pct": "CALCULATED",
    "distance_bins": "MEASURED"
  },
  "uniform_vs_foveated": {
    "uniform_cell_count": 9059,
    "foveated_cell_count": 6542,
    "cell_reduction_ratio": 1.38,
    "memory_uniform_mb": 0.55,
    "memory_foveated_mb": 0.40,
    "memory_reduction_pct": 27.8,
    "processing_time_uniform_ms": 54.62,
    "processing_time_foveated_ms": 58.56,
    "speedup_factor": 0.93
  },
  "distance_bins": [
    { "bin": "0-10m (Ring 0 / Near)", "resolution": "5 cm", "miou": 95.2, "elevation_rmse_cm": 1.1, "cell_density_pct": 26.4 },
    { "bin": "10-25m (Ring 1 / Mid-Near)", "resolution": "10 cm", "miou": 91.8, "elevation_rmse_cm": 2.5, "cell_density_pct": 40.6 },
    { "bin": "25-50m (Ring 2 / Mid)", "resolution": "25 cm", "miou": 85.0, "elevation_rmse_cm": 5.2, "cell_density_pct": 32.9 },
    { "bin": "50-100m (Ring 3 / Far)", "resolution": "50 cm", "miou": 77.4, "elevation_rmse_cm": 10.8, "cell_density_pct": 0.1 }
  ]
}
```

---

## 6. TELEMETRY & TIMING INSTRUMENTATION SPECIFICATION

Implemented in [`src/integration/telemetry.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/integration/telemetry.py):

1. **Per-Stage Latencies:**
   - Captured via `self.start_stage(name)` and `self.stop_stage(name)` using `time.perf_counter()`.
   - Recorded for: `preprocessing`, `inference`, `grid_indexing`, `mapping`, `hazard_analysis`, `total`.
   - Stored in sliding window `collections.deque(maxlen=100)`.
2. **Throughput & FPS:**
   - Real inter-frame interval $\Delta t = t_{\text{current}} - t_{\text{previous}}$.
   - $\text{FPS} = \frac{1}{\text{mean}(\Delta t)}$.
3. **RAM Memory Measurement:**
   - Measures actual process Resident Set Size (RSS) via `psutil.Process().memory_info().rss` (or `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`).
   - Units: Megabytes ($\text{MB}$).

---

## 7. SERVER REST API ENDPOINT SPECIFICATION

Implemented in [`src/visualization/server.py`](file:///Users/atharvahoge/Downloads/ATHARVA/HACKATHONS/SIH%20LiDAR%20UI/src/visualization/server.py):

| Endpoint | Method | Response Payload Description | Data Provenance / Origin |
| :--- | :---: | :--- | :--- |
| **`/api/status`** | `GET` | `{"status": "online", "mode": "SYNTHETIC", "frame_count": 42}` | Live server state (`PipelineOrchestrator`) |
| **`/api/architecture`** | `GET` | 7-stage architectural metadata, owners, resolutions, inputs/outputs | System architecture specification |
| **`/api/frame`** | `GET` | Subsampled 3D points, semantic classes, multi-ring cells, hazards, live telemetry HUD | Live pipeline frame execution (`process_frame()`) |
| **`/api/benchmark`** | `GET` | Comparative benchmark results (Uniform vs. Foveated), distance bins, hardware metadata | Empirical runner (`BenchmarkRunner.run_comparative_benchmark()`) |
| **`/api/cell_inspect`** | `GET` | `x, y` query $\to$ Ring ID, cell center, resolution, elevation bounds, roughness, traversability | Spatial indexer (`grid_indexer.world_to_cell()`) |
| **`/api/control`** | `POST` | `{"action": "play"|"pause"|"step"|"reset"|"set_scene", "scene_type": "urban"}` | Sequence playback engine (`SequencePlayer`) |

---

## 8. FRONTEND VALUE & TRUTHFULNESS AUDIT

| Visual Element / Component | Displayed Metric / Feature | Classification | Provenance & Source |
| :--- | :--- | :---: | :--- |
| **Live Point Cloud (Viewport)** | Subsampled points $(X, Y, Z)$ colored by semantic class / elevation | **REAL** | Extracted from `input_frame.points` streamed via `/api/frame`. |
| **Foveated Ring Overlays** | 4 concentric resolution rings ($5\text{cm}, 10\text{cm}, 25\text{cm}, 50\text{cm}$) | **REAL** | Extracted from `semantic_map.cells` streamed via `/api/frame`. |
| **Pothole Hazard Light Beams** | Vertical volumetric glowing beams & depth tags ($-14\text{cm}$) | **REAL** | Generated from detected pothole coordinates in `detect_map_hazards()`. |
| **Speed Breakers** | Parabolic humps ($+8\text{cm}$) with hazard chevron striping | **REAL** | Geometric profile from synthetic/sensor elevation map. |
| **3D Analytical Terrain Surface** | Deformed continuous 3D topographic mesh | **REAL** | Interpolated dynamically from foveated cell elevations ($Z_{\min}, Z_{\max}, Z_{\text{mean}}$). |
| **DRDO Cell Inspector** | $Z_{\min}, Z_{\max}, \Delta Z, \sigma_z$ (roughness), confidence, traversability | **REAL** | Computed live via `/api/cell_inspect?x=..&y=..` on active grid cell. |
| **Live Telemetry HUD** | FPS, CPU Latencies per stage (ms), RAM RSS (MB) | **REAL** | Measured live on host CPU via `TelemetryProfiler`. |
| **Benchmark Modal (Hero Cards)** | Memory reduction %, Speedup factor, Cell compression ratio | **CALCULATED** | Computed by `BenchmarkRunner.run_comparative_benchmark()`. |
| **Benchmark Modal (Distance Table)** | Ring-stratified mIoU % and elevation RMSE (cm) | **MEASURED** | Computed from ground truth points across distance intervals. |
| **Canonical Research UGV** | Single unified aerodynamic PBR vehicle with rotating optical LiDAR | **REAL ASSET** | Custom PBR geometry loaded across all 7 viewport modes. |

---

## 9. PRIMARY DEMO PROCEDURE

The canonical presentation flow for judges:

1. **Start the Autonomous Perception Control Center:**
   ```bash
   python3 -m src.visualization.server --port 8080
   ```
2. **Open Browser Console:**
   Navigate to `http://127.0.0.1:8080/` in any modern web browser.
3. **Step Through Perception Modes:**
   - **RAW LIDAR:** Observe raw 3D laser reflections.
   - **SEMANTIC:** Observe 8-class color-coded point cloud segmentation.
   - **FOVEATED GRID:** Observe 4 concentric variable-resolution rings ($5\text{cm} \to 50\text{cm}$).
   - **2.5D ELEVATION:** Observe height-aware elevation grid surface.
   - **TRAVERSABILITY & HAZARDS:** Observe detected road curbs, potholes (with volumetric depth light beams), and speed breakers.
   - **3D ANALYTICAL SURFACE:** Click any terrain anomaly to inspect depth, roughness ($\sigma_z$), and traversability rating in the DRDO inspector reticle.
4. **Inspect Live Telemetry:**
   Review real-time FPS, RAM RSS memory, and per-stage latency breakdown in the HUD.
5. **Open Benchmark Modal:**
   Click **"BENCHMARK"** in the top navigation bar to display the empirical head-to-head evaluation (Uniform 5cm vs. SYNTRIX Foveated) complete with distance-binned mIoUs and host hardware specifications.

---

## 10. BACKUP DEMO ARCHITECTURE

If the backend Python server cannot be started on the evaluation computer:
1. Navigate to `frontend/` directory.
2. Run `npm run dev` (or open pre-compiled `dist/index.html`).
3. The frontend's built-in client simulation engine automatically engages in offline fallback mode:
   - Full deterministic geometric terrain synthesis (Urban, Curb, Pothole, Overhang, Slope).
   - Dynamic vehicle teleoperation and hazard detection.
   - Full 3D canonical vehicle rendering and volumetric hazard beams.
   - Zero external cloud or server dependencies required.

---

## 11. TESTS & VERIFICATION RESULTS

### Test Commands & Exact Outputs

#### 1. Full Test Suite (109 Tests)
```bash
pytest tests/ -v
# Output: ============================= 109 passed in 3.09s ==============================
```

#### 2. Integration & Evaluation Suite (12 Tests)
```bash
pytest tests/integration/ tests/evaluation/ -v
# Output: ============================== 12 passed in 2.50s ==============================
```

#### 3. Frontend Production Build
```bash
npm run --prefix frontend build
# Output:
# ✓ 2223 modules transformed.
# ✓ built in 1.81s (Exit Code: 0)
```

#### 4. Automated Benchmark Execution
```bash
python3 -c "from src.evaluation.benchmark import BenchmarkRunner; BenchmarkRunner.run_comparative_benchmark(scene_type='urban', num_runs=5, save_to_file=True)"
# Output: outputs/benchmark_results.json generated (Exit Code: 0)
```

---

## 12. KNOWN RISKS & OPERATIONAL CONSIDERATIONS

1. **Port Availability:** The default server binds to port `8080`. If occupied, pass `--port <PORT>` (e.g. `python3 -m src.visualization.server --port 8888`).
2. **WebGL Hardware Acceleration:** The 3D Three.js viewport requires a WebGL-compatible browser (Google Chrome, Mozilla Firefox, Safari, Microsoft Edge) with hardware acceleration enabled.
3. **Cartesian Sensing Bounds:** Spatial indexing covers up to $100\text{m}$ radial distance. Preprocessor filters sanitize points outside this range.
4. **Synchronized Playback:** When stepping frames via REST API, the browser updates at $\sim 10\text{ FPS}$ to maintain smooth Three.js buffer garbage collection.

---

## 13. FINAL METRIC STATUS TABLE

| Metric Name | Numerical Value | Source / Methodology | Formally Classified Status |
| :--- | :---: | :--- | :---: |
| **End-to-End Latency** | `15.8 ms - 58.5 ms` | Wall-clock `time.perf_counter()` over 5 iterations | **MEASURED** |
| **Throughput (FPS)** | `17.1 - 63.3 FPS` | Computed directly from frame duration ($1000 / \Delta t$) | **MEASURED** |
| **Process RAM RSS** | `~68.2 MB` | OS Resident Set Size via `resource.getrusage()` | **MEASURED** |
| **Uniform 5cm Active Cells** | `9,059 cells` | Active cells aggregated from 12k-point urban scene | **MEASURED** |
| **SYNTRIX Foveated Cells** | `6,542 cells` | Multi-ring active cells aggregated from identical scene | **MEASURED** |
| **Active Cell Reduction Ratio** | `1.38 : 1` | Derived from measured active cell ratio ($\frac{9059}{6542}$) | **CALCULATED** |
| **Theoretical Grid Compression**| `95.4%` | Mathematical annulus area integration over $100\text{m}$ | **THEORETICAL** |
| **Near-Field Elevation RMSE** | `1.1 cm` | Point-to-plane root mean square error ($0\text{--}10\text{m}$) | **MEASURED** |
| **Near-Field Semantic mIoU** | `95.2%` | Class confusion matrix on ground truth points ($0\text{--}10\text{m}$) | **MEASURED** |
| **Pothole Detection Depth** | `-14.0 cm` | Localized parabolic elevation drop ($Z_{\text{road}} - Z_{\min}$) | **MEASURED** |
| **Speed Breaker Step Rise** | `+8.0 cm` | Localized parabolic elevation rise ($Z_{\max} - Z_{\text{road}}$) | **MEASURED** |
| **Target Operating FPS** | `10.0 - 30.0 FPS`| Autonomous vehicle closed-loop perception target | **TARGET** |

---

## 14. HANDOFF SIGN-OFF

- **Ready for Release Merge:** **YES**
- **Git Commit Hash:** `5f15336d39fa086588d08595874c7ca2ce401a0a`
- **Branch:** `feature/atharva-integration`
