# Foveated Spatial Grid Module Official Engineering Handoff

---

## SECTION 1 — OWNER
- **Name:** Manashri
- **Role:** Foveated Grid & Spatial Indexing Lead (Member 3)
- **Branch:** `feature/manashri-foveated-grid`
- **Current HEAD:** `fix(foveated): unify canonical spatial indexer contract`
- **Commit Hash:** `11053279ca147ccad58fbe1df815607314b1d1e4`

---

## SECTION 2 — RESPONSIBILITY

### What this workstream OWNS:
- Multi-ring variable-resolution spatial indexing (`src/foveated_grid/foveated_indexer.py`, `src/foveated_grid/grid_indexer.py`).
- Deterministic world-to-cell $(X, Y) \to (i, j, \text{level})$ coordinate quantization and cell-to-world $(i, j, \text{level}) \to (X_c, Y_c)$ center coordinate reconstruction.
- Half-open radial interval boundary enforcement $[r_k, r_{k+1})$.
- Sparse hash table data structure and cell accumulation (`SparseFoveatedGrid`, `SparseCell` in `src/foveated_grid/sparse_grid.py`).
- High-throughput scalar insertion, vectorized batch point assignment (`assign_points()`), and spatial region bounding queries.
- Handoff conversions to standardized `GridCell` and `SemanticMap` contract instances.

### What this workstream DOES NOT own:
- Point cloud ingestion, sanitization, and range filtering (owned by Amulya, `src/preprocessing/`).
- 3D semantic perception, feature extraction, and class inferencing (owned by Vedant, `src/perception/`).
- Elevation aggregation, slope estimation, terrain traversability, and curb/pothole hazard detection (owned by Heet, `src/mapping/`).
- End-to-end orchestration, UI/dashboard, and WebSockets (owned by Atharva, `src/integration/`, `src/visualization/`).
- Formal benchmarking suites and mIoU evaluation (owned by Himisha, `src/evaluation/`).

---

## SECTION 3 — WHAT WAS IMPLEMENTED

### 1. Canonical `CellKey` (`src/foveated_grid/foveated_indexer.py`)
- **Status:** ✅ IMPLEMENTED AND VERIFIED
- **Purpose:** Provide a canonical, hashable, tuple-compatible key for discrete multi-resolution cell identification.
- **Classes/Functions:** `CellKey(NamedTuple)`
- **Algorithm:** Inherits from `NamedTuple(level: int, i: int, j: int)` with bit-packing methods (`to_packed_uint64`, `from_packed_uint64`) and property aliases (`.ring_idx`, `.cell_x`, `.cell_y`, `.ring`, `.level_id`, `.x`, `.y`).
- **Input:** `level: int` ($0\text{--}3$), `i: int` (column index), `j: int` (row index).
- **Output:** Hashable 3-tuple / NamedTuple instance.
- **Dependencies:** Pure Python standard library (`typing.NamedTuple`).

### 2. `FoveatedGridIndexer` (`src/foveated_grid/foveated_indexer.py`)
- **Status:** ✅ IMPLEMENTED AND VERIFIED
- **Purpose:** Deterministic constant-time $O(1)$ spatial coordinate mapping and vector batch partitioning.
- **Important Methods:**
  - `get_level_for_distance(distance: float) -> Optional[FoveationLevelConfig]`
  - `resolution_for_distance(distance: float) -> Optional[float]`
  - `world_to_cell(x: float, y: float, level: Optional[int] = None) -> Optional[CellKey]`
  - `cell_to_world(cell_or_ix, iy=None, level=None) -> Tuple[float, float]`
  - `world_to_cell_batch(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]`
  - `assign_points(points: np.ndarray) -> Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]`
- **Algorithm:**
  - Radial distance $r = \sqrt{x^2 + y^2}$.
  - Level lookup adhering to half-open interval $[r_k, r_{k+1})$.
  - Floor quantization with IEEE-754 precision guard: $i = \lfloor \text{round}((x - x_{\min}) / \Delta, 9) \rfloor$, $j = \lfloor \text{round}((y - y_{\min}) / \Delta, 9) \rfloor$, where $x_{\min} = y_{\min} = -r_{\max, k}$.
  - Center reconstruction: $X_c = x_{\min} + (i + 0.5)\Delta$, $Y_c = y_{\min} + (j + 0.5)\Delta$.
- **Dependencies:** NumPy, PyYAML.
- **Configuration:** Ingests `configs/default_config.yaml` (`foveation_levels` section).

### 3. `SparseFoveatedGrid` & `SparseCell` (`src/foveated_grid/sparse_grid.py`)
- **Status:** ✅ IMPLEMENTED AND VERIFIED
- **Purpose:** Memory-efficient sparse spatial hash storage allocating only observed cells with zero memory overhead for unobserved regions.
- **Important Methods:** `insert()`, `insert_batch()`, `query()`, `get_cell_at()`, `query_cell()`, `get()`, `query_region()`, `iter_occupied_cells()`, `to_grid_cells()`, `to_semantic_map()`.
- **Dependencies:** NumPy, `src/contracts.py`.

