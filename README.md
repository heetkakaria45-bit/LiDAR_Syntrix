# Foveated Semantic 2.5D LiDAR Mapping for Autonomous Navigation

[![Project Status: Initialized](https://img.shields.io/badge/status-foundation--initialized-blue.svg)](#current-project-status)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/hackathon-SIH%202026-orange.svg)](#)

> **Smart India Hackathon (SIH 2026)**  
> High-performance variable-resolution 2.5D elevation and semantic mapping from raw 3D LiDAR point clouds for real-time autonomous navigation.

---

## 1. What the Project Does

This system transforms raw 3D LiDAR point clouds into an adaptive, variable-resolution (foveated) 2.5D semantic elevation grid. The pipeline enables autonomous vehicles and mobile robots to:
- Detect fine-grained ground hazards (such as road curbs, speed bumps, and potholes) in the immediate driving corridor.
- Semantically classify surrounding static and dynamic objects (vehicles, pedestrians, cyclists, poles, and buildings).
- Maintain an accurate 2.5D elevation surface without forfeiting vertical obstacle and overhang data.
- Scale spatial processing efficiently out to long sensing distances (up to 100 meters) while keeping compute and memory budgets predictable for real-time operation.

---

## 2. Why Foveated Mapping is Needed

Autonomous perception systems face a fundamental trade-off:

1. **The Cost of Uniform 3D Processing:**  
   Raw 3D point clouds contain hundreds of thousands of points per frame. Maintaining a uniformly high-resolution 3D voxel grid or elevation map over a 100-meter radius leads to quadratic/cubic growth in memory footprint and latency.
2. **The Hazard of 2D Occupancy Grids:**  
   Collapsing point clouds into binary 2D occupancy grids forfeits height metrics. A vehicle cannot distinguish a driveable 2 cm road imperfection from a lethal 18 cm curb or open pothole, and overhanging tree branches or tunnels are flattened into impassable obstacles.
3. **The Foveated Solution:**  
   Human vision uses a fovea to observe the point of focus at peak acuity while allocating peripheral vision to broader awareness. Similarly, our foveated pipeline allocates high spatial resolution ($5\text{ cm}$) in the near-field ($0\text{--}10\text{ m}$) where collision hazards demand immediate micro-maneuvers, and gracefully transitions to coarser resolutions ($10\text{ cm}$, $25\text{ cm}$, $50\text{ cm}$) at greater distances ($10\text{--}100\text{ m}$).

---

## 3. System Architecture & Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                       RAW LIDAR INPUT                       │
│              (KITTI / nuScenes / Rosbag / PCD)              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 LIDAR PREPROCESSING MODULE                  │
│       Filtering • Downsampling • Coordinate Alignment       │
│                [src/preprocessing/ — Amulya]                │
└──────────────────────────────┬──────────────────────────────┘
                               │  PointCloudFrame (Nx3, intensity)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               SEMANTIC POINT-CLOUD PERCEPTION               │
│          Point-Level Segmentation & Class Inference         │
│                 [src/perception/ — Vedant]                  │
└──────────────────────────────┬──────────────────────────────┘
                               │  SemanticPointCloud (Nx3, class, conf)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FOVEATED HIERARCHICAL GRID                  │
│           Spatial Indexing • Multi-Ring Assignment          │
│               [src/foveated_grid/ — Manashri]               │
└──────────────────────────────┬──────────────────────────────┘
                               │  Multi-Resolution Cell Index
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 SEMANTIC 2.5D ELEVATION MAP                 │
│         Elevation Fusion • Traversability • Hazards         │
│                  [src/mapping/ — Heet]                      │
└──────────────────────────────┬──────────────────────────────┘
                               │  SemanticMap (2.5D cells + traversability)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             REAL-TIME INTEGRATION & PIPELINE                │
│         Orchestration • Latency & Memory Profiling          │
│                [src/integration/ — Atharva]                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│   VISUALIZATION & DASHBOARD │ │  EVALUATION & BENCHMARKING  │
│  Top-Down & 3D Map Renderer │ │  mIoU • RMSE • Latency/FPS  │
│[src/visualization/— Atharva]│ │ [src/evaluation/ — Himisha] │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 4. Team Structure & Ownership

Six developers maintain end-to-end ownership over their dedicated architectural modules:

| Team Member | Engineering Role | Core Module Path | Primary Scope |
| :--- | :--- | :--- | :--- |
| **Vedant** | Deep Learning Perception | `src/perception/` | Point-cloud semantic segmentation, model inference, confidence scores. |
| **Amulya** | LiDAR Preprocessing | `src/preprocessing/` | Dataset ingestion, coordinate transforms, outlier filtering, frame contracts. |
| **Manashri** | Foveated Grid Data Structure | `src/foveated_grid/` | Hierarchical variable-resolution rings, spatial indexing, boundary transitions. |
| **Heet** | 2.5D Semantic Mapping | `src/mapping/` | Elevation aggregation, occupancy, traversability, curb and pothole detection. |
| **Atharva** | Integration & Visualization | `src/integration/`<br>`src/visualization/` | Real-time orchestration, multithreading, latency profiling, interactive dashboard. |
| **Himisha** | Evaluation & Benchmarks | `src/evaluation/` | Quantitative benchmarks (mIoU, elevation RMSE, distance stratification, FPS). |

---

## 5. Repository Structure

```
LiDAR/
├── README.md                 # Project vision, architecture, and developer guide
├── AGENTS.md                 # Permanent engineering rules & ownership boundaries
├── CONTRACTS.md              # Shared interface schemas and data protocols
├── CONTRIBUTING.md           # Git branching, commit guidelines, and PR workflow
├── pyproject.toml            # Python packaging and pytest configuration
├── requirements.txt          # Foundational dependencies (numpy, pyyaml, pytest)
├── .gitignore                # Ignore caches, builds, datasets, and weights
│
├── configs/
│   └── default_config.yaml   # Configurable foveation ranges, classes, conventions
│
├── data/
│   └── .gitkeep              # Local dataset directory (ignored by git)
│
├── models/
│   └── .gitkeep              # Trained weights and ONNX models (ignored by git)
│
├── outputs/
│   └── .gitkeep              # Generated maps and benchmark outputs
│
├── docs/
│   └── handoffs/
│       └── template_handoff.md # Standard handoff template for module milestones
│
├── scripts/
│   └── run_smoke_tests.py    # Smoke test runner
│
├── src/
│   ├── __init__.py
│   ├── contracts.py          # Typed dataclass implementations of CONTRACTS.md
│   ├── preprocessing/        # Owner: Amulya
│   ├── perception/           # Owner: Vedant
│   ├── foveated_grid/        # Owner: Manashri
│   ├── mapping/              # Owner: Heet
│   ├── integration/          # Owner: Atharva
│   ├── visualization/        # Owner: Atharva
│   └── evaluation/           # Owner: Himisha
│
└── tests/
    ├── __init__.py
    ├── test_imports.py       # Verifies clean module package discovery
    ├── test_config.py        # Verifies configuration hierarchy and validation
    ├── test_contracts.py     # Verifies data contract schemas and invariants
    ├── preprocessing/        # Tests for Amulya's module
    ├── perception/           # Tests for Vedant's module
    ├── foveated_grid/        # Tests for Manashri's module
    ├── mapping/              # Tests for Heet's module
    ├── integration/          # Tests for Atharva's module
    └── evaluation/           # Tests for Himisha's module
```

---

## 6. Setup Instructions

### Prerequisites
- Python 3.10 or higher
- Git

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/heetkakaria45-bit/LiDAR_Syntrix.git
cd LiDAR_Syntrix

# 2. Create and activate a clean virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Install foundational dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install the package in editable development mode
pip install -e .
```

---

## 7. Git Branches & Worktrees

Each developer works on their dedicated feature branch. **Direct pushes to `main` are blocked.**

### Dedicated Branches
- `feature/vedant-perception`
- `feature/amulya-preprocessing`
- `feature/manashri-foveated-grid`
- `feature/heet-mapping`
- `feature/atharva-integration`
- `feature/himisha-evaluation`

### Creating Your Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/<your-name>-<your-module>
```

### Using Git Worktrees for Parallel Development
If multiple teammates or local testing agents require separate checkouts simultaneously:
```bash
git worktree add ../LiDAR-foveated-grid feature/manashri-foveated-grid
```

---

## 8. Running Tests

Run the test suite via `pytest`:
```bash
pytest tests/ -v
```

Or run the self-contained smoke test runner:
```bash
python scripts/run_smoke_tests.py
```

---

## 9. Current Project Status

- **Phase:** Foundation Initialized (Milestone 0).
- **Completed:**
  - Shared repository skeleton and module boundaries established.
  - Interface contracts codified in [CONTRACTS.md](CONTRACTS.md) and [src/contracts.py](src/contracts.py).
  - Configurable foveation hierarchy defined in [configs/default_config.yaml](configs/default_config.yaml).
  - Engineering constraints, module boundaries, and benchmark honesty rules codified in [AGENTS.md](AGENTS.md).
  - Package discovery, test infrastructure, and smoke tests implemented and validated.
- **In Progress:** Individual team members commencing development on their respective feature branches.
- *Note:* Performance benchmarks (FPS, latency, mIoU) will be published only after Himisha's evaluation pipeline executes on physical sensor data. No speculative numbers are reported.
