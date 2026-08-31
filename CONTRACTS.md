# CONTRACTS.md — System Data Contracts & Interface Specifications

This document serves as the concise, authoritative source of truth for all shared data structures, coordinate systems, and architectural contracts in the **Foveated Semantic 2.5D LiDAR Mapping** system.

---

## 1. Coordinate System Contract (FROZEN)

```text
X = forward (meters)
Y = left    (meters)
Z = up      (meters)
```
* **Convention:** Right-Handed FLU (Forward-Left-Up).
* **Metric Standard:** All coordinates ($x, y, z$), ranges ($r$), elevations, step heights, and cell resolutions are strictly in **meters ($m$)**.
* **Angles:** All rotational angles (yaw, pitch, roll, slopes) are in **radians ($rad$)**.
* **Time:** Timestamps are in **seconds ($s$, float64)**.

---

## 2. Semantic Taxonomy Contract (FROZEN)

| ID | Class Enum Name | Semantics & Ground/Obstacle Role | Default Traversable |
| :---: | :--- | :--- | :---: |
| **0** | `DRIVABLE_GROUND` | Paved road, asphalt, smooth navigable ground | **True** |
| **1** | `NON_DRIVABLE_TERRAIN` | Grass, dirt, gravel, mud, vegetation | **False** |
| **2** | `VEHICLE` | Cars, trucks, buses, vans, trailers | **False** |
| **3** | `PEDESTRIAN` | Pedestrians, walking/standing persons | **False** |
| **4** | `CYCLIST` | Bicyclists, motorcyclists and mounts | **False** |
| **5** | `POLE` | Utility poles, street signs, light posts, tree trunks | **False** |
| **6** | `WALL_BUILDING` | Building walls, solid barriers, fences | **False** |
| **7** | `OTHER_OBSTACLE` | Debris, unclassified static objects, curbs | **False** |

> **Dataset Adaptation Rule:** External datasets (SemanticKITTI, nuScenes, Waymo) utilize varied label spaces. Dedicated adapters (`IDatasetAdapter`) MUST map external labels to this 8-class taxonomy before perception ingestion or ground-truth evaluation.

---

## 3. Foveation Geometry & Boundary Contract

Foveation level is determined by Euclidean distance on the ground plane $r = \sqrt{x^2 + y^2}$:

$$\text{Level}(r) = \begin{cases} 
0 & \text{for } 0.0 \le r < 10.0\,m \quad (\text{Cell size: } 0.05\,m) \\ 
1 & \text{for } 10.0 \le r < 25.0\,m \quad (\text{Cell size: } 0.10\,m) \\ 
2 & \text{for } 25.0 \le r < 50.0\,m \quad (\text{Cell size: } 0.25\,m) \\ 
3 & \text{for } 50.0 \le r \le 100.0\,m \quad (\text{Cell size: } 0.50\,m) 
\end{cases}$$

* **Interval Convention:** Half-open interval $[r_{min}, r_{max})$ for levels 0–2; closed $[50.0, 100.0]$ for level 3.
* **Out-of-Range Handling:** Points with $r < 0.0$ or $r > 100.0\,m$ are filtered or ignored.
* **Extensibility Hook:** The architecture permits future adaptive refinement:
  $$\text{Resolution} = f(\text{distance}, \text{semantic\_importance}, \text{uncertainty})$$

---

## 4. Core Data Structure Contracts

### 4.1 PointCloudFrame
Ingestion and preprocessing contract.

```python
@dataclass
class PointCloudFrame:
    points: np.ndarray        # Shape (N, 3), float32, FLU frame in meters
    intensity: Optional[np.ndarray] = None  # Shape (N,), float32
    timestamp: float = 0.0   # Epoch seconds
    frame_id: Union[int, str] = 0
    sensor_pose: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))
```

### 4.2 SemanticPointCloud
Output of perception stage, input to spatial indexing and mapping.

```python
@dataclass
class SemanticPointCloud:
    points: np.ndarray          # Shape (N, 3), float32
    semantic_labels: np.ndarray # Shape (N,), uint8 (Class IDs 0..7)
    confidence: np.ndarray      # Shape (N,), float32 in [0.0, 1.0]
    intensity: Optional[np.ndarray] = None
    timestamp: float = 0.0
    frame_id: Union[int, str] = 0
    sensor_pose: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))
```

### 4.3 GridCell
Semantic 2.5D foveated column cell.

