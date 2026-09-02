# Module Handoff & Interface Specification: Semantic Perception

- **Module Path:** `src/perception/`
- **Owner:** Vedant
- **Upstream Producer:** Amulya (`src/preprocessing/`)
- **Downstream Consumer:** Manashri (`src/foveated_grid/`) & Heet (`src/mapping/`)
- **Status:** Phase 2 Architecture Frozen

---

## 1. Responsibilities
- Implement 3D deep learning point cloud semantic segmentation inheriting from `BaseSemanticSegmenter`.
- Output class predictions strictly across the project 8-class taxonomy:
  - `0`: DRIVABLE_GROUND
  - `1`: NON_DRIVABLE_TERRAIN
  - `2`: VEHICLE
  - `3`: PEDESTRIAN
  - `4`: CYCLIST
  - `5`: POLE
  - `6`: WALL_BUILDING
  - `7`: OTHER_OBSTACLE
- Compute per-point confidence values normalized in $[0.0, 1.0]$.
- Deliver validated `SemanticPointCloud` instances.

## 2. Shared Data Contract
```python
from src.contracts import SemanticPointCloud

sem_cloud = SemanticPointCloud(
    points=points,                # np.ndarray (N, 3), float32
    semantic_class=classes,       # np.ndarray (N,), int32 in range [0..7]
    confidence=confidences,       # np.ndarray (N,), float32 in range [0.0, 1.0]
    timestamp=timestamp,
    frame_id="lidar_top",
    intensity=intensity,
)
```

## 3. Mock Model Available
- `src/perception/mock.py`: `MockSemanticSegmenter` allows testing without heavy GPU dependencies.

## 4. Verification Command
```bash
pytest tests/perception/ -v
```
