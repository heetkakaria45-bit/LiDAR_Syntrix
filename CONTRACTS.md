# System Interface Contracts & Data Specifications

> **Status:** Initial Proposed Standard (v0.1.0)  
> **Applicability:** Mandatory across all six pipeline modules.  
> **Rule:** Any breaking modifications to these contracts require consensus and approval per the RFC process in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 1. Global Conventions

All modules must strictly adhere to the following physical and coordinate conventions:

- **Coordinate System:** Right-handed Cartesian
  - **+X:** Forward (vehicle heading)
  - **+Y:** Left
  - **+Z:** Up
- **Units:**
  - Spatial distances: **meters (m)**
  - Angles: **radians (rad)**
  - Timestamps: **seconds (float64, Unix epoch or synchronized ROS time)**
  - Probabilities & Confidences: **normalized float [0.0, 1.0]**

---

## 2. Core Contract Definitions

### 2.1. `PointCloudFrame`

Ingested raw or preprocessed point cloud frame produced by `src/preprocessing/` (Owner: Amulya) and consumed by `src/perception/` (Owner: Vedant).

| Field | Type | Description | Mandatory? |
| :--- | :--- | :--- | :--- |
| `points` | `np.ndarray (N, 3), float32` | 3D coordinates $(x, y, z)$ in sensor/vehicle frame | Yes |
| `intensity` | `np.ndarray (N,), float32` | Calibrated LiDAR reflection intensity | Optional |
| `timestamp` | `float64` | Scan capture timestamp in seconds | Yes |
| `frame_id` | `str` | Sensor reference frame (e.g. `"lidar_top"`, `"base_link"`) | Yes |
| `sensor_pose` | `np.ndarray (4, 4), float64` | Transformation matrix $[R \mid t]$ relating sensor to odometry/world frame | Optional (default: $I_{4\times4}$) |

**Invariants:**
- `points` must be finite (no `NaN` or `Inf` values; Amulya's preprocessing module is responsible for sanitization).
- If `intensity` is provided, `len(intensity) == len(points)`.

---

### 2.2. `SemanticPointCloud`

Point cloud enriched with per-point semantic predictions and confidence scores, produced by `src/perception/` (Owner: Vedant) and consumed by `src/foveated_grid/` (Manashri) and `src/mapping/` (Heet).

| Field | Type | Description | Mandatory? |
| :--- | :--- | :--- | :--- |
| `points` | `np.ndarray (N, 3), float32` | 3D coordinates $(x, y, z)$ in vehicle/map frame | Yes |
| `semantic_class`| `np.ndarray (N,), int32/uint8`| Class ID corresponding to configured class taxonomy | Yes |
| `confidence` | `np.ndarray (N,), float32` | Softmax or model prediction confidence in range $[0.0, 1.0]$ | Yes |
| `intensity` | `np.ndarray (N,), float32` | Preserved intensity (if available) | Optional |
| `timestamp` | `float64` | Timestamp matching origin frame | Yes |
| `frame_id` | `str` | Reference frame identifier | Yes |

**Invariants:**
- `points.shape[0] == semantic_class.shape[0] == confidence.shape[0]`.
- All `semantic_class` entries must map to valid IDs defined in `configs/default_config.yaml`.

---

### 2.3. `GridCell`

Fundamental element of the multi-resolution 2.5D elevation grid, indexed and mapped by `src/foveated_grid/` (Manashri) and populated by `src/mapping/` (Heet).

| Field | Type | Description |
| :--- | :--- | :--- |
| `resolution_level` | `str` or `int` | Foveation ring identifier (e.g., `"near"`, `"mid_near"`, `"mid"`, `"far"`) |
| `cell_x` | `float32 / int32` | Center X coordinate (or discrete grid index) in map frame |
| `cell_y` | `float32 / int32` | Center Y coordinate (or discrete grid index) in map frame |
| `elevation` | `float32` | Primary estimated terrain elevation $Z$ (e.g. median/mean surface height) |
| `min_z` | `float32` | Lowest point elevation observed within cell bounds |
| `max_z` | `float32` | Highest point elevation observed within cell bounds |
| `semantic_class` | `int32 / uint8` | Aggregated semantic category (Bayesian filter or majority vote) |
| `confidence` | `float32` | Aggregated semantic confidence $[0.0, 1.0]$ |
| `occupancy` | `float32` | Occupancy probability $[0.0, 1.0]$ |
| `point_count` | `int32` | Total raw points accumulated within this cell |
| `roughness` | `float32` | Terrain roughness metric (surface variance or plane fit residue) |
| `timestamp` | `float64` | Timestamp of the most recent cell measurement update |

---

### 2.4. `SemanticMap`

Hierarchical composite multi-resolution 2.5D map data structure, produced by `src/mapping/` (Heet), used by `src/integration/` (Atharva) and `src/visualization/` (Atharva), and benchmarked by `src/evaluation/` (Himisha).

| Field | Type | Description |
| :--- | :--- | :--- |
| `cells` | Multi-resolution container | Sparse index, hierarchical quadtree, or concentric ring arrays of `GridCell`s |
| `resolution_levels`| `dict` | Configuration metadata for active rings (ranges, cell sizes) |
| `sensor_pose` | `np.ndarray (4, 4)` | Vehicle/sensor pose at current map generation epoch |
| `timestamp` | `float64` | Snapshot timestamp |
| `metadata` | `dict` | Optional diagnostics (point throughput, frame latency) |

---

## 3. Standard Semantic Class IDs

The default taxonomy is configured in [configs/default_config.yaml](configs/default_config.yaml).

| ID | Semantic Label | Description | Default Traversability |
| :---: | :--- | :--- | :---: |
| `0` | `drivable_ground` | Asphalt, flat road, smooth pavement | Traversable |
| `1` | `non_drivable_terrain` | Grass, mud, dense gravel, steep embankments | Non-traversable |
| `2` | `vehicle` | Cars, trucks, vans, buses | Obstacle |
| `3` | `pedestrian` | Walking persons, children | Dynamic Obstacle |
| `4` | `cyclist` | Bicycles, motorbikes, scooters | Dynamic Obstacle |
| `5` | `pole` | Lamp posts, traffic light poles, tree trunks | Structural Obstacle |
| `6` | `wall_building` | Building facades, sound barriers, retaining walls | Structural Obstacle |
| `7` | `other_obstacle` | Debris, construction barrels, unclassified hazards | Obstacle |

---

## 4. Contract Evolution & RFC Process

These contracts are deliberately designed as clean, minimal interfaces to avoid prematurely constraining low-level implementation details (e.g. CUDA memory buffers, sparse hash tables, or ring-buffer formats).

If an internal module requires schema adjustments:
1. **Never alter field names or units unilaterally.**
2. Propose an RFC (Request for Comments) in an issue / team discussion.
3. Update `CONTRACTS.md` and [src/contracts.py](src/contracts.py) with backward-compatibility in mind.
4. Notify affected module owners before merging changes.
