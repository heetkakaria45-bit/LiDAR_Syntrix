# System Architecture & Technical Blueprint

> **Project:** Foveated Semantic 2.5D LiDAR Mapping for Autonomous Navigation  
> **Event:** Smart India Hackathon (SIH 2026)  
> **Status:** Architecture Freeze (Phase 2)  
> **Applicability:** Mandatory technical standard across all six developer modules.

---

## 1. Executive Summary & Core Innovation

Autonomous mobile robots and self-driving vehicles require dense, millimeter-to-centimeter precision in their immediate stopping distance to negotiate low-profile obstacles, curbs, potholes, and road debris. However, extending that same uniform millimeter-level resolution across a $100\text{ m}$ radius creates an intractable computational bottleneck:
- **Uniform 3D Voxel Grids:** Memory scales cubically ($\mathcal{O}(R^3)$); point cloud segmentation and dense volumetric fusion over saturate GPU memory and bus bandwidth.
- **Traditional 2D Occupancy Grids:** Collapse all vertical geometry into binary occupied/free cells, forfeiting curb heights, potholes, surface slopes, and multi-layer overhangs (e.g. overhanging branches, underpasses).

### The Innovation
Our system introduces a **Distance-Aware, Semantic-Aware, and Uncertainty-Aware 2.5D Elevation Map**. The foundational spatial structure allocates high spatial resolution in the immediate vehicle near-field where emergency maneuvers occur, while progressively coarsening representation density outward to the $100\text{ m}$ horizon. 

Furthermore, the architecture provides a decoupled, hook-based **Adaptive Refinement Model**:
$$\text{Resolution}(\mathbf{x}) = f\Big(\text{Distance}(\mathbf{x}), \;\text{SemanticPriority}(\mathbf{x}), \;\text{Uncertainty}(\mathbf{x})\Big)$$
This ensures that safety-critical targets detected at long ranges (such as a pedestrian at $70\text{ m}$) trigger localized cell refinement without inflating memory consumption across the entire spatial ring.

---

## 2. End-to-End System Pipeline

The pipeline consists of 10 sequential and asynchronous stages:

