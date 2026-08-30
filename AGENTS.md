# Engineering Guidelines & Agent Rules

> **Applicability:** Mandatory for all human developers, pair programming sessions, and AI coding agents operating on this repository.

---

## 1. Project Purpose & Vision

The objective of **Foveated Semantic 2.5D LiDAR Mapping for Autonomous Navigation** (SIH 2026) is to solve the computational and memory bottlenecks of 3D autonomous perception:
- Raw 3D point clouds provide high geometric fidelity but require excessive compute and bandwidth to process and store uniformly across long distances.
- Traditional 2D occupancy grids forfeit height context required to detect critical hazards such as road curbs, potholes, step changes, and overhanging barriers.
- **Our Solution:** A variable-resolution, foveated semantic 2.5D elevation map that allocates millimeter/centimeter-level resolution in the immediate near-field of the vehicle (0–10m) while gracefully coarsening representation density with increasing distance (up to 100m).

---

## 2. System Architecture

```
RAW LIDAR (PCD/BIN/ROS2)
         ↓
LIDAR PREPROCESSING (src/preprocessing/ — Amulya)
         ↓  [PointCloudFrame]
SEMANTIC POINT CLOUD PERCEPTION (src/perception/ — Vedant)
         ↓  [SemanticPointCloud]
FOVEATED VARIABLE-RESOLUTION GRID (src/foveated_grid/ — Manashri)
         ↓  [Spatial Multi-Ring Index]
SEMANTIC 2.5D ELEVATION MAPPING (src/mapping/ — Heet)
         ↓  [SemanticMap with Traversability]
REAL-TIME INTEGRATION & ORCHESTRATION (src/integration/ — Atharva)
    ↙                                     ↘
VISUALIZATION (src/visualization/ — Atharva)   BENCHMARKING (src/evaluation/ — Himisha)
```

---

## 3. Team Roles & Strict Module Ownership

Each developer and AI assistant acting on their behalf **must stay strictly within their assigned module**.

| Team Member | Domain / Specialty | Module Path | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **Vedant** | Deep Learning / 3D Perception | `src/perception/`<br>`tests/perception/` | Point cloud semantic segmentation, inference pipelines, class predictions, confidence estimation, model compression. |
| **Amulya** | LiDAR Preprocessing & Datasets | `src/preprocessing/`<br>`tests/preprocessing/` | Dataset ingestion (SemanticKITTI, nuScenes, custom PCD), filtering, downsampling, coordinate transformations, `PointCloudFrame` creation. |
| **Manashri** | Foveated Grid & Spatial Structures | `src/foveated_grid/`<br>`tests/foveated_grid/` | Multi-ring hierarchical data structure, spatial indexing, high-speed point-to-cell assignment, resolution boundaries, cache efficiency. |
| **Heet** | 2.5D Mapping & Traversability | `src/mapping/`<br>`tests/mapping/` | Elevation aggregation (min/max/mean), semantic label fusion, occupancy estimation, terrain traversability, curb and pothole hazard detection. |
| **Atharva** | Integration, Optimization & UI | `src/integration/`<br>`src/visualization/`<br>`tests/integration/` | End-to-end pipeline wiring, runtime profiling, multithreading, real-time GUI/dashboard, top-down and 3D point cloud/elevation rendering. |
| **Himisha** | Evaluation & Benchmarking | `src/evaluation/`<br>`tests/evaluation/` | Quantitative benchmarks: mIoU, precision, recall, elevation RMSE, distance-binned analysis, FPS, latency, memory footprint, uniform vs. foveated studies. |

### The Golden Rule of Ownership
> **NO CROSS-MODULE REWRITES:** No developer or AI agent shall unilaterally rewrite, delete, or re-architect another developer's module. If an interface update is required, follow the RFC process defined in [CONTRACTS.md](CONTRACTS.md) and coordinate with the module owner.

---

## 4. Coding Conventions

1. **Language & Version:** Python 3.10+ standard.
2. **Type Annotations:** All functions, methods, and class definitions must include comprehensive PEP 484 type hints.
3. **Documentation:** Every public class and function must include a docstring detailing inputs, outputs, exceptions, and coordinate conventions.
4. **Style Standard:** Follow PEP 8 guidelines. Line length is capped at 100 characters.
5. **No Hard-Coding:** Never hard-code grid sizes, foveation ranges, thresholds, or class IDs in module logic. All constants must be ingested from [configs/default_config.yaml](configs/default_config.yaml) or passed as parameters.

---

## 5. Interface & Contract Integrity

1. **Single Source of Truth:** All data exchange across module boundaries must conform to [CONTRACTS.md](CONTRACTS.md) and [src/contracts.py](src/contracts.py).
2. **Contract Immutability:** Do not rename fields or modify expected array dimensions without an approved RFC.
3. **Coordinate Systems:** Always assume $X = \text{forward}$, $Y = \text{left}$, $Z = \text{up}$ in meters. If input data is in a different frame, `src/preprocessing/` must transform it before handoff.

---

## 6. Dependency & Environment Rules

1. **Lightweight Baseline:** Core repo dependencies remain strictly lightweight (`numpy`, `pyyaml`, `pytest`).
2. **Modular Optional Dependencies:** Heavy, hardware-locked dependencies (e.g. `torch`, `spconv`, `open3d`, `cupy`, `tensorrt`) must be guarded and imported optionally so that unit tests, preprocessing, and spatial indexing modules can be developed and tested on any platform without requiring a high-end GPU.
3. **Virtual Environment:** Always develop inside a virtual environment (`.venv`). Do not install packages globally.

---

## 7. Git & Collaboration Rules

1. **Main Branch Protection:** `main` is protected. No direct commits to `main`.
2. **Feature Branching:** Every member works on their dedicated feature branch:
   - `feature/vedant-perception`
   - `feature/amulya-preprocessing`
   - `feature/manashri-foveated-grid`
   - `feature/heet-mapping`
   - `feature/atharva-integration`
   - `feature/himisha-evaluation`
3. **Conventional Commits:** Use standard semantic commit prefixes:
   - `feat:` new functional capability
   - `fix:` bug fix
   - `test:` test additions or fixes
   - `docs:` documentation updates
   - `refactor:` code reorganization without functional changes
4. **Clean Git History:** Never commit raw dataset files (`.bin`, `.pcd`, `.las`), trained weights (`.pth`, `.onnx`), or temporary runtime outputs.

---

## 8. Testing Requirements

1. **Unit Testing:** Every feature added to a module must be accompanied by unit tests in the corresponding `tests/<module>/` directory.
2. **Zero Failures on Merge:** Pull requests must pass all tests before being merged:
   ```bash
   pytest tests/ -v
   ```
3. **Determinism:** Tests must be deterministic and run without requiring external cloud access or proprietary datasets. Mock fixtures or synthetic geometric point clouds should be used for testing.

---

## 9. Performance Measurement & Prohibition on Fabricated Results

> [!CAUTION]
> **STRICT PROHIBITION ON FABRICATED BENCHMARKS:**
> Under no circumstances may any developer or AI assistant invent, estimate without attribution, or fabricate performance statistics (such as "achieved 45 FPS", "92.4% mIoU", or "60% memory savings") in commit messages, documentation, or benchmark reports.
>
> All reported numbers must:
> 1. Originate from actual automated test runs recorded by `src/evaluation/`.
> 2. Document the exact hardware specification (CPU, GPU, RAM) and dataset split used.
> 3. Be reproducible by running the evaluation scripts.