### 4. Compatibility Module `grid_indexer.py` (`src/foveated_grid/grid_indexer.py`)
- **Status:** ✅ IMPLEMENTED AND VERIFIED
- **Purpose:** Re-exports all canonical classes and functions to guarantee backward compatibility with legacy scripts and tests.

---

## SECTION 4 — DATA CONTRACT

### Input Contract
- **Datatype:** `np.ndarray` or contract dataclasses (`PointCloudFrame`, `SemanticPointCloud`).
- **Shape:** $(N, 2)$, $(N, 3)$, or $(N, \ge 3)$.
- **Dtype:** `float32` or `float64` for points; `int32`/`uint8` for class labels; `float32` for confidences.
- **Units:** Meters for $(x, y, z)$.
- **Coordinate Convention:** Right-handed Cartesian ($+X = \text{Forward}$, $+Y = \text{Left}$, $+Z = \text{Up}$).

### Output Contract
1. **Spatial Assignments (`assign_points`):**
   - Datatype: `Dict[str, Dict[Tuple[int, int], Tuple[float, float, np.ndarray]]]`
   - Mapping: `level_name` (`"near"`, `"mid_near"`, `"mid"`, `"far"`) $\to (i, j) \to (X_c, Y_c, \text{point\_indices\_array})$.
   - Consumed by: `src/mapping/mapper.py` (`SemanticElevationMapper`).
2. **Contract Objects (`to_grid_cells`, `to_semantic_map`):**
   - Datatypes: `List[GridCell]`, `SemanticMap` (conforming to `CONTRACTS.md` and `src/contracts.py`).
   - Consumed by: `src/mapping/`, `src/integration/`, `src/visualization/`.

---

## SECTION 5 — FILES CHANGED

| File | Change Type | Reason |
| :--- | :---: | :--- |
| `src/foveated_grid/foveated_indexer.py` | `MODIFIED` | Implemented canonical NamedTuple `CellKey`, flexible calling signatures, and `assign_points()` mapping protocol. |
| `src/foveated_grid/sparse_grid.py` | `MODIFIED` | Added `get_cell_at()` and `get()` query aliases for flexible query syntax. |
| `src/foveated_grid/__init__.py` | `MODIFIED` | Standardized canonical and convenience exports. |
| `src/foveated_grid/grid_indexer.py` | `NEW` | Added backward-compatibility re-export shim. |
| `tests/foveated_grid/test_canonical_indexer.py` | `NEW` | Added regression test suite verifying canonical interface, four rings, boundary limits, and integration protocol. |
| `docs/handoffs/foveated_grid_handoff.md` | `NEW` | Added formal module handoff specification. |

---

## SECTION 6 — TESTS

### Test Command 1 (Module Suite)
```bash
.venv\Scripts\pytest -v tests/foveated_grid/
```
- **Result:** 57 passed, 0 failed, 0 errors in 2.05s.
- **Pass Count:** 57
- **Fail Count:** 0
- **Error Count:** 0

### Test Command 2 (Full System Suite)
```bash
.venv\Scripts\pytest -v
```
- **Result:** 100 passed, 0 failed, 0 errors in 2.11s.
- **Pass Count:** 100
- **Fail Count:** 0
- **Error Count:** 0

---

## SECTION 7 — MANUAL VERIFICATION

1. **Benchmark Execution:**
   ```bash
   .venv\Scripts\python scripts/benchmark_foveated_grid.py
   ```
   - Verified that 5-trial median benchmarks execute cleanly across 10k, 50k, and 100k point workloads with zero exceptions.
2. **Synthetic Integration Run:**
   - Ingested deterministic synthetic curb ($0.15\text{m}$ step) and pothole ($-0.08\text{m}$ depression) scenes via `ingest_point_cloud()`.
   - Verified that near-field resolution ($0.05\text{m}$) correctly resolves curb boundaries into discrete contiguous cell bands.

---

## SECTION 8 — BENCHMARKS / NUMERIC CLAIMS

### Metric 1: Module-Level Geometric Storage Reduction
- **Value:** $96.19\%$ (concentric annuli vs uniform circular baseline) / $95.44\%$ (bounding squares vs uniform square baseline).
- **What it measures:** Theoretical cell capacity reduction of foveated resolution bands compared to a dense $0.05\text{m}$ uniform grid.
- **Classification:** **CALCULATED** (Geometric analysis).
- **Calculation:**
  - Uniform $0.05\text{m}$ circle ($R = 100\text{m}$): $\frac{\pi \times 100^2}{0.05^2} = 12,566,371\text{ cells}$.
  - Foveated annuli: $125,664 + 164,934 + 94,248 + 94,248 = 479,094\text{ cells}$.
  - Reduction: $1.0 - (479,094 / 12,566,371) = 96.1875\%$.