```
                  ┌─────────────────────────────────────┐
                  │          RAW LIDAR INPUT            │
                  │  (PCD / BIN / ROS2 sensor_msgs)     │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 1. INGESTION & PREPROCESSING        │
                  │ Outlier removal • Coordinate frame  │
                  │ [src/preprocessing/ — Amulya]       │
                  └──────────────────┬──────────────────┘
                                     │  PointCloudFrame (Nx3, intensity, pose)
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 2. SEMANTIC PERCEPTION              │
                  │ Modular 3D Deep Learning Inference  │
                  │ [src/perception/ — Vedant]          │
                  └──────────────────┬──────────────────┘
                                     │  SemanticPointCloud (Nx3, class, conf)
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 3. FOVEATED SPATIAL INDEXING        │
                  │ Multi-Ring Point-to-Cell Hashing    │
                  │ [src/foveated_grid/ — Manashri]     │
                  └──────────────────┬──────────────────┘
                                     │  Multi-Resolution Cell Index
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 4. 2.5D SEMANTIC ELEVATION MAPPING  │
                  │ Elevation aggregation • Occupancy   │
                  │ [src/mapping/ — Heet]               │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 5. TERRAIN & HAZARD ANALYSIS        │
                  │ Curbs • Potholes • Slopes • Overhang│
                  │ [src/mapping/ — Heet]               │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 6. TEMPORAL MAP UPDATE & TRACKING   │
                  │ Recursive Bayesian filtering        │
                  │ [src/mapping/ — Heet]               │
                  └──────────────────┬──────────────────┘
                                     │  SemanticMap (Foveated composite)
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 7. REAL-TIME ORCHESTRATION          │
                  │ Multithreaded pipeline & telemetry  │
                  │ [src/integration/ — Atharva]        │
                  └──────────┬──────────────────────┬───┘
                             │                      │
                             ▼                      ▼
┌──────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
│ 8. AUTONOMOUS PERCEPTION CONTROL CENTER  │ │ 9. QUANTITATIVE BENCHMARKING ENGINE      │
│ Interactive 2.5D/3D visualizer & UI      │ │ Uniform vs. Foveated comparative eval    │
│ [src/visualization/ — Atharva]           │ │ [src/evaluation/ — Himisha]             │
└──────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 3. Detailed Stage Responsibilities & Interfaces

### Stage 1: LiDAR Preprocessing (`src/preprocessing/` — Amulya)
- **Inputs:** Raw binary point clouds (`.bin`), point cloud files (`.pcd`), or live ROS 2 `sensor_msgs/PointCloud2`.
- **Responsibilities:**
  - Ingestion and range clipping ($0.5\text{ m} \le r \le 100.0\text{ m}$).
  - Statistical and radius outlier filtering to remove atmospheric dust and sensor noise.
  - Coordinate transformation into the standard ego-vehicle frame:
    $$\mathbf{p}_{\text{base}} = \mathbf{T}_{\text{sensor}}^{\text{base}} \, \mathbf{p}_{\text{sensor}}$$
  - Generation of verified `PointCloudFrame` instances.
- **Invariants:** Output point arrays must be free of `NaN` and `Inf` values; coordinates must be $(N, 3)$ `float32`.

### Stage 2: Semantic Point Cloud Perception (`src/perception/` — Vedant)
- **Inputs:** `PointCloudFrame`.
- **Responsibilities:**
  - Model-agnostic semantic inference allocating class probabilities across the 8 project taxonomy classes.
  - Compute normalized per-point confidence scores $c_i \in [0.0, 1.0]$.
  - Generation of vectorized `SemanticPointCloud`.
- **Decoupled Architecture:** The perception module exposes an abstract interface `BaseSemanticSegmenter`. Swap implementations (e.g. RangeNet++, Cylinder3D, Sparse Conv, PointNet++) without modifying the mapping engine.

### Stage 3: Foveated Spatial Representation (`src/foveated_grid/` — Manashri)
- **Inputs:** `SemanticPointCloud` and sensor origin.
- **Responsibilities:**
  - Spatial partitioning across concentric distance rings:
    - **Level 0 (Near):** $0\text{--}10\text{ m}$ @ $\Delta x = \Delta y = 0.05\text{ m}$ ($5\text{ cm}$)
    - **Level 1 (Mid-Near):** $10\text{--}25\text{ m}$ @ $\Delta x = \Delta y = 0.10\text{ m}$ ($10\text{ cm}$)
    - **Level 2 (Mid):** $25\text{--}50\text{ m}$ @ $\Delta x = \Delta y = 0.25\text{ m}$ ($25\text{ cm}$)
    - **Level 3 (Far):** $50\text{--}100\text{ m}$ @ $\Delta x = \Delta y = 0.50\text{ m}$ ($50\text{ cm}$)
  - Deterministic world-to-cell and cell-to-world index transformations:
    $$i = \left\lfloor \frac{x - x_{\min}^{(l)}}{\Delta^{(l)}} \right\rfloor, \quad j = \left\lfloor \frac{y - y_{\min}^{(l)}}{\Delta^{(l)}} \right\rfloor$$
  - Exact handling of boundary points on half-open ring intervals $[r_k, r_{k+1})$.
  - Memory-efficient sparse spatial indexing (sparse hash tables or packed Morton keys).

### Stage 4: 2.5D Semantic Mapping (`src/mapping/` — Heet)
- **Inputs:** Multi-resolution spatial point-to-cell bins from Manashri's grid.
- **Responsibilities:**
  - Cell elevation aggregation: surface height $z_{\text{nominal}}$ (robust median or lowest-point filter), $z_{\min}$, and $z_{\max}$.
  - Semantic label fusion: Bayesian log-odds update or confidence-weighted majority voting over point observations falling in each cell.
  - Cell occupancy estimation and point count tracking.
  - Generation of `GridCell` entities.

### Stage 5: Terrain & Hazard Analysis (`src/mapping/` — Heet)
- **Inputs:** Populated 2.5D elevation grid cells.
- **Responsibilities:**
  - **Local Surface Slope:** Evaluated via finite difference gradient over neighboring cells:
    $$\theta = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$
  - **Surface Roughness:** Elevation variance $\sigma_z^2$ of points within the cell.
  - **Deterministic Curb Detection:** Identifies sharp step discontinuities ($8\text{ cm} \le \Delta z \le 25\text{ cm}$) between adjacent drivable and non-drivable cells.
  - **Pothole Detection:** Identifies localized depressions below the fitted local road plane ($\Delta z \le -5\text{ cm}$).
  - **Overhang Representation:** Evaluates vertical clearance between ground surface $z_{\text{ground}}$ and elevated point clusters $z_{\max}$. Cells with clearance $> 2.2\text{ m}$ are flagged as traversable overhangs.

### Stage 6: Temporal Map Update (`src/mapping/` & `src/integration/` — Heet & Atharva)
- **Inputs:** Consecutive `SemanticMap` snapshots across timestamps $t_k, t_{k+1}$.
- **Responsibilities:**
  - Ego-motion compensation using 6-DoF transformation matrix $\mathbf{T}_{k+1}^k$.
  - Temporal recursive filtering for stationary cells:
    $$L_{k+1}(m_i) = L_k(m_i) + \log\frac{P(m_i \mid z_{k+1})}{1 - P(m_i \mid z_{k+1})}$$
  - Observation count incrementing and transient noise eviction.
  - Tracking dynamic object cells (pedestrians, vehicles) using cell velocity vectors $\mathbf{v} = (v_x, v_y)$.

### Stage 7: Real-Time Integration & Orchestration (`src/integration/` — Atharva)
- **Inputs:** All pipeline modules.
- **Responsibilities:**
  - Multithreaded execution pipeline decoupling sensor acquisition from ML inference and spatial mapping.
  - Memory footprint management, zero-copy buffer sharing via shared NumPy arrays.
  - Real-time performance profiling: recording per-stage latency, end-to-end FPS, CPU/GPU utilization, and memory telemetry.

### Stage 8: Autonomous Perception Control Center (`src/visualization/` — Atharva)
- **Inputs:** `SemanticMap`, `PointCloudFrame`, and telemetry streams.
- **Responsibilities:**
  - Render 12 real-time views including top-down 2.5D elevation, traversability hazards, semantic foveation bands, and side-by-side uniform-vs-foveated comparisons.
  - Interactive cell inspector revealing raw elevation, class distributions, and confidence.

### Stage 9: Quantitative Benchmarking (`src/evaluation/` — Himisha)
- **Inputs:** Ground truth labels, `SemanticMap`, and runtime telemetry.
- **Responsibilities:**
  - Evaluate semantic segmentation metrics: mIoU, precision, recall, and class-specific F1.
  - Evaluate geometric elevation accuracy: RMSE between estimated cell elevation and ground truth surface.
  - Distance-stratified benchmarking: Breakdown of accuracy across the 4 distance zones ($0\text{--}10\text{ m}, 10\text{--}25\text{ m}, 25\text{--}50\text{ m}, 50\text{--}100\text{ m}$).
  - Comparative analysis proving memory savings and FPS acceleration of foveated mapping versus uniform $5\text{ cm}$ grids.

---

## 4. Frozen Coordinate Conventions

```
                    +Z (Up)
                     │
                     │
                     │
                     └───────► +X (Forward / Heading)
                    ╱
                   ╱
                  ▼
              +Y (Left)
