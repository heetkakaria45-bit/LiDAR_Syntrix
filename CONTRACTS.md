# System Interface Contracts & Data Specifications

> **Status:** Architecture Freeze Standard (v0.2.0)  
> **Applicability:** Mandatory across all six pipeline modules.  
> **Rule:** Any breaking modifications to these contracts require consensus and approval per the RFC process in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 1. Global Physical & Geometric Conventions

All modules must strictly adhere to the following physical and coordinate conventions:

- **Coordinate System:** Right-handed Cartesian
  - **+X:** Forward (vehicle heading)
  - **+Y:** Left
  - **+Z:** Up
- **Units:**
  - Spatial distances: **meters (m)**
  - Angles: **radians (rad)**
  - Linear velocity: **meters per second ($\text{m/s}$)**
  - Timestamps: **seconds (float64, Unix epoch or synchronized ROS time)**
  - Probabilities & Confidences: **normalized float [0.0, 1.0]**

---

## 2. Core Data Contracts

### 2.1. `PointCloudFrame`
Standardized ingested raw or filtered LiDAR frame.  
**Produced by:** `src/preprocessing/` (Owner: Amulya)  
**Consumed by:** `src/perception/` (Owner: Vedant)

| Field | Type | Description | Mandatory? |
| :--- | :--- | :--- | :--- |
| `points` | `np.ndarray (N, 3), float32` | 3D Cartesian coordinates $(x, y, z)$ in ego/sensor frame | Yes |
| `intensity` | `np.ndarray (N,), float32` | Calibrated LiDAR reflection intensity | Optional |
| `timestamp` | `float64` | Capture epoch in seconds | Yes |
| `frame_id` | `str` | Sensor reference frame (e.g., `"lidar_top"`, `"base_link"`) | Yes |
| `sensor_pose` | `np.ndarray (4, 4), float64` | Transformation matrix $[R \mid t]$ from sensor to world frame | Optional (default: $I_4$) |

---

### 2.2. `SemanticPointCloud`
Point cloud enriched with per-point semantic predictions and confidence scores.  
**Produced by:** `src/perception/` (Owner: Vedant)  
**Consumed by:** `src/foveated_grid/` (Manashri), `src/mapping/` (Heet)

| Field | Type | Description | Mandatory? |
| :--- | :--- | :--- | :--- |
| `points` | `np.ndarray (N, 3), float32` | 3D coordinates $(x, y, z)$ in vehicle/map frame | Yes |
| `semantic_class`| `np.ndarray (N,), int32/uint8`| Class ID corresponding to project taxonomy ($0\text{--}7$) | Yes |
| `confidence` | `np.ndarray (N,), float32` | Prediction confidence in range $[0.0, 1.0]$ | Yes |
| `intensity` | `np.ndarray (N,), float32` | Preserved reflection intensity (if available) | Optional |
| `timestamp` | `float64` | Timestamp matching origin frame | Yes |
| `frame_id` | `str` | Reference frame identifier | Yes |

---

### 2.3. `GridCell`
Fundamental element of the multi-resolution 2.5D elevation grid.  
**Indexed by:** `src/foveated_grid/` (Owner: Manashri)  
**Aggregated by:** `src/mapping/` (Owner: Heet)

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `resolution_level` | `str` or `int` | Foveation ring identifier (`"near"`, `"mid_near"`, `"mid"`, `"far"`) | Required |
| `cell_x` | `float32` | Center X coordinate in map frame (meters) | Required |
| `cell_y` | `float32` | Center Y coordinate in map frame (meters) | Required |
| `elevation` | `float32` | Primary estimated terrain surface elevation $Z$ | Required |
| `min_z` | `float32` | Lowest point elevation observed within cell bounds | Required |
| `max_z` | `float32` | Highest point elevation observed within cell bounds | Required |
| `semantic_class` | `int32` | Aggregated semantic category ID ($0\text{--}7$) | Required |
| `confidence` | `float32` | Aggregated semantic confidence $[0.0, 1.0]$ | Required |
| `occupancy` | `float32` | Occupancy probability $[0.0, 1.0]$ | Required |
| `point_count` | `int32` | Total raw points accumulated within this cell | Required |
| `roughness` | `float32` | Terrain roughness metric ($\sigma_z^2$ or plane fit residual) | Required |
| `timestamp` | `float64` | Timestamp of latest cell update | Required |
| **Extended Fields:** | | | |
| `velocity` | `Optional[Tuple[float, float, float]]` | Estimated cell linear velocity $(v_x, v_y, v_z)$ in $\text{m/s}$ | `None` |
| `observation_count` | `int` | Number of temporal frames observing this cell | `1` |
| `uncertainty` | `float` | Geometric or elevation variance metric | `0.0` |
| `semantic_probabilities` | `Optional[np.ndarray]` | Probability distribution vector over 8 classes | `None` |

