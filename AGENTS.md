# AGENTS.md — Autonomous Agent & Developer Collaboration Rules

## 1. Project Purpose & Scope
**Foveated Semantic 2.5D LiDAR Mapping for Autonomous Navigation** is an autonomous vehicle perception and mapping system designed to build real-time, memory-efficient 2.5D elevation and semantic representations from streaming 3D LiDAR point clouds using multi-resolution foveation.

---

## 2. Frozen System Architecture

```text
RAW LIDAR
    ↓
PREPROCESSING (Amulya)
    ↓
SEMANTIC PERCEPTION (Vedant)
    ↓
FOVEATED SPATIAL REPRESENTATION (Manashri)
    ↓
SEMANTIC 2.5D MAP (Heet)
    ↓
TERRAIN / TRAVERSABILITY ANALYSIS (Heet)
    ↓
TEMPORAL MAP UPDATE (Heet)
    ↓
REAL-TIME INTEGRATION (Atharva)
    ↓
VISUALIZATION (Atharva)
    ↓
BENCHMARKING (Himisha)
```

---

## 3. Frozen Coordinate Convention

```text
X = forward
Y = left
Z = up
```
* **Coordinate convention:** Right-handed FLU (Forward-Left-Up).
* **Spatial units:** Meters ($m$) for all linear dimensions, distances, and elevation.
* **Angular units:** Radians ($rad$).
* **Range:** $[0.0, 100.0]\,m$ operational envelope.

---

## 4. Module Ownership Boundaries (FROZEN)

| Developer | Primary Ownership Path | Core Responsibilities |
| :--- | :--- | :--- |
| **Amulya** | `src/preprocessing/` | LiDAR ingestion, NaN/range filtering, ego-noise removal, downsampling, `PointCloudFrame` |
| **Vedant** | `src/perception/` | Semantic segmentation models, class inference, confidence estimation, `SemanticPointCloud` |
| **Manashri** | `src/foveated_grid/` | Multi-resolution spatial partitioning, spatial indexing/hashing, Morton keys, `FoveatedSpatialGrid` |
| **Heet** | `src/mapping/` | 2.5D elevation aggregation, roughness, traversability evaluation, temporal update, `SemanticMap` |
| **Atharva** | `src/integration/`<br>`src/visualization/` | End-to-end pipeline runtime integration, latency telemetry, Autonomous Perception Control Center UI |
| **Himisha** | `src/evaluation/` | Synthetic scene generation, benchmark harness, Uniform vs. Foveated comparison, validation |

### Strict Isolation Rule
* **No ambiguous ownership.**
* **Never modify another developer's core module directory without formal agreement and verified contract compliance.**
* Shared types, contracts, configuration, and mocks reside in `src/common/` and require consensus for modifications.

---

## 5. Contract-First Development & Mocking

All six developers MUST build against the shared interfaces defined in `src/common/interfaces.py` and data types in `src/common/types.py`.

* Developers can work completely independently in parallel using the clean mocks provided in `src/common/mocks.py`.
* Upstream developers (e.g. Amulya, Vedant) provide standard output contracts.
* Downstream developers (e.g. Manashri, Heet, Atharva, Himisha) ingest contracts via interfaces without relying on unmerged implementations.

---

## 6. Central Configuration Rules

* **All architecture parameters must be loaded from `config/config.yaml` via `src.common.config.load_config()`.**
* **NEVER hardcode spatial thresholds, foveation radii, cell resolutions, or class IDs into module code.**
* **NEVER write machine-specific absolute paths into configuration files.** Always resolve relative paths from the project root.

### Foveation Levels (Frozen Defaults):
* **Level 0 (0–10 m):** $0.05\,m$ resolution
* **Level 1 (10–25 m):** $0.10\,m$ resolution
* **Level 2 (25–50 m):** $0.25\,m$ resolution
* **Level 3 (50–100 m):** $0.50\,m$ resolution

### Semantic Taxonomy (Frozen Classes):
* `0 = DRIVABLE_GROUND`
* `1 = NON_DRIVABLE_TERRAIN`
* `2 = VEHICLE`
* `3 = PEDESTRIAN`
* `4 = CYCLIST`
* `5 = POLE`
* `6 = WALL_BUILDING`
* `7 = OTHER_OBSTACLE`

---

## 7. Testing & Quality Requirements

* All new features must be accompanied by unit tests in `tests/unit/`.
* Test foveation boundaries explicitly (e.g. $r = 9.999$, $r = 10.000$, $r = 10.001$).
* Test negative coordinates ($X < 0$, $Y < 0$) and boundary transitions.
* Ensure deterministic behavior across repeated executions.

---

## 8. Zero-Fabrication Metric Policy

* **NO benchmark numbers, latency statistics, memory consumption metrics, or detection scores may be fabricated or hardcoded.**
* All performance comparisons between Uniform Grids and Foveated Grids must be produced by reproducible executions with verified timers (`time.perf_counter()`) and profilers.

---

## 9. Version Control Workflow Boundary

* **Git / GitHub management is outside the scope of Phase 2 setup.**
* Do **NOT** run `git init`, create remotes, commit, switch branches, or push during this setup task.