- **Note:** This is a module-level geometric reduction benchmark and NOT the final end-to-end system benchmark.

### Metric 2: Batch Insertion Throughput
- **Values:**
  - 10,000 points: $318,354\text{ pts/s}$ ($31.41\text{ ms}$)
  - 50,000 points: $269,460\text{ pts/s}$ ($185.56\text{ ms}$)
  - 100,000 points: $241,571\text{ pts/s}$ ($413.96\text{ ms}$)
- **What it measures:** Vectorized batch point ingestion and sparse cell assignment rate.
- **Classification:** **MEASURED**.
- **Hardware:** Intel64 Family 6 Model 189 Stepping 1, Windows 11, Python 3.12.10.
- **Measurement Method:** Median wall-clock time over 5 trials using `time.perf_counter()`.

### Metric 3: Point Query Lookup Rate
- **Value:** $493,869\text{ lookups/s}$ ($2.02\text{ }\mu\text{s/lookup}$).
- **What it measures:** Point-to-cell spatial hash lookup speed.
- **Classification:** **MEASURED**.

---

## SECTION 9 — KNOWN LIMITATIONS

1. **Horizontal 2D Radial Metric:** Foveation ring lookup calculates $r = \sqrt{x^2 + y^2}$, assuming points are in the horizontal ground plane frame.
2. **Ego Frame Alignment:** Rings are centered on coordinate origin $(0, 0)$. In dynamic vehicle motion, world point clouds must be transformed to ego base frame prior to insertion, or transformed via `sensor_pose`.
3. **Artifact Dependency:** `outputs/grid_benchmark_results.json` is a generated offline profiling artifact, **not** a required runtime dependency.

---

## SECTION 10 — INTEGRATION REQUIREMENTS

- **Upstream Dependency:** Receives `PointCloudFrame` from Amulya (`src/preprocessing/`) or `SemanticPointCloud` from Vedant (`src/perception/`).
- **Downstream Consumer:** Consumed by Heet (`src/mapping/mapper.py`) via `assign_points(points)` or `grid.to_semantic_map()`.
- **Expected Data Format:** Points as NumPy array $(N, 3)$ with $(X=\text{fwd}, Y=\text{left}, Z=\text{up})$ in meters.
- **Configuration:** Reads `configs/default_config.yaml` or accepts programmatic `FoveationLevelConfig` overrides.
- **Dependencies:** Only core lightweight dependencies (`numpy`, `pyyaml`).

---

## SECTION 11 — MERGE RISKS

- **Merge Conflicts:** None anticipated. No files outside `src/foveated_grid/` and `tests/foveated_grid/` were modified.
- **API Assumptions:** `CellKey` supports both named attributes and tuple unpacking `(level, i, j)` / `(ring_idx, cell_x, cell_y)`.
- **Backward Compatibility:** `src/foveated_grid/grid_indexer.py` re-exports all canonical symbols.

---

## SECTION 12 — HOW TO VERIFY AFTER MERGE

1. Activate virtual environment:
   ```bash
   .venv\Scripts\activate
   ```
2. Run the foveated grid test suite:
   ```bash
   pytest -v tests/foveated_grid/
   ```
   *Expected result: 57 passed.*
3. Run the full repository test suite:
   ```bash
   pytest -v
   ```
   *Expected result: 100 passed.*
4. Run the foveated benchmark script:
   ```bash
   python scripts/benchmark_foveated_grid.py
   ```
   *Expected result: Benchmark prints theoretical reduction and throughput table cleanly.*

---

## SECTION 13 — DEFINITION OF DONE

- **Status:** **COMPLETE**
- **Justification:**
  - One canonical indexer interface with 100% tuple and attribute compatibility.
  - All 14 previous failures legitimately resolved.
  - 57/57 foveated grid tests and 100/100 repository tests pass deterministically.
  - Four rings, epsilon boundaries, origin, negative coordinates, and out-of-range behaviors verified.
  - Sparse representation preserved with zero memory overhead for empty space.
  - Mapping protocol integration verified.
  - Zero modifications to other team members' modules.

---

## SECTION 14 — FINAL HANDOFF MESSAGE

**READY FOR MERGE:** **YES**

**REQUIRED FOLLOW-UP:**
- Vedant can merge `feature/manashri-foveated-grid` into the main integration pipeline branch.
- Downstream `src/mapping/mapper.py` can directly consume `assign_points()` with zero adapter mismatch.

**COMMIT:** `11053279ca147ccad58fbe1df815607314b1d1e4`