---

### 2.4. `SemanticMap`
Hierarchical composite multi-resolution 2.5D map data structure.  
**Produced by:** `src/mapping/` (Owner: Heet)  
**Consumed by:** `src/integration/`, `src/visualization/`, `src/evaluation/`

| Field | Type | Description |
| :--- | :--- | :--- |
| `cells` | Multi-resolution container | Container of `GridCell` instances (indexed by ring or packed key) |
| `resolution_levels`| `dict` | Active resolution definitions (ranges, cell dimensions) |
| `sensor_pose` | `np.ndarray (4, 4)` | Vehicle/sensor pose at current map generation epoch |
| `timestamp` | `float64` | Snapshot timestamp |
| `metadata` | `dict` | Diagnostic metrics (cell count, throughput, hazards detected) |

---

## 3. Standard Semantic Taxonomy & Dataset Label Mapping

The project targets eight standard semantic classes:

| ID | Project Class Name | Description | Traversability |
| :---: | :--- | :--- | :---: |
| `0` | `DRIVABLE_GROUND` | Asphalt, flat road, smooth pavement | Traversable |
| `1` | `NON_DRIVABLE_TERRAIN`| Grass, mud, dense gravel, steep embankments | Non-traversable |
| `2` | `VEHICLE` | Cars, trucks, vans, buses | Obstacle |
| `3` | `PEDESTRIAN` | Walking persons, children | Dynamic Obstacle |
| `4` | `CYCLIST` | Bicycles, motorbikes, scooters | Dynamic Obstacle |
| `5` | `POLE` | Lamp posts, traffic light poles, tree trunks | Structural Obstacle |
| `6` | `WALL_BUILDING` | Building facades, sound barriers, retaining walls | Structural Obstacle |
| `7` | `OTHER_OBSTACLE` | Debris, construction barrels, unclassified hazards | Obstacle |

### 3.1. SemanticKITTI Mapping Table
SemanticKITTI learning map IDs are converted into project class IDs as follows:

| SemanticKITTI Label | KITTI ID | Project Class ID | Project Class Name |
| :--- | :---: | :---: | :--- |
| `road`, `parking`, `lane-marking` | 9, 11, 12 | **0** | `DRIVABLE_GROUND` |
| `sidewalk`, `other-ground`, `terrain`, `vegetation` | 10, 13, 14, 15 | **1** | `NON_DRIVABLE_TERRAIN` |
| `car`, `truck`, `other-vehicle`, `bus` | 1, 3, 4, 5 | **2** | `VEHICLE` |
| `person` | 6 | **3** | `PEDESTRIAN` |
| `bicyclist`, `motorcyclist`, `bicycle`, `motorcycle` | 7, 8, 2 | **4** | `CYCLIST` |
| `pole`, `traffic-sign`, `trunk` | 17, 18, 16 | **5** | `POLE` |
| `building`, `fence` | 19, 20 | **6** | `WALL_BUILDING` |
| `other-object`, `unlabeled` | 0, 21 | **7** | `OTHER_OBSTACLE` |

### 3.2. nuScenes Mapping Table
nuScenes 16-class LiDAR segmentation taxonomy maps into project class IDs:

| nuScenes Class | nuScenes ID | Project Class ID | Project Class Name |
| :--- | :---: | :---: | :--- |
| `driveable_surface` | 1 | **0** | `DRIVABLE_GROUND` |
| `sidewalk`, `terrain`, `vegetation` | 2, 3, 4 | **1** | `NON_DRIVABLE_TERRAIN` |
| `car`, `truck`, `bus`, `trailer`, `construction_vehicle` | 5, 6, 7, 8, 9 | **2** | `VEHICLE` |
| `pedestrian` | 10 | **3** | `PEDESTRIAN` |
| `motorcycle`, `bicycle` | 11, 12 | **4** | `CYCLIST` |
| `traffic_cone`, `barrier` (poles/posts) | 13 | **5** | `POLE` |
| `manmade` (buildings, walls) | 15 | **6** | `WALL_BUILDING` |
| `other_flat`, `static_other`, `noise` | 0, 14, 16 | **7** | `OTHER_OBSTACLE` |

---

## 4. Contract Evolution & RFC Procedure

1. No developer may alter field names, datatypes, or physical coordinate frames unilaterally.
2. If an internal module requires schema adjustments, submit an RFC in an issue or team meeting.
3. Once approved, update `CONTRACTS.md` and `src/contracts.py` simultaneously.
