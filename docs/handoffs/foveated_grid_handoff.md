# Foveated Spatial Grid & Indexing Module Official Handoff

> **Module:** `src/foveated_grid/`  
> **Module Owner:** Manashri (Member 3)  
> **Branch:** `feature/manashri-foveated-grid`  
> **Target Integrator:** Vedant (System Integration & Release)  

---

## 1. CANONICAL INDEXER

The foveated indexing engine defines `CellKey` as a canonical `NamedTuple` subclass, reconciling object-style named attribute access and tuple-style unpacking/indexing with zero overhead.

### CellKey Definition
```python
class CellKey(NamedTuple):
    level: int  # Foveation ring level index (0, 1, 2, 3)
    i: int      # Discrete X column index (forward axis)
    j: int      # Discrete Y row index (left axis)

    # Ring/Level Aliases
    @property
    def ring_idx(self) -> int: return self.level
    @property
    def ring(self) -> int: return self.level
    @property
    def level_id(self) -> int: return self.level

    # Discrete 2D Coordinate Aliases
    @property
    def cell_x(self) -> int: return self.i
    @property
    def cell_y(self) -> int: return self.j
    @property
    def x(self) -> int: return self.i
    @property
    def y(self) -> int: return self.j

    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.level, self.i, self.j)
```

### Usage Example
```python
from src.foveated_grid import FoveatedGridIndexer, world_to_cell, cell_to_world

indexer = FoveatedGridIndexer()

# 1. World to Cell
key = indexer.world_to_cell(5.0, -2.5)
assert key is not None

# Named attribute access
print(key.level, key.i, key.j)
print(key.ring_idx, key.cell_x, key.cell_y)

# Tuple unpacking & indexing
ring_idx, cx, cy = key
assert key[0] == 0

# 2. Cell to World Center
x_center, y_center = indexer.cell_to_world(key)
# Or using indices: indexer.cell_to_world(key.i, key.j, key.level)
```

---

## 2. FOVEATION RINGS

The system maintains four concentric resolution rings centered on the vehicle ego origin:

| Ring Level | Level Name | Distance Band ($r = \sqrt{x^2+y^2}$) | Grid Resolution ($\Delta$) | Coordinate Offset ($x_{\min}, y_{\min}$) | Functional Priority |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Ring 0** | `near` | $[0.0\text{ m}, 10.0\text{ m})$ | **$0.05\text{ m}$ ($5\text{ cm}$)** | $-10.0\text{ m}, -10.0\text{ m}$ | Road hazards, curbs, potholes ($1.0$) |
| **Ring 1** | `mid_near` | $[10.0\text{ m}, 25.0\text{ m})$ | **$0.10\text{ m}$ ($10\text{ cm}$)** | $-25.0\text{ m}, -25.0\text{ m}$ | Dynamic actors, pedestrians ($0.8$) |
| **Ring 2** | `mid` | $[25.0\text{ m}, 50.0\text{ m})$ | **$0.25\text{ m}$ ($25\text{ cm}$)** | $-50.0\text{ m}, -50.0\text{ m}$ | Intermediate lane context ($0.5$) |
| **Ring 3** | `far` | $[50.0\text{ m}, 100.0\text{ m})$ | **$0.50\text{ m}$ ($50\text{ cm}$)** | $-100.0\text{ m}, -100.0\text{ m}$ | Horizon, distant buildings ($0.2$) |

### Why Half-Open Intervals $[r_k, r_{k+1})$ Are Used
Half-open intervals guarantee:
1. **Unambiguous Ring Ownership:** A point at an exact boundary (e.g. $r = 10.000\text{m}$) belongs strictly to Ring 1, never duplicating across Ring 0 and Ring 1.
2. **Gapless Partitioning:** The domain $[0, 100\text{m})$ is partitioned without spatial holes or overlap regions.
3. **Origin Invariant:** The sensor origin $(0, 0)$ where $r = 0.0\text{m}$ is deterministically owned by Ring 0 (`near`).

---

## 3. COORDINATE QUANTIZATION

### Distance Calculation
Horizontal Euclidean 2D sensing radius:
$$r = \sqrt{x^2 + y^2} = \text{hypot}(x, y)$$

### Coordinate Origin & Bounding Offsets
Each ring level $k$ defines its physical bounding box spanning $[-r_{\max, k}, +r_{\max, k}]$:
$$x_{\min, k} = -r_{\max, k}, \quad y_{\min, k} = -r_{\max, k}$$

### Floor Quantization Formula
Continuous coordinates $(x, y)$ map to discrete column/row indices $(i, j)$ via:
$$i = \left\lfloor \text{round}\left(\frac{x - x_{\min, k}}{\Delta_k}, 9\right) \right\rfloor$$
$$j = \left\lfloor \text{round}\left(\frac{y - y_{\min, k}}{\Delta_k}, 9\right) \right\rfloor$$
where $\text{round}(\cdot, 9)$ guards against IEEE-754 float precision boundary truncation (e.g., $10.1 / 0.05 = 201.99999999999997 \to 202$).

