# Benchmarking & Performance Engineering Specification

> **Module Owner:** Himisha (`src/evaluation/`)  
> **Status:** Specification Freeze (Phase 2)  
> **Purpose:** Quantitative evaluation protocols, metrics, latency profiling, and anti-fabrication standards.

---

## 1. Core Evaluation Philosophy & Anti-Fabrication Oath

The primary contribution of this research for SIH 2026 is proving that **foveated semantic 2.5D mapping dramatically cuts memory and latency while retaining millimeter-level geometric safety where it matters most**.

To ensure academic and engineering integrity:
> [!CAUTION]
> **STRICT PROHIBITION ON FABRICATED NUMBERS:**
> Under no circumstances may any performance metric (FPS, mIoU, RMSE, memory savings) be invented, estimated, or published in commit messages, documentation, or jury slides without originating from an automated test script executed on physical data splits with logged hardware specifications.

---

## 2. Primary Comparative Study: Uniform vs. Foveated

Himisha's evaluation pipeline must execute an automated comparative study contrasting:

| Dimension | Uniform High-Resolution Grid | Foveated Multi-Ring Grid | Target Advantage |
| :--- | :--- | :--- | :--- |
| **Grid Resolution** | $0.05\text{ m}$ ($5\text{ cm}$) uniform to $100\text{ m}$ | $5\text{ cm}$ (near), $10\text{ cm}$ (mid-near), $25\text{ cm}$ (mid), $50\text{ cm}$ (far) | Adaptive density |
| **Theoretical Cell Count** | $\left(\frac{200}{0.05}\right)^2 = \mathbf{16,000,000\text{ cells}}$ | $\sim \mathbf{650,000\text{ cells}}$ | **$\ge 95\%$ memory reduction** |
| **Memory Footprint** | Measured in MB/GB | Measured in MB/GB | Quantified in evaluation reports |
| **Mapping Update Latency** | Insertion time across 16M cells | Multi-ring hash insertion time | **$\ge 5\times$ speedup** |
| **Near-Field Accuracy ($0\text{--}10\text{ m}$)** | Baseline RMSE & mIoU | Baseline RMSE & mIoU | **Zero accuracy loss in near field** |
| **Hazard Detection Recall** | Curb/pothole detection % in $0\text{--}10\text{ m}$ | Curb/pothole detection % in $0\text{--}10\text{ m}$ | **Identical safety recall** |

---

## 3. Quantitative Evaluation Metrics

### 3.1. Semantic Segmentation Metrics
Computed against labeled ground truth point clouds and aggregated map cells:

- **Intersection-over-Union (IoU) per class $c$:**
  $$\text{IoU}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c + \text{FN}_c}$$
- **Mean Intersection-over-Union (mIoU):**
  $$\text{mIoU} = \frac{1}{C} \sum_{c=0}^{C-1} \text{IoU}_c$$
- **Precision, Recall, and $F_1$-score:**
  $$\text{Precision}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c}, \quad \text{Recall}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FN}_c}, \quad F_1 = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$

### 3.2. Geometric & Elevation Accuracy Metrics
Computed between ground truth mesh/point surface height $z_i^*$ and estimated cell elevation $\hat{z}_i$:

- **Elevation Root Mean Square Error (RMSE):**
  $$\text{RMSE}_z = \sqrt{\frac{1}{M} \sum_{i=1}^M (\hat{z}_i - z_i^*)^2}$$
- **Mean Absolute Error (MAE):**
  $$\text{MAE}_z = \frac{1}{M} \sum_{i=1}^M |\hat{z}_i - z_i^*|$$
- **Step Discontinuity Recall:** Percentage of road curbs and potholes correctly identified within $\pm 5\text{ cm}$ spatial tolerance.

### 3.3. Distance-Stratified Evaluation
Because spatial resolution varies with distance, all geometric and semantic metrics must be stratified and reported across four distance bins:
1. **Near Zone ($0\text{--}10\text{ m}$):** Evaluates near-field fidelity ($5\text{ cm}$ resolution).
2. **Mid-Near Zone ($10\text{--}25\text{ m}$):** Evaluates tactical maneuvering zone ($10\text{ cm}$ resolution).
3. **Mid Zone ($25\text{--}50\text{ m}$):** Evaluates intermediate perception zone ($25\text{ cm}$ resolution).
4. **Far Zone ($50\text{--}100\text{ m}$):** Evaluates distant situational awareness ($50\text{ cm}$ resolution).

---

## 4. Latency & Resource Telemetry Protocol

The benchmarking module must record real-time performance telemetry per frame and generate summary statistical tables (Mean, Median, 95th Percentile, 99th Percentile):

```
┌────────────────────────────────────────────────────────────┐
│                    FRAME LATENCY BREAKDOWN                 │
├─────────────────────────┬─────────────────┬────────────────┤
│ Pipeline Stage          │ Mean Time (ms)  │ P95 Time (ms)  │
├─────────────────────────┼─────────────────┼────────────────┤
│ 1. Preprocessing        │ [auto-recorded] │ [auto-recorded]│
│ 2. Perception Inference │ [auto-recorded] │ [auto-recorded]│
│ 3. Grid Binning / Index │ [auto-recorded] │ [auto-recorded]│
│ 4. 2.5D Mapping Fusion  │ [auto-recorded] │ [auto-recorded]│
│ 5. Hazard Analysis      │ [auto-recorded] │ [auto-recorded]│
│ 6. Rendering / UI Push  │ [auto-recorded] │ [auto-recorded]│
├─────────────────────────┼─────────────────┼────────────────┤
│ TOTAL PIPELINE LATENCY  │ [auto-recorded] │ [auto-recorded]│
│ END-TO-END SYSTEM FPS   │ [auto-recorded] │ [auto-recorded]│
└─────────────────────────┴─────────────────┴────────────────┘
```

### Memory Footprint Tracking
- **Process RAM:** Measured using `psutil` (Resident Set Size in MB).
- **GPU VRAM:** Measured via `torch.cuda.memory_allocated()` or `pynvml` (Allocated & Reserved MB).
- **Spatial Grid Memory:** Measured via `sys.getsizeof()` on populated cell containers.

---

## 5. Automated Benchmark Report Generation

Himisha's module must automatically output reproducibility artifacts in `outputs/`:
1. `outputs/benchmark_summary.json`: Machine-readable structured benchmark metrics.
2. `outputs/benchmark_report.md`: Formatted Markdown report ready for presentation to SIH jurors.
3. `outputs/distance_error_curve.png`: Plot of Elevation RMSE versus Range $(0\text{--}100\text{ m})$.
4. `outputs/latency_breakdown.png`: Stacked bar chart showing per-stage execution times.
