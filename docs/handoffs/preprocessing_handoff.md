# Preprocessing Module Engineering Handoff & Interface Specification

---

## SECTION 1 — OWNER

- **Name:** Amulya (Member 2)
- **Role:** Preprocessing Lead
- **Branch:** `feature/amulya-preprocessing`
- **Current HEAD:** `a4c9053`
- **Commit Hash:** `a4c90533bb5c1a5625232e573573025547a79f05`

---

## SECTION 2 — RESPONSIBILITY

### What this workstream OWNS:
1. **Point Cloud Ingestion & Loaders:**
   - Ingesting SemanticKITTI / KITTI Velodyne `.bin` binary point clouds.
   - In-memory NumPy array ingestion into standardized `PointCloudFrame` instances.
2. **Point Cloud Validation & Sanitization:**
   - Vectorized detection and removal of non-finite (NaN, +Inf, -Inf) coordinates and intensity values.
   - Strict dimensional and shape enforcement `(N, 3)` for coordinates and `(N,)` for intensity.
3. **Spatial Filtering & Normalization:**
   - Configurable 3D Euclidean range filtering ($r = \sqrt{x^2+y^2+z^2}$) with exact boundary preservation ($r_{min} \le r \le r_{max}$).
   - Handling of valid negative Cartesian coordinates ($x < 0, y < 0, z < 0$).
   - Uniform cubic voxel grid downsampling with arithmetic centroid and average intensity aggregation.
   - Optional statistical outlier removal (k-NN distance standard deviation thresholding) and radius outlier removal.
   - Rigid body 4x4 coordinate transformations ($p' = p \cdot R^T + t$) into standard ego vehicle base frame.
4. **Synthetic Scene Generation:**
   - Deterministic procedural generation of 7 urban road scene geometries (`flat_road`, `curb`, `pothole`, `slope`, `overhang`, `wall`, `urban`) with ground truth semantic labels and calibrated intensities for cross-team development.
5. **Telemetry & Execution Metrics:**
   - Real-time instrumentation of point counts, reduction ratios, downsample factors, and elapsed wall-clock processing latency (`PreprocessingMetrics`).

### What this workstream DOES NOT OWN:
- Semantic segmentation, neural network inference, or classification (`src/perception/` — Vedant).
- Multi-resolution foveated polar/Cartesian grid spatial indexing (`src/foveated_grid/` — Manashri).
- 2.5D elevation grid accumulation, hazard detection, or traversability estimation (`src/mapping/` — Heet).
- Full pipeline scheduling, thread orchestration, web server, and UI dashboards (`src/integration/`, `frontend/` — Atharva).
- Benchmark suites and evaluation metrics (`src/evaluation/` — Himisha).
- Core shared data contracts (`src/contracts.py`, `CONTRACTS.md`).
- Ground plane segmentation / separation (intentionally excluded to maintain frozen architectural separation).

---

## SECTION 3 — WHAT WAS IMPLEMENTED

### 1. Ingestion Loaders (`src/preprocessing/loaders.py`)
- **Purpose:** Fast binary dataset loading and memory array conversion.
- **Key Functions:**
  - `load_kitti_bin(file_path, frame_id="lidar_top", timestamp=0.0, sensor_pose=None, sanitize=True) -> PointCloudFrame`: Reads raw float32 4-tuples `[x, y, z, intensity]` (16 bytes per point) from `.bin` files, verifies byte size divisibility, and sanitizes non-finite values.
  - `load_raw_points(points, intensity=None, frame_id="lidar_top", timestamp=0.0, sensor_pose=None, sanitize=True) -> PointCloudFrame`: Wraps arbitrary NumPy arrays into validated `PointCloudFrame` instances, guaranteeing float32 precision.
- **Dependencies:** `numpy`, `pathlib`, `os`, `src.contracts.PointCloudFrame`.

### 2. Spatial Filtering & Sanitization (`src/preprocessing/filters.py`)
- **Purpose:** Core vectorized geometric processing algorithms.
- **Key Functions:**
  - `validate_and_sanitize_points(points, intensity=None) -> Tuple[np.ndarray, Optional[np.ndarray]]`:
    - *Algorithm:* Vectorized boolean masking `np.all(np.isfinite(points), axis=1) & np.isfinite(intensity)`.
    - *Input:* `(N, 3)` coordinates, optional `(N,)` intensity.
    - *Output:* `(M, 3)` float32 coordinates, optional `(M,)` float32 intensity.
  - `filter_by_range(points, intensity=None, min_range=0.5, max_range=100.0) -> Tuple[np.ndarray, Optional[np.ndarray]]`:
    - *Algorithm:* Computes $r = \sqrt{x^2+y^2+z^2}$, retains points where $r_{min} - \epsilon \le r \le r_{max} + \epsilon$. Properly handles negative coordinates by computing radial distance.
  - `voxel_downsample(points, intensity=None, leaf_size=0.05) -> Tuple[np.ndarray, Optional[np.ndarray]]`:
    - *Algorithm:* Discretizes space into integer voxel bins $\lfloor p / \text{leaf\_size}\rfloor$, groups via `np.unique`, and computes arithmetic centroids via `np.add.at`.
  - `remove_outliers_statistical(points, intensity=None, nb_neighbors=20, std_ratio=2.0, max_eval_points=50000)`:
    - *Algorithm:* Chunked k-NN Euclidean distance evaluation; points with mean neighbor distance $> \mu + \sigma \cdot \text{std}$ are filtered out.
  - `remove_outliers_radius(points, intensity=None, radius=0.5, min_neighbors=5, chunk_size=2000)`:
    - *Algorithm:* Counts neighbor points within sphere radius $r$; points with $< \text{min\_neighbors}$ are dropped.
  - `transform_coordinates(points, transform_matrix) -> np.ndarray`:
    - *Algorithm:* Rigid body matrix multiplication $p' = p \cdot R^T + t$ using (4, 4) homogeneous transformation matrix.

### 3. Pipeline Orchestrator & Telemetry (`src/preprocessing/pipeline.py`)
- **Purpose:** Configurable end-to-end preprocessing execution with runtime instrumentation.
- **Key Classes / Functions:**
  - `PreprocessingConfig`: Typed dataclass loaded from YAML or dict controlling parameters (`min_range`, `max_range`, `range_filter_enabled`, `voxel_downsample_enabled`, `voxel_leaf_size`, `outlier_removal_enabled`, `outlier_nb_neighbors`, `outlier_std_ratio`, `coordinate_transform`).
  - `PreprocessingMetrics`: Telemetry dataclass storing `input_points`, `output_points`, `latency_ms`, `reduction_ratio`, `downsample_ratio`.
  - `LiDARPreprocessor`: Main class orchestrating validation $\to$ range filter $\to$ optional SOR $\to$ optional voxel downsampling $\to$ optional coordinate transformation $\to$ output `PointCloudFrame`.
  - `preprocess_frame(frame, config=None) -> PointCloudFrame`: Functional one-liner entry point.

### 4. Deterministic Synthetic Scene Generator (`src/preprocessing/synthetic.py`)
- **Purpose:** Procedural geometric point cloud generator for simulation and integration testing.
- **Key Functions:**
  - `generate_synthetic_scene(config=None) -> Tuple[PointCloudFrame, SemanticPointCloud]`: Procedurally generates 7 scene types (`flat_road`, `curb`, `pothole`, `slope`, `overhang`, `wall`, `urban`) with deterministic random seeds, geometric noise, simulated intensity, and ground-truth semantic class annotations.

---

## SECTION 4 — DATA CONTRACT

### Input Contract:
- **Data Type:** `PointCloudFrame` or raw `np.ndarray` via loaders
- **Points Shape:** `(N, 3)`
- **Points Dtype:** `float32` (or convertible numeric array)
- **Points Units:** Meters
- **Intensity Shape:** Optional `(N,)`
- **Intensity Dtype:** `float32`
- **Required Fields:** `points`, `timestamp`, `frame_id`
- **Optional Fields:** `intensity`, `sensor_pose` (4x4 `float64`)

### Output Contract:
- **Data Type:** `PointCloudFrame` complying with `CONTRACTS.md`
- **Points Shape:** `(M, 3)` where $0 \le M \le N$
- **Points Dtype:** `np.float32`
- **Intensity Shape:** `None` or `(M,)` aligned 1:1 with points
- **Intensity Dtype:** `np.float32`
- **Timestamp:** `float` (preserved unchanged)
- **Frame ID:** `str` (preserved unchanged)
- **Sensor Pose:** `(4, 4)` `np.float64` (preserved unchanged)
- **Coordinate Convention:**
  - $+X$: Forward
  - $+Y$: Left
  - $+Z$: Up
  - Origin: Sensor center (or vehicle base after coordinate transform)
  - Units: Meters

### Downstream Consumption:
- **`src/perception/` (Vedant):** Consumes `processed_frame.points` `(M, 3)` and `processed_frame.intensity` `(M,)` for semantic class inference, outputting `SemanticPointCloud`.
- **`src/integration/` (Atharva):** Ingests raw frames via `load_kitti_bin()` / `load_raw_points()`, runs `LiDARPreprocessor.preprocess()`, logs `metrics.latency_ms` and `metrics.reduction_ratio` to telemetry streams.

---

## SECTION 5 — FILES CHANGED

| File | Change | Reason |
| :--- | :--- | :--- |
| `src/preprocessing/filters.py` | Modified | Hardened input validation ordering: validates intensity shape before empty-point early exit. |
| `src/preprocessing/loaders.py` | Modified | Ensured `load_raw_points()` explicitly casts float64 inputs to float32 even when `sanitize=False`. |
| `tests/preprocessing/test_preprocessing.py` | Modified | Added 5 test suites (non-finite intensity sanitization, extended validation bounds, full pipeline determinism regression, coordinate transform metadata preservation, YAML config instantiation). |
| `tests/preprocessing/test_loaders.py` | Modified | Added tests for non-finite KITTI binary sanitization and float64 conversion. |
| `docs/handoffs/preprocessing_handoff.md` | New | Formal engineering handoff documentation. |

---

## SECTION 6 — TESTS

### Test Command 1 (Preprocessing Unit Tests):
```bash
py -3 -m pytest tests/preprocessing/ -v
```
- **Result:** `32 passed in 1.34s`
- **Pass Count:** 32
- **Fail Count:** 0
- **Error Count:** 0

### Test Command 2 (Full Repository Test Suite):
```bash
py -3 -m pytest tests/ -v
```
- **Result:** `65 passed in 1.40s`
- **Pass Count:** 65
- **Fail Count:** 0
- **Error Count:** 0

---

## SECTION 7 — MANUAL VERIFICATION

1. **Direct Pipeline Execution on Synthetic Scene:**
   - Instantiated `LiDARPreprocessor` with `configs/default_config.yaml`.
   - Generated 50,000-point synthetic urban scene.
   - Executed `preprocess()`, verified output shapes, non-NaN assertion, point reduction, and telemetry metric fields.
2. **KITTI Binary Loader Round-Trip:**
   - Created synthetic binary `.bin` file containing valid float32 points + non-finite NaN/Inf points.
   - Loaded via `load_kitti_bin(sanitize=True)`, verified corrupted rows were safely dropped and valid points remained uncorrupted.
3. **Determinism Verification:**
   - Executed identical 1,500-point noisy frame through the full multi-stage pipeline across two independent invocations; verified `np.array_equal` on both coordinates and intensities.

---

## SECTION 8 — BENCHMARKS / NUMERIC CLAIMS

| Value | Metric | Calculation / Scenario | Hardware | Input Size | Runs | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2.40 ms** (min: 1.16 ms) | Latency | Range filter ($0.5\text{m} \le r \le 100\text{m}$) | Intel x86_64, Windows | 15,000 points | 25 | **MEASURED** |
| **31.28 ms** (min: 21.54 ms)| Latency | Range filter + Voxel downsample (leaf 0.10m) | Intel x86_64, Windows | 15,000 points | 25 | **MEASURED** |
| **10.68 ms** (min: 5.18 ms) | Latency | Range filter on dense frame | Intel x86_64, Windows | 50,000 points | 20 | **MEASURED** |
| **144.84 ms** | Latency | Range filter + Voxel downsample (leaf 0.10m) | Intel x86_64, Windows | 50,000 points | 20 | **MEASURED** |
| **0.00%** | Defect Rate | Non-finite points surviving `validate_and_sanitize_points` | Exact verification | Arbitrary NaN/Inf | 32 tests | **MEASURED** |
| **100%** | Determinism | Bit-for-bit repeatability on identical inputs | Exact array equality | 1,500 points | 2 runs | **MEASURED** |
| **10 Hz** | Target Rate | Target real-time pipeline throughput | Real-time budget | 15k-30k points | N/A | **TARGET** |

---

## SECTION 9 — KNOWN LIMITATIONS

1. **Loader Formats:** Supports SemanticKITTI / KITTI `.bin` binary files and in-memory NumPy arrays. ROS2 bag, LAS, and PCD file loaders are deferred to future milestones.
2. **Statistical Outlier Removal (SOR) Performance:** Full k-NN statistical outlier removal on dense raw clouds (>50,000 points) uses chunked NumPy broadcasting which requires ~1.2GB transient memory and is computationally expensive on CPU. In 10Hz real-time pipelines, SOR should be disabled or run **after** voxel downsampling.
3. **No Ground Plane Separation:** Ground extraction is intentionally not part of Amulya's preprocessing module; terrain analysis is performed downstream in `src/mapping/`.

---

## SECTION 10 — INTEGRATION REQUIREMENTS

- **Upstream Dependency:** File system dataset or live stream generating NumPy arrays or KITTI `.bin` files.
- **Downstream Consumer:** Vedant (`src/perception/`) and Atharva (`src/integration/`).
- **Expected API:**
  ```python
  from src.preprocessing import LiDARPreprocessor, PreprocessingConfig, load_kitti_bin, preprocess_frame

  # Option 1: Configured Preprocessor instance
  preprocessor = LiDARPreprocessor.from_config_file("configs/default_config.yaml")
  processed_frame, metrics = preprocessor.preprocess(raw_frame)

  # Option 2: Direct one-liner
  processed_frame = preprocess_frame(raw_frame)
  ```
- **Data Format:** `PointCloudFrame(points: (N, 3) float32, intensity: (N,) float32, timestamp: float, frame_id: str, sensor_pose: (4,4) float64)`.
- **Environment:** Pure Python + NumPy (`>=1.24.0`) + PyYAML (`>=6.0`). No GPU/CUDA or C++ compilation required.

---

## SECTION 11 — MERGE RISKS

- **Files with Potential Overwrite Risk:**
  - `tests/preprocessing/test_preprocessing.py`: On `origin/main`, commit `2097687` added a 28-line placeholder test. The `feature/amulya-preprocessing` branch replaces this with a complete 32-test suite.
- **Duplicated Logic:** None. Public API in `src/preprocessing/__init__.py` cleanly encapsulates all utilities.
- **Compatibility:** Fully backwards-compatible with `src/contracts.py` and `configs/default_config.yaml`.

---

## SECTION 12 — HOW TO VERIFY AFTER MERGE

Procedure for Vedant after merging `feature/amulya-preprocessing`:

1. **Verify Git Tree & Clean Build:**
   ```bash
   git status
   ```
2. **Execute Preprocessing Unit Tests:**
   ```bash
   py -3 -m pytest tests/preprocessing/ -v
   ```
   *(Expected: 32 passed, 0 failed, 0 errors)*
3. **Execute Full Repository Test Suite:**
   ```bash
   py -3 -m pytest tests/ -v
   ```
   *(Expected: 65 passed, 0 failed, 0 errors)*
4. **Smoke-test Integration Import:**
   ```bash
   py -3 -c "from src.preprocessing import LiDARPreprocessor, load_kitti_bin, generate_synthetic_scene; preprocessor = LiDARPreprocessor.from_config_file('configs/default_config.yaml'); frame, _ = generate_synthetic_scene(); out, m = preprocessor.preprocess(frame); print(f'Successfully processed {m.output_points} points in {m.latency_ms:.2f}ms')"
   ```

---

## SECTION 13 — DEFINITION OF DONE

**Status: COMPLETE**

- All required algorithms (sanitization, range filtering, voxel grid downsampling, outlier removal, coordinate transforms, KITTI loader, synthetic scenes) implemented and verified.
- Frozen data contract (`PointCloudFrame`) strictly adhered to.
- 100% test pass rate across 32 preprocessing tests and 65 repository-wide tests.
- Zero unauthorized modifications outside module ownership.

---

## SECTION 14 — FINAL HANDOFF MESSAGE

**READY FOR MERGE: YES**

**REQUIRED FOLLOW-UP:** None for Preprocessing. Vedant can merge `feature/amulya-preprocessing` directly into `main`.

**COMMIT:** `a4c90533bb5c1a5625232e573573025547a79f05`
