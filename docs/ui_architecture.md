# Autonomous Perception Control Center — UI Architecture & Specification

> **Module Owner:** Atharva (`src/visualization/`)  
> **Status:** Specification Freeze (Phase 2)  
> **Purpose:** Comprehensive architecture for the interactive Autonomous Perception Control Center for SIH 2026.

---

## 1. Vision & Core Principles

The visualization system is not a generic telemetry dashboard or static plotting tool. It is designed as a **mission-critical Autonomous Perception Control Center** for autonomous driving engineers, safety auditors, and hackathon evaluators.

### Fundamental Operating Principles:
1. **Real Data Ingestion Only:** The UI strictly consumes actual pipeline data (`PointCloudFrame`, `SemanticPointCloud`, `SemanticMap`, and runtime telemetry). Under no circumstances are mock or fabricated telemetry values displayed.
2. **Zero-Overhead Decoupling:** The visualization engine executes in a dedicated process or thread, consuming state snapshots via double-buffered memory or IPC (WebSockets / shared memory). It must never block or degrade the real-time LiDAR perception pipeline.
3. **Dual Operation Modes:**
   - **Live Pipeline Mode:** Streams directly from active sensor/ROS 2 input or running test suites.
   - **Temporal Playback Mode:** Scans, pauses, steps, and rewinds through prerecorded frame sequences (`.bin` or recorded run sessions) for detailed inspection.

---

## 2. The 12 Mission-Critical Display Views

The control center organizes into a cohesive multi-viewport layout supporting 12 specialized perception views:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AUTONOMOUS PERCEPTION CONTROL CENTER                            │
├────────────────────────────────┬───────────────────────────────┬───────────────────────┤
│ [VIEW 1] Live LiDAR Stream     │ [VIEW 2] Semantic 3D Point    │ [VIEW 7] Telemetry &  │
│ - Raw 3D point cloud           │   Cloud                       │   Performance Monitor │
│ - Intensity-colored points     │ - 8-class color map           │ - FPS counter (real)  │
│ - Ego-vehicle marker           │ - Dynamic obstacle highlights │ - Per-stage latency   │
│                                │                               │ - RAM / VRAM meter    │
├────────────────────────────────┼───────────────────────────────┼───────────────────────┤
│ [VIEW 3] 2.5D Elevation Map    │ [VIEW 4] Terrain Traversabil- │ [VIEW 8] Cell & Fovea │
│ - Continuous surface height    │   ity & Hazard Map            │   Inspector           │
│ - Top-down & isometric view    │ - Green: Drivable (slope<15°) │ - Hover cursor readout│
│ - Slope gradient vectors       │ - Orange: Curb warning        │ - Elevation, z_range  │
│                                │ - Red: Lethal step / Pothole  │ - Class distribution  │
├────────────────────────────────┼───────────────────────────────┼───────────────────────┤
│ [VIEW 5] Foveation Multi-Ring  │ [VIEW 6] Uniform vs. Foveated │ [VIEW 9] Semantic     │
│   Grid Topology                │   Comparative Side-by-Side    │   Confidence Heatmap  │
│ - Rings 0, 1, 2, 3 boundaries  │ - Left: 5cm Uniform Grid      │ - Softmax confidence  │
│ - Cell boundary tessellation   │ - Right: Foveated Multi-Ring  │ - Ambiguity highlights│
│ - Point count density colormap │ - Memory & compute delta      │                       │
├────────────────────────────────┼───────────────────────────────┼───────────────────────┤
│ [VIEW 10] Resolution Decision  │ [VIEW 11] Detected Obstacle & │ [VIEW 12] Temporal    │
│   Explainer                    │   Hazard Inventory            │   Playback Controller │
│ - Why cell was refined         │ - Curbs, potholes, obstacles  │ - Play / Pause / Step │
│ - Distance vs semantic trigger │ - Relative range & heading    │ - Timeline scrubbing  │
└────────────────────────────────┴───────────────────────────────┴───────────────────────┘
```

---

## 3. Viewport Specifications

### View 1: Live LiDAR Stream
- **Source:** `PointCloudFrame` from `src/preprocessing/`.
- **Renders:** Raw $(x, y, z)$ point cloud colored by calibrated intensity or range. Displays vehicle origin $(0, 0, 0)$ with an orientation triad.

### View 2: Semantic 3D Point Cloud
- **Source:** `SemanticPointCloud` from `src/perception/`.
- **Renders:** 3D points colored according to the 8 standard project semantic classes:
  - Drivable Ground: Purple (`#804080`)
  - Non-Drivable Terrain: Forest Green (`#006400`)
  - Vehicle: Deep Blue (`#00008E`)
  - Pedestrian: Crimson (`#DC143C`)
  - Cyclist: Bright Red (`#FF0000`)
  - Pole: Grey (`#999999`)
  - Wall/Building: Dark Charcoal (`#464646`)
  - Other Obstacle: Amber Orange (`#FAAA1E`)

