# System Architecture — Foveated Semantic 2.5D LiDAR Mapping

## 1. System Pipeline Overview

```text
+-----------------------------------------------------------------------------------+
| 1. RAW LIDAR SENSOR / DATASET STREAM                                              |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (Raw PointCloudFrame)
+-----------------------------------------------------------------------------------+
| 2. PREPROCESSING [Amulya - src/preprocessing/]                                    |
|    - NaN/Inf filtering, range cropping (-100m..+100m), ego-vehicle noise removal  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (Clean PointCloudFrame)
+-----------------------------------------------------------------------------------+
| 3. SEMANTIC PERCEPTION [Vedant - src/perception/]                                 |
|    - Deep/lightweight point segmentation model (Taxonomy classes 0..7)            |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (SemanticPointCloud)
+-----------------------------------------------------------------------------------+
| 4. FOVEATED SPATIAL REPRESENTATION [Manashri - src/foveated_grid/]                |
|    - Multi-resolution spatial partitioning (0.05m, 0.10m, 0.25m, 0.50m)           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (Foveated Point Partitions / Indexing)
+-----------------------------------------------------------------------------------+
| 5. SEMANTIC 2.5D MAP [Heet - src/mapping/]                                        |
|    - Elevation statistics (min_z, max_z, mean_z), roughness, semantic consensus  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (Active SemanticMap)
+-----------------------------------------------------------------------------------+
| 6. TERRAIN / TRAVERSABILITY ANALYSIS [Heet - src/mapping/]                        |
|    - Slope, step height, roughness, traversability cost scoring                   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (Traversability-Annotated SemanticMap)
+-----------------------------------------------------------------------------------+
| 7. TEMPORAL MAP UPDATE [Heet - src/mapping/]                                      |
|    - Multi-frame fusion, observation count decay, persistent confidence           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (Updated SemanticMap)
+-----------------------------------------------------------------------------------+
| 8. REAL-TIME INTEGRATION [Atharva - src/integration/]                             |
|    - Pipeline orchestration, frame synchronization, telemetry collection          |
+-----------------------------------------------------------------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
+----------------------------------------+ +----------------------------------------+
| 9. VISUALIZATION [Atharva]             | | 10. BENCHMARKING [Himisha]             |
|    - Autonomous Perception UI          | |     - Latency, FPS, RAM/VRAM profiler  |
|    - 12 viewing modes + telemetry      | |     - Uniform vs Foveated validation   |
+----------------------------------------+ +----------------------------------------+
```

---

## 2. Comprehensive Stage Specifications

### Stage 1: Raw LiDAR Ingestion
* **Responsibility:** Ingest streaming LiDAR frames from live sensors (Ouster/Velodyne) or standard datasets (SemanticKITTI, nuScenes, Waymo).
* **Input:** Sensor binary packet or dataset files.
* **Output:** `PointCloudFrame` ($N \times 3$ coordinates, intensity, timestamp, frame ID, pose).
* **Dependencies:** None.
* **Ownership:** Shared / `IDatasetAdapter`.
* **Mockability:** High (`MockDatasetAdapter` produces synthetic frames deterministically).

### Stage 2: Preprocessing
* **Responsibility:** Clean point cloud, reject NaN/Inf readings, filter out ego-vehicle body returns, apply 3D bounding box filter ($[-100, 100]\,m$ in $X/Y$, $[-5, 10]\,m$ in $Z$), perform optional voxel downsampling.
* **Input:** Raw `PointCloudFrame`.
* **Output:** Clean `PointCloudFrame`.
* **Dependencies:** Central configuration (`config/config.yaml`).
* **Ownership:** **Amulya** (`src/preprocessing/`).
* **Mockability:** High (`MockPreprocessor` performs identity pass-through or basic range crops).

### Stage 3: Semantic Perception
* **Responsibility:** Classify each 3D point into one of the 8 frozen semantic classes (`DRIVABLE_GROUND`, `NON_DRIVABLE_TERRAIN`, `VEHICLE`, `PEDESTRIAN`, `CYCLIST`, `POLE`, `WALL_BUILDING`, `OTHER_OBSTACLE`) with confidence $[0.0, 1.0]$.
* **Input:** Clean `PointCloudFrame`.
* **Output:** `SemanticPointCloud` ($N \times 3$ points, $N$ labels, $N$ confidences).
* **Dependencies:** Deep learning runtime (PyTorch / ONNX Runtime / CUDA / CPU fallback).
* **Ownership:** **Vedant** (`src/perception/`).
* **Mockability:** High (`MockSemanticPerception` assigns default class labels and confidences to allow immediate downstream development).