```python
@dataclass
class GridCell:
    # Spatial & Resolution Identity
    resolution_level: int       # 0, 1, 2, 3
    cell_index: Tuple[int, int] # Discrete (ix, iy)
    position: Tuple[float, float] # Continuous cell center (x, y) in meters
    
    # 2.5D Elevation & Geometry
    elevation: float            # Estimated ground elevation (mean Z in m)
    min_z: float                # Minimum observed point Z (m)
    max_z: float                # Maximum observed point Z (m)
    roughness: float            # Surface variance / plane fitting residual (m)
    
    # Semantics & Occupancy
    semantic_class: int         # Dominant class ID (0..7)
    semantic_confidence: float  # Classification confidence [0.0, 1.0]
    occupancy: float            # Occupancy probability [0.0, 1.0]
    point_count: int            # Number of points aggregated
    timestamp: float            # Latest update timestamp
    
    # Extension Points (Future-proofed)
    velocity: Optional[Tuple[float, float, float]] = None  # (vx, vy, vz)
    observation_count: int = 1                             # Temporal hits
    uncertainty: float = 0.0                               # Elevation variance
    semantic_probs: Optional[List[float]] = None           # 8-element probability vector
```

### 4.4 SemanticMap
Map container representation.

```python
@dataclass
class SemanticMap:
    cells: Dict[Tuple[int, int, int], GridCell]  # Key: (level, ix, iy)
    resolution_levels: List[FoveationLevelConfig]
    sensor_pose: np.ndarray                      # 4x4 transform
    timestamp: float = 0.0
    frame_id: Union[int, str] = 0
```

---

## 5. Foveated Spatial Indexing Contract (`src/foveated_grid/`)

* **Deterministic Conversions:**
  $$\text{CellIndex}(x, y, \Delta) = \left(\left\lfloor \frac{x}{\Delta} \right\rfloor, \left\lfloor \frac{y}{\Delta} \right\rfloor\right)$$
  $$\text{WorldCenter}(i_x, i_y, \Delta) = \left((i_x + 0.5)\Delta, (i_y + 0.5)\Delta\right)$$
* **Negative Coordinate Support:** Full, symmetric handling across all four quadrants ($x < 0, y < 0$).
* **Candidate Storage Implementations for Phase E Benchmarking:**
  1. Flat Hash Table with Packed Integer Keys (e.g. `uint64 = (level << 48) | (ix << 24) | iy`)
  2. Morton / Z-order spatial hashing
  3. Multi-layer Quadtree
  4. Hierarchical nested 2D dense grids per zone

---

## 6. 2.5D Semantic Mapping Contract (`src/mapping/`)

* **Not a 2D Flat Occupancy Grid:** Represents elevation ($Z$), vertical extent ($span = max\_z - min\_z$), surface roughness, and semantic consensus per cell.
* **Traversability Scoring Function Contract:**
  $$\text{Cost} = w_s \cdot \text{Slope} + w_h \cdot \text{StepHeight} + w_r \cdot \text{Roughness} + w_{sem} \cdot \text{SemanticPenalty}$$
* **Geometric Analysis Requirements:**
  - Elevation estimation from ground returns.
  - Step height discontinuity detection (curbs, potholes).
  - Overhang handling (points with free space underneath).

---

## 7. Perception Interface Contract (`src/perception/`)

* **Model Independence:** Perception is completely isolated behind `ISemanticPerception.infer(PointCloudFrame) -> SemanticPointCloud`.
* **Swappable Architectures:** Permits future integration of PointNet++, SparseConv, MinkowskiEngine, or lightweight Point Transformer backbones without modifying mapping code.

---

## 8. Telemetry & Performance Contract (`src/evaluation/`)

* **Zero-Fabrication Contract:** All reported statistics must be measured directly from physical execution timers.
* **Required Metrics:**
  - Preprocessing Latency ($ms$)
  - Perception Inference Latency ($ms$)
  - Spatial Insertion / Projection Latency ($ms$)
  - 2.5D Mapping Latency ($ms$)
  - Total Pipeline Latency ($ms$) & Real-time FPS ($Hz$)
  - Host RAM Usage ($MB$) & GPU VRAM Usage ($MB$)
  - Point count vs. Grid cell count compression ratio
* **Mandatory Evaluation Benchmark:** Side-by-side comparison of **Uniform High-Resolution Grid ($0.05\,m$)** vs. **Multi-Resolution Foveated Grid**.