### View 3: 2.5D Elevation Map
- **Source:** `SemanticMap` from `src/mapping/`.
- **Renders:** Surface height mesh with continuous colormap (turbo or viridis). Highlights elevation gradients and surface contours.

### View 4: Terrain Traversability & Hazard Map
- **Source:** Traversability analysis in `src/mapping/`.
- **Renders:**
  - **Drivable Surface:** Green tint ($< 15^\circ$ slope, roughness $< 0.05$).
  - **Curbs:** Yellow/Orange bounding lines indicating sharp step changes ($8\text{--}25\text{ cm}$).
  - **Potholes:** Flashing cyan/blue outlines for negative road depressions ($\le -5\text{ cm}$).
  - **Overhangs:** Dashed bounding volumes showing safe overhead vehicle clearance ($> 2.2\text{ m}$).

### View 5: Foveation Multi-Ring Grid Topology
- **Source:** `src/foveated_grid/`.
- **Renders:** Concentric ring boundaries at $10\text{ m}, 25\text{ m}, 50\text{ m}, 100\text{ m}$, overlaid with variable resolution grid wireframes ($5\text{ cm}, 10\text{ cm}, 25\text{ cm}, 50\text{ cm}$). Colormapped by point accumulation count.

### View 6: Uniform vs. Foveated Comparative Side-by-Side
- **Purpose:** Direct hackathon jury validation tool.
- **Renders:** Synchronized side-by-side view comparing a hypothetical uniform $5\text{ cm}$ grid (requiring $16\text{ million}$ cells over $100\text{ m}$) against our foveated multi-ring grid (requiring $\sim 650,000$ cells, a $96\%$ reduction in memory footprint). Displays active memory usage and update times side by side.

### View 7: Real-Time Performance Telemetry
- **Source:** `src/integration/` telemetry profiler.
- **Renders:** Real-time HUD showing:
  - System FPS (Frames Per Second).
  - Stage latency breakdown bar chart (Preprocessing $\rightarrow$ Inference $\rightarrow$ Grid Binning $\rightarrow$ Elevation Mapping $\rightarrow$ UI Render).
  - System RAM footprint (MB) and GPU VRAM footprint (MB).
  - Active point count and total populated grid cell count.

### View 8: Interactive Cell & Fovea Inspector
- **Interaction:** User clicks or hovers over any grid cell in the top-down map.
- **Renders:** Flyout panel detailing:
  - Coordinate: $(x_{\text{center}}, y_{\text{center}})$
  - Foveation Ring: Level ID and grid resolution $\Delta x$
  - Elevation Statistics: $z_{\text{surface}}, z_{\min}, z_{\max}, \sigma_z$
  - Dominant Class: Name, confidence, observation count
  - Traversability: Slope angle, roughness, hazard classification

### View 9: Semantic Confidence Heatmap
- **Source:** `SemanticPointCloud.confidence` & `GridCell.confidence`.
- **Renders:** Spatial heatmap highlighting areas of low prediction confidence (e.g. distant boundary obstacles or ambiguous terrain) in orange/red, signaling areas requiring caution or adaptive refinement.

### View 10: Resolution Decision Explainer
- **Purpose:** Explainability engine for adaptive refinement.
- **Renders:** Color codes cells by the rule that triggered their active resolution level:
  - Blue: Default distance-based foveation band.
  - Red: Semantic priority override (e.g. fine-grained pedestrian detection).
  - Yellow: Geometric uncertainty override (e.g. sharp slope change).

### View 11: Detected Obstacle & Hazard Inventory
- **Renders:** Tabular list of active critical hazards within $50\text{ m}$:
  - ID, Hazard Type (Curb, Pothole, Pedestrian, Vehicle), Distance, Relative Angle, Clearance Margin.

### View 12: Temporal Playback Controller
- **Interaction:** Floating playback bar at bottom of window.
- **Controls:** Play, Pause, Step Forward ($+1$ frame), Step Backward ($-1$ frame), Seek Slider, Playback Speed ($0.25\times, 0.5\times, 1.0\times, 2.0\times$).

---

## 4. Technical Implementation Stack

Atharva has two viable architectural implementation pathways:

### Option A: Modern Web-Based UI (Three.js / React / WebGL via WebSocket)
- **Advantages:** Cross-platform, runs on any laptop or browser without heavy local GUI library conflicts, hardware-accelerated WebGL point cloud rendering, responsive layout.
- **Architecture:** Lightweight local Python FastAPI/WebSocket server streaming binary serialization of `SemanticMap` snapshots to a React/Three.js frontend.

### Option B: High-Performance Python Native Desktop (VisPy / Open3D / Polyscope)
- **Advantages:** Direct zero-copy memory access to NumPy arrays without network serialization, high FPS on local GPU.
- **Architecture:** Python desktop event loop with PyQt/PySide6 controls and VisPy/OpenGL viewports.

*Recommendation for Atharva:* Both options conform to the data stream interfaces defined in `CONTRACTS.md`. Option A is recommended for hackathon demonstration clarity and ease of juror interaction.
