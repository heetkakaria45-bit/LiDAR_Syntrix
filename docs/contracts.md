# System Interface Contracts & Data Specifications

> **Canonical Document:** [CONTRACTS.md](file:///c:/Users/kakar/LiDAR/CONTRACTS.md)  
> **Status:** Architecture Freeze Standard (v0.2.0)  
> **Applicability:** Mandatory across all six pipeline modules.

*(Refer to [CONTRACTS.md](file:///c:/Users/kakar/LiDAR/CONTRACTS.md) for the root specification)*

---

## Summary of Frozen Contracts

### 1. `PointCloudFrame`
- `points`: $(N, 3)$ float32, coordinates in standard ego frame ($X=\text{forward}, Y=\text{left}, Z=\text{up}$ in meters).
- `intensity`: Optional $(N,)$ float32.
- `timestamp`: float64.
- `frame_id`: str.
- `sensor_pose`: $(4, 4)$ float64 matrix.

### 2. `SemanticPointCloud`
- `points`: $(N, 3)$ float32.
- `semantic_class`: $(N,)$ int32 matching project taxonomy ($0\text{--}7$).
- `confidence`: $(N,)$ float32 normalized in $[0.0, 1.0]$.
- `intensity`: Optional $(N,)$ float32.
- `timestamp`: float64.
- `frame_id`: str.

### 3. `GridCell`
- Spatial & Foveation: `resolution_level`, `cell_x`, `cell_y`.
- Elevation & Geometry: `elevation`, `min_z`, `max_z`, `roughness`.
- Semantics & Occupancy: `semantic_class`, `confidence`, `occupancy`, `point_count`.
- Temporal & Dynamic Extensions: `timestamp`, `velocity`, `observation_count`, `uncertainty`, `semantic_probabilities`.

### 4. `SemanticMap`
- Multi-resolution cell container, active ring parameters, 6-DoF sensor pose, snapshot timestamp, and metadata.

### 5. Dataset Label Mappings
- Full mapping tables for **SemanticKITTI** and **nuScenes** defined in [CONTRACTS.md](file:///c:/Users/kakar/LiDAR/CONTRACTS.md#3-standard-semantic-taxonomy--dataset-label-mapping).