### Negative Coordinate & Quadrant Behavior
Because $x_{\min, k} = -r_{\max, k} < 0$, the quantity $(x - x_{\min, k}) \ge 0$ is strictly non-negative for all valid points inside the ring bounding box. Discrete cell indices $i, j \ge 0$ remain non-negative unsigned integers across all 4 Cartesian quadrants.

### Boundary Behavior
- Exact boundary $r = 10.0\text{m} \to \text{Ring } 1$ (`mid_near`).
- Epsilon inside $r = 10.0 - 10^{-6}\text{m} \to \text{Ring } 0$ (`near`).
- Maximum sensing limit $r = 100.0\text{m} \to \text{None}$ (out of range).
- Points beyond $100\text{m}$ or with negative distances return `None` safely.

---

## 4. SPARSE GRID

`SparseFoveatedGrid` provides a sparse hash-map data structure mapping discrete `CellKey` to `SparseCell` containers.

### Storage Model
- Internal storage: `Dict[CellKey, SparseCell]`.
- Empty cell overhead: **Zero**. Only cells containing at least one LiDAR observation are allocated in memory.

### Point Insertion & Lookup
- **Scalar Insertion (`insert(x, y, data)`):** Constant-time $O(1)$ coordinate quantization, instantiating `SparseCell` on first observation or appending payload to existing cell.
- **Point Query (`query(x, y)` / `get_cell_at(x, y)`):** Looks up occupied cell in $O(1)$ time ($2.02\text{ }\mu\text{s/lookup}$). If unoccupied or out-of-bounds, returns `None` without allocating dummy space.
- **Key Query (`query_cell(key)` / `get(key)`):** Direct hash table key lookup.
- **Region Query (`query_region(min_x, max_x, min_y, max_y)`):** Iterates strictly over occupied sparse cells $O(K)$, testing bounding box containment.

### Vectorized Batch Insertion (`insert_batch(points, payloads)`)
- Accepts NumPy arrays $(N, \ge 2)$ or contract dataclasses (`PointCloudFrame`, `SemanticPointCloud`).
- Vectorized batch distance computation, ring masking, and coordinate floor quantization via NumPy.
- Groups point indices into discrete cells via vectorized sorting and unique key splitting at C-speed ($>240\text{k--}318\text{k pts/s}$).

---

## 5. DOWNSTREAM API (MAPPING CONSUMPTION)

`FoveatedGridIndexer.assign_points()` conforms directly to the `GridIndexerProtocol` consumed by Heet's `SemanticElevationMapper` (`src/mapping/mapper.py`):

```python
def assign_points(
    self, points: np.ndarray
) -> Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]:
    """Assigns (N, 3) points into discrete spatial cells across foveation rings.
    
    Returns:
        Dict mapping:
            ring_name ("near", "mid_near", "mid", "far") ->
                (cell_x, cell_y) ->
                    (center_x, center_y, point_indices_array)
    """
```

### Downstream Consumption Workflow in Mapping:
```python
# In src/mapping/mapper.py:
assignments = foveated_indexer.assign_points(semantic_cloud.points)

for ring_name, cell_dict in assignments.items():
    for (gx, gy), (center_x, center_y, pt_indices) in cell_dict.items():
        cell_z = semantic_cloud.points[pt_indices, 2]
        cell_cls = semantic_cloud.semantic_class[pt_indices]
        cell_conf = semantic_cloud.confidence[pt_indices]
        
        # Aggregate cell elevation, roughness, semantics, and occupancy
        grid_cell = aggregate_cell(
            resolution_level=ring_name,
            cell_x=center_x,
            cell_y=center_y,
            points_z=cell_z,
            classes=cell_cls,
            confidences=cell_conf,
            timestamp=semantic_cloud.timestamp,
        )
```

---

## 6. TESTS

### Test Command
```bash
.venv\Scripts\pytest -v tests/foveated_grid/
```

### Exact Test Output
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\manas\OneDrive\Documents\LiDAR_Syntrix
configfile: pyproject.toml
collected 57 items

tests\foveated_grid\test_batch_insert.py .......                         [ 12%]
tests\foveated_grid\test_canonical_indexer.py ........                   [ 26%]
tests\foveated_grid\test_foveated_indexer.py ..............              [ 50%]
tests\foveated_grid\test_mapping_integration.py ....                     [ 57%]
tests\foveated_grid\test_sparse_grid.py ...................              [ 91%]
tests\foveated_grid\test_stress_validation.py .....                      [100%]

