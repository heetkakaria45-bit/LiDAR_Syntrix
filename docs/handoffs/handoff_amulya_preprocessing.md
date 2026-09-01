# Module Handoff & Interface Specification: Preprocessing

- **Module Path:** `src/preprocessing/`
- **Owner:** Amulya
- **Downstream Consumer:** Vedant (`src/perception/`) & Atharva (`src/integration/`)
- **Status:** Phase 2 Architecture Frozen

---

## 1. Responsibilities
- Ingest raw LiDAR data (.pcd, .bin, or ROS2 messages).
- Apply statistical outlier removal and distance clipping ($0.5\text{m} \le r \le 100\text{m}$).
- Transform sensor point clouds into base/ego frame ($X=\text{forward}, Y=\text{left}, Z=\text{up}$).
- Deliver validated `PointCloudFrame` instances.

## 2. Shared Data Contract
```python
from src.contracts import PointCloudFrame

frame = PointCloudFrame(
    points=points,       # np.ndarray (N, 3), float32
    intensity=intensity, # Optional np.ndarray (N,), float32
    timestamp=timestamp, # float (seconds)
    frame_id="lidar_top",
    sensor_pose=pose,    # np.ndarray (4, 4), float64
)
```

## 3. Mock & Synthetic Data Available
- `src/preprocessing/synthetic.py`: `generate_synthetic_scene(config)`
- Generates curbs, potholes, slopes, vehicles, pedestrians, poles, and buildings.

## 4. Verification Command
```bash
pytest tests/preprocessing/ -v
```
