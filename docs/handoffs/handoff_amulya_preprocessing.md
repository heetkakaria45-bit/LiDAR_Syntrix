# Preprocessing Module Engineering Handoff & Interface Specification

---

## SECTION 1 — OWNER

- **Name:** Amulya (Member 2)
- **Role:** Preprocessing Lead
- **Branch:** `feature/amulya-preprocessing`
- **Current HEAD:** `d7261ee`
- **Commit Hash:** `d7261eed0a9ec674bc6f014ea4962b9a1eb40954`

---

## SECTION 2 — RESPONSIBILITY & SCOPE BOUNDARIES

### What this workstream OWNS:
1. **Point Cloud Ingestion & Loaders (`src/preprocessing/loaders.py`):**
   - Ingesting SemanticKITTI / KITTI Velodyne `.bin` binary point clouds.
   - Wrapping in-memory NumPy arrays into standardized `PointCloudFrame` instances.
2. **Point Cloud Validation & Sanitization (`src/preprocessing/filters.py`):**
   - Vectorized detection and elimination of non-finite (NaN, +Inf, -Inf) coordinates and intensities.
   - Strict dimensional validation (`(N, 3)` for coordinates, `(N,)` for intensity).
3. **Spatial Filtering & Normalization (`src/preprocessing/filters.py`):**
   - Configurable Euclidean 3D range filtering with exact boundary preservation.
   - Uniform cubic voxel grid downsampling with arithmetic centroid and mean intensity aggregation.
   - Optional statistical (k-NN) and radius outlier removal.
   - Rigid body 4x4 coordinate transformations ($p' = p \cdot R^T + t$) into vehicle base frame.
4. **Pipeline Orchestration & Telemetry (`src/preprocessing/pipeline.py`):**
   - Config-driven pipeline execution (`LiDARPreprocessor`, `preprocess_frame`) and actual runtime metrics instrumentation (`PreprocessingMetrics`).
5. **Deterministic Synthetic Scene Generation (`src/preprocessing/synthetic.py`):**
   - Procedural generation of 7 canonical urban road geometries for offline testing.

### What this workstream DOES NOT OWN:
- **Ground Separation / Ground Plane Extraction:** Intentionally excluded from Preprocessing. Handled downstream in `src/mapping/` (Heet) and `src/perception/` (Vedant).
- **Perception Inference & Classification:** Handled in `src/perception/` (Vedant).
- **Foveated Spatial Grid Indexing:** Handled in `src/foveated_grid/` (Manashri).
- **2.5D Elevation Mapping & Hazard Detection:** Handled in `src/mapping/` (Heet).
- **Pipeline Integration, Web Server & Dashboard:** Handled in `src/integration/` and `frontend/` (Atharva).
- **Evaluation & Benchmarking Framework:** Handled in `src/evaluation/` (Himisha).
- **Shared Data Contracts:** Defined in `src/contracts.py` and `CONTRACTS.md`.

---

## SECTION 3 — TECHNICAL IMPLEMENTATION & ALGORITHMIC DETAILS

### 1. `validate_and_sanitize_points`
- **File:** [`src/preprocessing/filters.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/filters.py#L19-L68)
- **Exact Behavior:** Vectorized boolean filtering using NumPy `np.isfinite()`.
- **Invalid Point Handling:** Any point row containing non-numeric or non-finite values in $X$, $Y$, or $Z$ is stripped out.
- **NaN / Inf Handling:** Evaluates `finite_mask = np.all(np.isfinite(points), axis=1)`. If intensity is supplied, `finite_mask &= np.isfinite(intensity)`. Coordinates and intensity are sliced using the same mask, guaranteeing 100% 1:1 alignment between surviving points and intensities.
- **Malformed Input Handling:**
  - Validates `points.ndim == 2 and points.shape[1] == 3`; raises `ValueError` if 1D or shape is $(N, 4)$ or other.
  - Validates `intensity.ndim == 1 and intensity.shape[0] == points.shape[0]`; raises `ValueError` on mismatched lengths (including empty points with non-empty intensity).
  - Automatically converts nested lists / non-NumPy iterables to `float32` arrays.
  - Gracefully handles empty $(0, 3)$ inputs, returning empty $(0, 3)$ points and $(0,)$ intensity without exception.

### 2. Range Filtering
- **File:** [`src/preprocessing/filters.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/filters.py#L71-L129)
- **Minimum Range:** `min_range = 0.5m` (configurable).
- **Maximum Range:** `max_range = 100.0m` (configurable).
- **Boundary Behavior:** Calculates exact 3D Euclidean radial distance $r = \sqrt{x^2 + y^2 + z^2}$. Retains points satisfying $(r_{min} - \text{tol}) \le r \le (r_{max} + \text{tol})$ with floating-point tolerance $\text{tol} = 10^{-6}\text{m}$.
- **Negative Coordinate Handling:** Coordinate sign is never confused with radial distance; negative coordinates (e.g. $x = -5\text{m} \implies r = 5\text{m}$) are correctly retained. Points with $r < r_{min}$ (sensor origin self-reflection noise) and $r > r_{max}$ (beyond sensor sensing horizon) are dropped.
- **Validation:** Raises `ValueError` if `min_range < 0` or `min_range > max_range`.

### 3. Outlier Filtering
- **File:** [`src/preprocessing/filters.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/filters.py#L187-L308)
- **Statistical Outlier Removal (SOR):** Computes mean distance to $k$-nearest neighbors for each point ($k = 20$ default). Computes global mean $\mu$ and standard deviation $\sigma$. Points with mean neighbor distance $> \mu + \text{std\_ratio} \cdot \sigma$ (default $\text{std\_ratio} = 2.0$) are rejected. Implemented with vectorized chunked broadcasting ($2000$ points/chunk) to conserve memory.
- **Radius Outlier Removal (ROR):** Counts neighbors within search radius $r = 0.5\text{m}$. Points with fewer than `min_neighbors` ($5$ default) are rejected.

### 4. Voxel Grid Downsampling
- **File:** [`src/preprocessing/filters.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/filters.py#L131-L185)
- **Algorithm:** Partitions 3D continuous space into uniform cubic voxels of size `leaf_size` (default $0.05\text{m} = 5\text{cm}$). Computes integer grid coordinates $\lfloor p / \text{leaf\_size} \rfloor$, finds unique voxel bins via `np.unique`, and accumulates points into arithmetic centroids $\frac{1}{K}\sum_{i=1}^K p_i$ and average intensity $\frac{1}{K}\sum_{i=1}^K I_i$ using `np.add.at`.
- **Determinism:** Output order is determined by sorted unique voxel indices, producing 100% deterministic output.
- **Validation:** Raises `ValueError` if `leaf_size <= 0`.

### 5. Ground Separation Boundary
- **Status in Preprocessing:** Intentionally **not implemented** in Amulya's preprocessing module.
- **Rationale:** Ground extraction is part of the downstream 2.5D mapping and traversability responsibility (`src/mapping/` — Heet) and semantic segmentation (`src/perception/` — Vedant). Preprocessing deliberately preserves the full point cloud so downstream perception models can segment roads/curbs/potholes with complete vertical context.

### 6. KITTI / SemanticKITTI Ingestion Loader
- **File:** [`src/preprocessing/loaders.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/loaders.py#L22-L100)
- **Binary Format:** Ingests raw `.bin` files formatted as contiguous float32 4-tuples: `[x, y, z, remission/intensity]` (16 bytes per point).
- **Coordinate Convention:** KITTI Velodyne coordinate frame ($+X$ Forward, $+Y$ Left, $+Z$ Up in meters) matches the project standard directly.
- **Validation:**
  - Verifies file existence; raises `FileNotFoundError` if missing.
  - Verifies file byte length is a multiple of 16 bytes; raises `ValueError` on corrupted/truncated files.
  - Handles 0-byte empty files gracefully, returning empty `PointCloudFrame`.
  - Automatically executes `validate_and_sanitize_points()` when `sanitize=True`.

### 7. Deterministic Synthetic Scene Generator
- **File:** [`src/preprocessing/synthetic.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/synthetic.py#L24-L254)
- **Supported Geometries:**
  1. `flat_road`: Planar horizontal drivable surface (Class 0).
  2. `curb`: Drivable road with elevated $8\text{cm}$–$25\text{cm}$ sidewalk step (Class 1).
  3. `pothole`: Road with depressed circular hazard zone (Class 7).
  4. `slope`: Inclined ramp along forward axis ($10^\circ$ incline default).
  5. `overhang`: Road with overhead bridge slab at $z = 3.5\text{m}$ (Class 6).
  6. `wall`: Road bounded by vertical building facade at $y = 4.0\text{m}$ (Class 6).
  7. `urban`: Comprehensive multi-obstacle scene (road, sidewalk, vehicle, pedestrian, pole).
- **Repeatability:** Seeded PRNG (`np.random.default_rng(config.seed)`) guarantees identical point distributions across runs.

---

## SECTION 4 — DATA CONTRACT & DATA FLOW

### Data Flow Architecture:
```
[Raw LiDAR / KITTI .bin / In-Memory NumPy Arrays]
                     │
                     ▼
       validate_and_sanitize_points()
       - Drops NaN, +Inf, -Inf
       - Validates (N, 3) and (N,) shapes
       - Enforces float32 dtypes
                     │
                     ▼
              filter_by_range()
       - Clips to [0.5m, 100.0m] Euclidean radius
       - Preserves exact boundary points
       - Preserves valid negative coordinates
                     │
                     ▼
      remove_outliers_statistical() [Optional]
       - Filters isolated noise via k-NN distance
                     │
                     ▼
             voxel_downsample() [Optional]
       - Spatial cubic voxel grid binning
       - Arithmetic centroid & mean intensity
                     │
                     ▼
           transform_coordinates() [Optional]
       - Rigid body 4x4 matrix: p' = p @ R.T + t
                     │
                     ▼
     [Ground Processing Handoff to Downstream]
       - Complete point cloud preserved
                     │
                     ▼
     Standardized PointCloudFrame Output
       - (M, 3) float32 points
       - (M,) float32 intensity
       - Preserved timestamp, frame_id, sensor_pose
                     │
                     ▼
[Downstream Perception (Vedant) & Integration (Atharva)]
```

### Exact Output Contract (`PointCloudFrame`):
- `points`: `np.ndarray` of shape `(M, 3)`, `dtype=np.float32`, in meters.
- `intensity`: `Optional[np.ndarray]` of shape `(M,)`, `dtype=np.float32`.
- `timestamp`: `float` in seconds (preserved from input).
- `frame_id`: `str` (e.g. `"lidar_top"`, preserved from input).
- `sensor_pose`: `np.ndarray` of shape `(4, 4)`, `dtype=np.float64` (preserved from input).
- **Coordinate Convention:** $+X$ Forward, $+Y$ Left, $+Z$ Up, Origin at sensor center or vehicle base frame.

---

## SECTION 5 — FILES CHANGED

| File | Type | Description |
| :--- | :--- | :--- |
| [`src/preprocessing/filters.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/filters.py) | Modified | Reordered parameter validation in `validate_and_sanitize_points` to check intensity dimensions before empty-point check. |
| [`src/preprocessing/loaders.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/src/preprocessing/loaders.py) | Modified | Hardened `load_raw_points` to explicitly cast float64 inputs to float32 even when `sanitize=False`. |
| [`tests/preprocessing/test_preprocessing.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/tests/preprocessing/test_preprocessing.py) | Modified | Added 5 test suites covering non-finite intensity, extended bounds validation, pipeline determinism regression, coordinate transform metadata preservation, and YAML config instantiation. |
| [`tests/preprocessing/test_loaders.py`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/tests/preprocessing/test_loaders.py) | Modified | Added tests for non-finite KITTI binary sanitization and float64 conversion. |
| [`docs/handoffs/preprocessing_handoff.md`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/docs/handoffs/preprocessing_handoff.md) | New | Official module engineering handoff documentation. |
| [`docs/handoffs/handoff_amulya_preprocessing.md`](file:///c:/Users/Dell/OneDrive/Desktop/Syntrix_LiDAR/LiDAR_Syntrix/docs/handoffs/handoff_amulya_preprocessing.md) | New | Canonical handoff documentation aligned with repository convention. |

---

## SECTION 6 — TESTS & VERIFICATION RESULTS

### Preprocessing Unit Tests:
```bash
py -3 -m pytest tests/preprocessing/ -v
```
- **Result:** `32 passed in 1.76s`
- **Pass Count:** 32
- **Fail Count:** 0
- **Error Count:** 0

### Full Repository Test Suite:
```bash
py -3 -m pytest tests/ -v
```
- **Result:** `65 passed in 1.30s`
- **Pass Count:** 65
- **Fail Count:** 0
- **Error Count:** 0

---

## SECTION 7 — MANUAL VERIFICATION

1. **Synthetic Scene Preprocessing Run:**
   ```bash
   py -3 -c "from src.preprocessing import LiDARPreprocessor, generate_synthetic_scene; preprocessor = LiDARPreprocessor.from_config_file('configs/default_config.yaml'); frame, _ = generate_synthetic_scene(); out, m = preprocessor.preprocess(frame); print(f'Input: {m.input_points}, Output: {m.output_points}, Latency: {m.latency_ms:.2f}ms')"
   ```
   *Output:* Successfully executed without error, displaying measured latency and valid point reduction.
2. **KITTI Binary Corrupted File Test:**
   Generated binary with mock NaN/Inf floats; verified `load_kitti_bin(sanitize=True)` drops corrupted rows while preserving valid coordinates and intensities.
3. **Determinism Verification:**
   Preprocessed identical frame across multiple independent runs; confirmed `np.array_equal` on both coordinates and intensity.

---

## SECTION 8 — BENCHMARKS & PERFORMANCE CLAIMS

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

## SECTION 9 — ASSUMPTIONS & KNOWN LIMITATIONS

### Assumptions Downstream Perception Makes About Preprocessing:
1. **Clean Input:** All output points are strictly finite (`np.all(np.isfinite(points)) == True`), containing zero NaNs, +Infs, or -Infs.
2. **Range Conformance:** All points reside within the operational radial field $[0.5\text{m}, 100.0\text{m}]$ without out-of-range sensor noise.
3. **Data Type & Shape:** `points` is strictly a 2D NumPy array of shape `(N, 3)` with `dtype=np.float32`.
4. **Intensity Alignment:** If present, `intensity` is a 1D NumPy array of shape `(N,)` with `dtype=np.float32` aligned row-for-row with `points`.
5. **Ground Points Present:** Ground points are preserved in the cloud to allow downstream neural models and elevation mappers full geometric terrain structure.

### Remaining Preprocessing Risks / Limitations:
1. **SOR Computation on Dense Clouds:** Full k-NN statistical outlier removal on dense raw clouds (>50,000 points) uses chunked NumPy broadcasting which requires ~1.2GB transient memory and is computationally expensive on CPU. In 10Hz real-time pipelines, SOR should be disabled or run **after** voxel downsampling.
2. **Loader Formats:** Currently supports SemanticKITTI / KITTI `.bin` binary files and in-memory NumPy arrays. ROS2 bag, LAS, and PCD file loaders are deferred to future milestones.

---

## SECTION 10 — INTEGRATION REQUIREMENTS (FOR VEDANT & ATHARVA)

### Quick Integration Snippet:
```python
from src.contracts import PointCloudFrame
from src.preprocessing import (
    LiDARPreprocessor,
    PreprocessingConfig,
    load_kitti_bin,
    load_raw_points,
    preprocess_frame,
)

# 1. Config-driven initialization
preprocessor = LiDARPreprocessor.from_config_file("configs/default_config.yaml")

# 2. Ingest raw frame
raw_frame: PointCloudFrame = load_kitti_bin("data/kitti/000000.bin", frame_id="lidar_top")

# 3. Preprocess
processed_frame, metrics = preprocessor.preprocess(raw_frame)

# 4. Pass to downstream perception / mapping
# points = processed_frame.points        # (N, 3) float32
# intensity = processed_frame.intensity  # (N,) float32
```

---

## SECTION 11 — MERGE RISKS

- **Overwrite Risk:** `tests/preprocessing/test_preprocessing.py` on `feature/amulya-preprocessing` supersedes the 28-line placeholder on `origin/main` with the full 32-test suite.
- **Contract Impact:** Zero. `src/contracts.py` was untouched.
- **Config Impact:** Compatible with `configs/default_config.yaml`.

---

## SECTION 12 — HOW TO VERIFY AFTER MERGE

1. `git status` (verify clean tree)
2. `py -3 -m pytest tests/preprocessing/ -v` (32 passed)
3. `py -3 -m pytest tests/ -v` (65 passed)
4. Smoke test:
   ```bash
   py -3 -c "from src.preprocessing import LiDARPreprocessor, generate_synthetic_scene; p = LiDARPreprocessor.from_config_file('configs/default_config.yaml'); f, _ = generate_synthetic_scene(); out, m = p.preprocess(f); print(f'Passed: {m.output_points} points in {m.latency_ms:.2f}ms')"
   ```

---

## SECTION 13 — DEFINITION OF DONE

**Status: COMPLETE**

- All required algorithms implemented, tested, and verified.
- Frozen data contract strictly adhered to.
- Zero regressions across 65 repository-wide tests.

---

## SECTION 14 — FINAL HANDOFF MESSAGE

**READY FOR MERGE: YES**

**REQUIRED FOLLOW-UP:** None for Preprocessing. Vedant can merge `feature/amulya-preprocessing` directly into `main`.

**COMMIT:** `d7261eed0a9ec674bc6f014ea4962b9a1eb40954`