```

- **Reference Frame:** Standard right-handed Cartesian coordinate system.
- **Axes:**
  - **$+X$:** Forward pointing along vehicle longitudinal axis.
  - **$+Y$:** Left pointing along vehicle lateral axis.
  - **$+Z$:** Up pointing along vehicle vertical axis.
- **Units:**
  - Coordinates & dimensions: **meters (m)**
  - Angles & rotations: **radians (rad)**
  - Linear velocity: **meters per second ($\text{m/s}$)**
  - Timestamps: **seconds (float64, Unix epoch or synchronized ROS time)**

---

## 5. Foveated Spatial Indexing Architecture

### 5.1. Initial Distance Foveation Parameters
Configured in `configs/default_config.yaml`:

| Level | Ring Name | Range Span | Cell Resolution | Area Covered | Grid Dimension (if dense) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **0** | `near` | $0\text{--}10\text{ m}$ | $0.05\text{ m}$ ($5\text{ cm}$) | $314\text{ m}^2$ | $400 \times 400$ cells |
| **1** | `mid_near` | $10\text{--}25\text{ m}$ | $0.10\text{ m}$ ($10\text{ cm}$) | $1,649\text{ m}^2$ | $500 \times 500$ cells |
| **2** | `mid` | $25\text{--}50\text{ m}$ | $0.25\text{ m}$ ($25\text{ cm}$) | $5,890\text{ m}^2$ | $400 \times 400$ cells |
| **3** | `far` | $50\text{--}100\text{ m}$ | $0.50\text{ m}$ ($50\text{ cm}$) | $23,562\text{ m}^2$ | $400 \times 400$ cells |

### 5.2. Data Structure Evaluation for Manashri
Manashri is tasked with evaluating and benchmarking four candidate data structures in `src/foveated_grid/`:
1. **Concentric Cartesian Multi-Grid:** A stack of 4 independent 2D dense arrays with coordinate offset math. Ultra-fast $\mathcal{O}(1)$ random access, but allocates memory in the inner rings for outer layers.
2. **Concentric Polar / Cylindrical Rings:** Cells indexed by $(r_k, \theta_j)$. High geometric alignment with LiDAR beam distribution, but cell width expands radially ($\Delta w = r \Delta \theta$).
3. **Hierarchical Quadtree:** Dynamically subdivides cells based on depth criteria. Elegant variable resolution, but incurs pointer-chasing latency and cache misses.
4. **Packed 64-Bit Morton / Hash Grid:** Combines ring level and Cartesian indices into a 64-bit integer key $(L \ll 48) \mid (i \ll 24) \mid j$ stored in a sparse flat hash map. Highly memory-efficient with $\mathcal{O}(1)$ average insertion.

---

## 6. Adaptive Semantic & Uncertainty Refinement

While the baseline system uses distance-based concentric rings, the architecture is forward-compatible with dynamic multi-factor refinement:

$$\Delta_{\text{target}}(\mathbf{x}) = \Delta_{\text{base}}(d(\mathbf{x})) \times \left(1 - w_{\text{sem}} \cdot I_{\text{class}}(\mathbf{x})\right) \times \left(1 - w_{\text{unc}} \cdot U(\mathbf{x})\right)$$

- **Distance Term $d(\mathbf{x})$:** Governs default baseline ring resolution.
- **Semantic Priority $I_{\text{class}} \in [0.0, 1.0]$:** Assigned per class. Vulnerable Road Users (pedestrians, cyclists) have high priority ($1.0$), forcing cell resolution to refine locally.
- **Uncertainty Term $U(\mathbf{x}) \in [0.0, 1.0]$:** High prediction entropy or high elevation variance triggers localized subdivision.
- **Concrete Example:** A pedestrian detected at $70\text{ m}$ (normally in the $50\text{ cm}$ far ring) triggers localized sub-cells at $10\text{ cm}$ within their bounding radius, enabling accurate obstacle localization without refining the surrounding $23,000\text{ m}^2$ ground plane.

---

## 7. Development Dependency Graph & Mocking Strategy

To guarantee that all six engineers can develop in parallel without blocking:

```
[Synthetic Scene Generator] ───► PointCloudFrame (Mock)
             │
             ├──► Preprocessing (Amulya) ──► PointCloudFrame (Real)
             │                                     │
             │                                     ▼
             ├──► Perception (Vedant)     ──► SemanticPointCloud (Real)
             │                                     │
             │                                     ▼
             ├──► Foveated Grid (Manashri)──► Multi-Ring Cell Index
             │                                     │
             │                                     ▼
             ├──► Mapping (Heet)          ──► SemanticMap & Hazards
             │                                     │
             │                                     ▼
             ├──► Integration (Atharva)   ──► Orchestrated Pipeline & Telemetry
             │                                     │
             │                                     ▼
             └──► Evaluation (Himisha)    ──► Benchmark Reports
```

### Module Mocks Available
- **Synthetic PointCloudFrame:** Available immediately via `src/preprocessing/synthetic.py` (generates curbs, ramps, potholes, pedestrians, vehicles).
- **Mock Semantic Segmenter:** Assigns ground truth classes to synthetic geometric primitives with configurable noise, allowing Heet (Mapping), Manashri (Grid), and Atharva (Integration) to develop without waiting for Vedant's neural network training.
- **Mock Elevation Surface:** Allows Atharva to build the UI and Himisha to write benchmark verification scripts before live sensor data is loaded.