### Stage 4: Foveated Spatial Representation
* **Responsibility:** Map continuous $(X, Y)$ coordinates into discrete multi-resolution foveation zones (Level 0: 0–10m @ 0.05m; Level 1: 10–25m @ 0.10m; Level 2: 25–50m @ 0.25m; Level 3: 50–100m @ 0.50m); handle boundary continuity, negative coordinate math, spatial hashing/indexing.
* **Input:** `SemanticPointCloud`.
* **Output:** Indexed multi-resolution point partitions / spatial key mappings.
* **Dependencies:** Central foveation configuration.
* **Ownership:** **Manashri** (`src/foveated_grid/`).
* **Mockability:** High (`MockFoveatedGrid` evaluates mathematical boundary formulas).

### Stage 5: Semantic 2.5D Map
* **Responsibility:** Aggregate points within discrete $(level, i_x, i_y)$ grid cells; compute ground elevation ($mean\_z$), height bounds ($min\_z, max\_z$), local roughness (variance of $z$), occupancy state, and dominant semantic class via voting or confidence accumulation.
* **Input:** Indexed `SemanticPointCloud` + Foveated Grid mapping.
* **Output:** `SemanticMap` containing updated `GridCell` dictionary.
* **Dependencies:** `src/common/types.py`, `src/foveated_grid/`.
* **Ownership:** **Heet** (`src/mapping/`).
* **Mockability:** High (`MockSemantic25DMapper` maintains a structured `SemanticMap`).

### Stage 6: Terrain & Traversability Analysis
* **Responsibility:** Compute step height discontinuities ($max\_z - min\_z$), local slope gradients between adjacent cells, surface roughness, and combine with semantic penalties to classify cell traversability and navigation costs.
* **Input:** `SemanticMap`.
* **Output:** Traversability-annotated `SemanticMap` / `Dict[CellKey, TraversabilityScore]`.
* **Dependencies:** `src/common/types.py`.
* **Ownership:** **Heet** (`src/mapping/`).
* **Mockability:** High (`MockTraversabilityAnalyzer` checks simple roughness and ground flags).

### Stage 7: Temporal Map Update
* **Responsibility:** Integrate sequential frames over time using ego-motion transforms (`sensor_pose`); update observation counts, apply confidence decay to unobserved cells, filter transient noise, and maintain persistent map state.
* **Input:** Historical `SemanticMap` + incoming `SemanticPointCloud`.
* **Output:** Temporally integrated `SemanticMap`.
* **Dependencies:** Sensor pose transformation math.
* **Ownership:** **Heet** (`src/mapping/`).
* **Mockability:** High (`MockTemporalMapUpdater` updates timestamps and aggregates frame history).

### Stage 8: Real-Time Pipeline Integration
* **Responsibility:** Orchestrate the end-to-end execution flow, handle streaming iterator pipelines, synchronize timestamps, and collect accurate wall-clock latency telemetry across every stage.
* **Input:** Streaming raw point clouds or dataset sequences.
* **Output:** `(SemanticMap, TelemetryMetrics)` per frame.
* **Dependencies:** Interfaces of all upstream stages.
* **Ownership:** **Atharva** (`src/integration/`).
* **Mockability:** High (`MockPipelineIntegrator` coordinates mock components).

### Stage 9: Perception Control Center Visualization
* **Responsibility:** Interactive multi-panel GUI providing 12 specialized inspection modes (Live LiDAR, Semantic segmentation, Elevation gradient, Traversability heatmap, Foveation zones, Uniform vs. Foveated comparison, Real-time telemetry, Cell inspector, Confidence display, Resolution decisions, Object bounding boxes, Playback controls).
* **Input:** `SemanticMap` + `TelemetryMetrics`.
* **Output:** Rendered GUI frames / interactive window.
* **Dependencies:** UI framework (OpenCV / Matplotlib / PyQt / Modern Web).
* **Ownership:** **Atharva** (`src/visualization/`).
* **Mockability:** High (`MockVisualizer` records calls without popping UI windows during test runs).

### Stage 10: Benchmarking & Validation
* **Responsibility:** Automated benchmark suite measuring component latencies, system throughput (FPS), RAM/VRAM memory footprint, point-to-cell compression efficiency, and side-by-side Uniform High-Resolution ($0.05\,m$) vs. Foveated Grid performance. Zero fabrication policy.
* **Input:** Benchmark datasets, synthetic geometric scenarios, integrated pipeline.
* **Output:** Quantitative evaluation reports, JSON benchmark artifacts, reproducible comparison charts.
* **Dependencies:** Python profiling tools, NumPy.
* **Ownership:** **Himisha** (`src/evaluation/`).
* **Mockability:** High (`MockBenchmarkEngine` provides standard report templates).
