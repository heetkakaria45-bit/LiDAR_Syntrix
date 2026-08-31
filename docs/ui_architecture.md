# Autonomous Perception Control Center — UI Architecture

## 1. Overview & Architectural Role

The **Autonomous Perception Control Center** (owned by **Atharva**, `src/visualization/`) provides real-time visualization, inspection, and diagnostic controls for the foveated 2.5D semantic mapping system.

It is designed to consume **real system outputs** (`SemanticMap`, `PointCloudFrame`, `TelemetryMetrics`) and support both live sensor streams and prerecorded dataset playback.

```text
+-------------------------------------------------------------------------------+
| AUTONOMOUS PERCEPTION CONTROL CENTER (12 Specialized Diagnostic Views)         |
+---------------------------------------+---------------------------------------+
|  Top Left: 3D/2.5D Map Viewport       |  Top Right: Telemetry & Inspector     |
|  - Live LiDAR Points                  |  - Real-time Stage Latency (ms)       |
|  - Semantic Classification Layer      |  - FPS / Throughput Meter             |
|  - Elevation Heatmap (Z-gradient)     |  - Host RAM / GPU VRAM Usage          |
|  - Traversability / Navigation Cost   |  - Foveation Compression Ratio        |
|  - Foveation Zone Boundaries          |  - Point Count vs Cell Count          |
+---------------------------------------+---------------------------------------+
|  Bottom Left: Multi-Layer Diagnostics |  Bottom Right: Cell/Fovea Inspector   |
|  - Uniform vs Foveated Comparison     |  - Selected Cell (x, y, elevation)    |
|  - Resolution-Decision Explanation    |  - Roughness / Step Height / Slope    |
|  - Semantic Confidence Map            |  - Class Probability Distribution     |
|  - Detected Object Bounding Boxes     |  - Temporal Playback Scrubber         |
+---------------------------------------+---------------------------------------+
```

---

## 2. The 12 Functional Viewing Modes

| # | Viewing Mode | Description & Visual Representation |
| :---: | :--- | :--- |
| **1** | **Live LiDAR View** | Direct 3D point cloud colored by raw sensor return intensity or height $Z$. |
| **2** | **Semantic View** | Point cloud and 2.5D cells colored by dominant semantic class ID (0..7) using frozen palette. |
| **3** | **Elevation View** | Continuous color gradient representing estimated ground elevation $Z$ ($min\_z$ to $max\_z$). |
| **4** | **Traversability View** | Green-Yellow-Red navigation cost heatmap highlighting drivable vs. lethal obstacles. |
| **5** | **Foveation View** | Concentric radial zone overlays ($0..10m, 10..25m, 25..50m, 50..100m$) with cell grid outlines. |
| **6** | **Uniform vs. Foveated View** | Split-screen or toggle comparison displaying cell density reduction and boundary transitions. |
| **7** | **Performance Telemetry** | Real-time line graphs showing per-stage latency ($t_{prep}, t_{infer}, t_{map}$), FPS, and RAM. |
| **8** | **Cell / Fovea Inspector** | Interactive mouse hover/click revealing detailed `GridCell` metadata in a sidebar panel. |
| **9** | **Semantic Confidence** | Visual confidence heatmap showing model classification certainty ($0.0$ red to $1.0$ blue). |
| **10** | **Resolution Explanation** | Explains why a specific cell resolution was selected (distance rule vs. adaptive semantic boost). |
| **11** | **Object Information** | 3D bounding boxes and cluster centroids for detected dynamic objects (vehicles, pedestrians). |
| **12** | **Temporal Playback** | Interactive timeline scrubber with play, pause, step-forward, and playback speed controls. |

---

## 3. Data Flow & Decoupling Contract

1. **Decoupled Consumer:** The visualizer implements `IVisualizer` and consumes immutable copies of `SemanticMap` and `TelemetryMetrics`.
2. **Non-Blocking Execution:** The visualization update loop should execute in a separate thread or at a throttled render rate (e.g. 30–60 FPS) without stalling the core real-time perception pipeline.
3. **Headless Mode Support:** The visualizer must support running in headless / disabled mode (`MockVisualizer`) to allow automated CI testing and benchmarking without GUI dependencies.
