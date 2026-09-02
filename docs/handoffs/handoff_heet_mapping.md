# Module Handoff & Interface Specification: 2.5D Elevation Mapping & Hazards

- **Module Path:** `src/mapping/`
- **Owner:** Heet
- **Upstream Producers:** Manashri (`src/foveated_grid/`) & Vedant (`src/perception/`)
- **Downstream Consumers:** Atharva (`src/integration/`, `src/visualization/`) & Himisha (`src/evaluation/`)
- **Status:** Phase 2 Architecture Frozen

---

## 1. Responsibilities
- Aggregate point elevations into nominal $Z$, $Z_{\min}$, $Z_{\max}$, and surface roughness $\sigma_z^2$ per cell.
- Fuse per-point semantic predictions into dominant cell class and confidence.
- Implement geometric hazard detection:
  - **Curbs:** Step discontinuity $8\text{cm} \le \Delta z \le 25\text{cm}$.
  - **Potholes:** Local negative road depression $\Delta z \le -5\text{cm}$.
  - **Overhangs:** Safe vertical vehicle clearance $> 2.2\text{m}$.
  - **Slope & Traversability:** Terrain gradient $\theta \le 15^\circ$ for drivability.
- Produce validated `SemanticMap` instances containing `GridCell` objects.

## 2. Shared Data Contract
```python
from src.contracts import GridCell, SemanticMap
from src.mapping import SemanticMapBuilder

builder = SemanticMapBuilder()
semantic_map = builder.build_map(semantic_cloud, sensor_pose=pose)
```

## 3. Verification Command
```bash
pytest tests/mapping/ -v
```