============================= 57 passed in 2.54s ==============================
```

### Full Repository Verification
```bash
.venv\Scripts\pytest -v
```
```text
============================= 100 passed in 2.11s =============================
```

### Covered Edge Cases & Tests
- **Tuple Unpacking & Named Attributes:** `test_cell_key_tuple_unpacking`
- **Ring Boundaries & Epsilon Limits:** `test_resolution_for_distance_exact_boundaries`, `test_ring_boundaries_and_epsilon_transitions`
- **Four Quadrants & Sign Combinations:** `test_four_quadrants_negative_coordinates`
- **Sparse Storage & Non-Allocation:** `test_sparse_grid_storage_and_queries`, `test_iter_occupied_cells_non_mutating`
- **Vectorized Ingestion & Stress:** `test_batch_insert_large_synthetic`, `test_stress_pipeline_100k_points`
- **Mapping Integration Protocol:** `test_assign_points_protocol`, `test_semantic_point_cloud_to_semantic_map_handoff`

---

## 7. BENCHMARK METHODOLOGY

> [!NOTE]
> The cell-count reduction figures reported below represent a **module-level geometric storage benchmark** based on spatial grid discretization.
> **The final project-wide baseline definition must be locked during integration.**

### Spatial Domain & Envelope Definitions
1. **Uniform Baseline Grid ($5\text{ cm}$ Uniform Resolution):**
   - **Square Bounding Domain ($200\text{m} \times 200\text{m}$):**
     $$\text{Cells}_{\text{square}} = \left(\frac{200}{0.05}\right)^2 = 4000 \times 4000 = 16,000,000\text{ cells}$$
   - **Radial Disk Envelope ($R = 100\text{m}$):**
     $$\text{Cells}_{\text{radial}} = \frac{\pi \times (100.0)^2}{0.05^2} \approx 12,566,371\text{ cells}$$

2. **Foveated Rings Grid ($5 / 10 / 25 / 50\text{ cm}$):**
   - **Bounding Square Domains:**
     $$\text{Ring 0: } \left(\frac{20}{0.05}\right)^2 = 160,000\text{ cells}$$
     $$\text{Ring 1: } \left(\frac{50}{0.10}\right)^2 - \left(\frac{20}{0.10}\right)^2 = 250,000 - 40,000 = 210,000\text{ cells}$$
     $$\text{Ring 2: } \left(\frac{100}{0.25}\right)^2 - \left(\frac{50}{0.25}\right)^2 = 160,000 - 40,000 = 120,000\text{ cells}$$
     $$\text{Ring 3: } \left(\frac{200}{0.50}\right)^2 - \left(\frac{100}{0.50}\right)^2 = 160,000 - 40,000 = 120,000\text{ cells}$$
     $$\text{Total Square Foveated Cells} = 730,000\text{ cells (}\mathbf{95.44\%}\text{ reduction vs 16.0M uniform square)}$$
   - **Radial Concentric Annuli Domains:**
     $$\text{Ring 0 } [0, 10\text{m}): \frac{\pi (10^2 - 0^2)}{0.05^2} \approx 125,664\text{ cells}$$
     $$\text{Ring 1 } [10, 25\text{m}): \frac{\pi (25^2 - 10^2)}{0.10^2} \approx 164,934\text{ cells}$$
     $$\text{Ring 2 } [25, 50\text{m}): \frac{\pi (50^2 - 25^2)}{0.25^2} \approx 94,248\text{ cells}$$
     $$\text{Ring 3 } [50, 100\text{m}): \frac{\pi (100^2 - 50^2)}{0.50^2} \approx 94,248\text{ cells}$$
     $$\text{Total Radial Foveated Cells} = 479,094\text{ cells (}\mathbf{96.19\%}\text{ reduction vs 12.57M uniform radial)}$$

### Hardware & Execution Environment
- **Platform:** Intel64 Family 6 Model 189 Stepping 1, Windows 11, Python 3.12.10.
- **Timing:** `time.perf_counter()`, median over 5 trials.
- **Measured Throughput:**
  - 10k points: $318,354\text{ pts/s}$ ($31.41\text{ ms}$)
  - 50k points: $269,460\text{ pts/s}$ ($185.56\text{ ms}$)
  - 100k points: $241,571\text{ pts/s}$ ($413.96\text{ ms}$)
  - Point lookup rate: $493,869\text{ lookups/s}$

---

## 8. COMPATIBILITY & RECOMMENDED IMPORTS

### Recommended Imports for Downstream Modules
```python
# Canonical Primary Imports
from src.foveated_grid import (
    CellKey,
    FoveatedGridIndexer,
    FoveationLevelConfig,
    SparseCell,
    SparseFoveatedGrid,
    assign_points,
    cell_to_world,
    get_level_for_distance,
    load_foveation_config,
    resolution_for_distance,
    world_to_cell,
)
```

### Backward Compatibility Module
If any legacy script or external test imports `src.foveated_grid.grid_indexer`, the new `grid_indexer.py` compatibility layer automatically re-exports all canonical classes and functions without breaking.

---

## FINAL SUMMARY

- **Status:** **COMPLETE & VERIFIED**
- **Ready for Merge:** **YES**
- **Commit Hash:** `098bcb758d9e6074213d2f9547d7c672b14352be`
