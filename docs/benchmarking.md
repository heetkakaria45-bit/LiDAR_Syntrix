# Benchmarking & Performance Evaluation Contract

## 1. Zero-Fabrication Metric Policy

> [!IMPORTANT]
> **Strict Verification Standard:**
> No benchmark result, runtime latency, memory usage statistic, frame rate, or compression metric may ever be hardcoded or fabricated. All numbers presented in final reports must be generated dynamically from reproducible benchmark runs instrumented with physical system timers (`time.perf_counter()`), memory profilers, and hardware counters.

---

## 2. Mandatory Evaluation Benchmark: Uniform vs. Foveated Grid

The primary scientific contribution of this architecture is demonstrating that multi-resolution foveation delivers high spatial fidelity near the ego-vehicle while drastically reducing memory footprint and computational latency compared to a uniform high-resolution grid.

### Comparison Matrix

$$\begin{array}{|l|c|c|}
\hline
\textbf{Metric} & \textbf{Uniform Grid (0.05 m)} & \textbf{Foveated Grid (0.05m - 0.50m)} \\
\hline
\text{Total Range} & 0 \text{ to } 100\,m \text{ (200m } \times \text{ 200m box)} & 0 \text{ to } 100\,m \text{ (200m } \times \text{ 200m box)} \\
\text{Theoretical Max Cells} & 4,000 \times 4,000 = 16,000,000 & \approx 1,200,000 \text{ (13.3}\times \text{ reduction)} \\
\text{Active Memory (MB)} & \text{Measured in Phase K} & \text{Measured in Phase K} \\
\text{Point Insertion Time (ms)} & \text{Measured in Phase K} & \text{Measured in Phase K} \\
\text{Traversability Eval Time (ms)} & \text{Measured in Phase K} & \text{Measured in Phase K} \\
\text{Near-field Resolution (0-10m)} & 0.05\,m & 0.05\,m \text{ (Identical)} \\
\text{Far-field Resolution (50-100m)} & 0.05\,m & 0.50\,m \text{ (Sufficient for planning)} \\
\hline
\end{array}$$

---

## 3. Standardized Telemetry Metrics Contract

The benchmarking engine (`src/evaluation/`) will track and log the following core metrics per frame:

1. **Preprocessing Latency ($t_{prep}$):** Time spent filtering NaNs, cropping ranges, and cleaning noise ($ms$).
2. **Inference Latency ($t_{infer}$):** Neural network / perception inference time ($ms$).
3. **Spatial Projection Latency ($t_{proj}$):** Point cloud transformation and foveated spatial binning time ($ms$).
4. **2.5D Mapping Latency ($t_{map}$):** Elevation estimation, roughness calculation, and cell aggregation time ($ms$).
5. **Traversability Evaluation Latency ($t_{trav}$):** Slope, step height, and obstacle cost calculation time ($ms$).
6. **Rendering Latency ($t_{render}$):** GUI drawing / display pipeline time ($ms$).
7. **End-to-End Latency ($t_{total}$):** Total wall-clock time from raw packet to updated map ($ms$).
8. **Pipeline Throughput ($FPS$):** Frames processed per second ($Hz$).
9. **Host RAM Usage ($RAM_{MB}$):** Process resident set size (RSS) in megabytes.
10. **GPU VRAM Usage ($VRAM_{MB}$):** Dedicated GPU memory allocation in megabytes (when CUDA is active).
11. **Input Point Count ($N_{pts}$):** Number of raw LiDAR points ingested.
12. **Active Grid Cell Count ($N_{cells}$):** Number of non-empty 2.5D cells maintained in the active map.

---

## 4. Benchmark Harness Requirements (Phase K)

1. **Warmup Period:** Execute at least 10 warmup frames prior to recording performance data to eliminate initial JIT/cache cold-start bias.
2. **Statistical Aggregation:** For each metric, compute:
   - Minimum
   - Maximum
   - Mean
   - Median (p50)
   - 95th Percentile (p95)
   - 99th Percentile (p99)
   - Standard Deviation
3. **Environment Standardization:** Log CPU model, core count, RAM size, GPU model, OS version, and Python package versions alongside benchmark JSON outputs.
4. **Reproducibility Script:** Provide single-command execution:
   ```bash
   python -m src.evaluation.benchmark --config config/config.yaml --dataset <path_to_sequence> --output results/
   ```
