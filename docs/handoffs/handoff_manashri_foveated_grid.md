# Module Handoff & Interface Specification: Foveated Spatial Grid

- **Module Path:** `src/foveated_grid/`
- **Owner:** Manashri
- **Upstream Producer:** Vedant (`src/perception/`)
- **Downstream Consumer:** Heet (`src/mapping/`)
- **Status:** Phase 2 Architecture Frozen

---

## 1. Responsibilities
- Implement multi-ring spatial grid indexing supporting 4 concentric distance rings:
  - **Level 0 (Near):** $0\text{--}10\text{m}$ @ $5\text{cm}$ resolution ($\Delta = 0.05\text{m}$)
  - **Level 1 (Mid-Near):** $10\text{--}25\text{m}$ @ $10\text{cm}$ resolution ($\Delta = 0.10\text{m}$)
  - **Level 2 (Mid):** $25\text{--}50\text{m}$ @ $25\text{cm}$ resolution ($\Delta = 0.25\text{m}$)
  - **Level 3 (Far):** $50\text{--}100\text{m}$ @ $50\text{cm}$ resolution ($\Delta = 0.50\text{m}$)
- Handle half-open boundary intervals $[r_k, r_{k+1})$ and negative coordinates deterministically.
- Provide high-throughput point binning: `bin_points(points) -> Dict[Tuple[int, int, int], List[int]]`.
- Support adaptive semantic/uncertainty refinement hook.

## 2. Shared Data Contract & API
```python
from src.foveated_grid import FoveatedGridIndexer, FoveationRing

indexer = FoveatedGridIndexer()
ring = indexer.get_ring_for_distance(distance=8.5) # Returns Ring 0 (near, res=0.05)
cell_info = indexer.world_to_cell(x=5.2, y=-3.1)   # (level_id, cell_ix, cell_iy, center_x, center_y)
world_pos = indexer.cell_to_world(level_id=0, cell_ix=104, cell_iy=-62)
bins = indexer.bin_points(points) # Fast spatial hash binning
```

## 3. Verification Command
```bash
pytest tests/foveated_grid/ -v
```
