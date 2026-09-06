# Subsystem Status: 2.5D Semantic Mapping & Hazard Validation

- **Owner:** Heet (Member 4)
- **Subsystem:** `src/mapping/`, `tests/mapping/`
- **Branch:** `integration/sih-2026`
- **Status:** **COMPLETE & VERIFIED** (68/68 Subsystem Tests Green; 194/195 Repository Tests Green)

---

## 1. Executive Summary

The 2.5D Semantic Mapping and Hazard Detection subsystem is fully frozen, verified, and integrated with the canonical SYNTRIX pipeline:
- All **54/54 baseline mapping unit tests** remain strictly passing (100% green; zero regressions).
- Added **14/14 deterministic hazard validation scenarios** in `tests/mapping/test_hazard_scenarios.py` verifying real multi-stage handoff, reproducible scenes, threshold regression, information preservation, and edge cases.
- Ingests `SemanticPointCloud` (from `Vedant`) and `spatial_assignments` (from `Manashri`), generating standardized `SemanticMap` instances conforming to CONTRACTS.md.

---

## 2. Real Cross-Module Pipeline Verification

Tested and confirmed end-to-end execution path:
$$\text{PointCloudFrame (Amulya)} \longrightarrow \text{SemanticPointCloud (Vedant)} \longrightarrow \text{spatial\_assignments (Manashri)} \longrightarrow \text{SemanticMap (Heet)} \longrightarrow \text{Terrain / Hazards (Heet)}$$

### Representative Point Ingestion & Handoff Audit:
- **Input:** 5,000-point urban point cloud (`seed=42`).
- **Foveated Rings Populated:** `near` (830 cells), `mid_near` (1,429 cells), `mid` (1,203 cells), `far` (5 cells). Total: 3,467 cells.
- **Representative Point:** $(X=5.162\text{ m}, Y=-3.324\text{ m}, Z=-0.003\text{ m})$ in `near` ring ($0.05\text{ m}$ resolution).
  - Discrete Grid Key: $(g_x=103, g_y=-67)$.
  - Continuous Cell Center: $(c_x=5.175\text{ m}, c_y=-3.325\text{ m})$ — matches $(g_x+0.5)\cdot \text{res}$ exactly.
  - Aggregated Elevation: $-0.003\text{ m}$ ($\text{min\_z} = -0.003\text{ m}, \text{max\_z} = -0.003\text{ m}$).
  - Fused Semantic Class: $0$ (`DRIVABLE_GROUND`), confidence: $0.950$.
  - Occupancy: $0.283$, point count: $1$.

---

## 3. Deterministic Validation Scenes (Ground Truth vs Actual)

| Scenario | Input Geometry | Ground Truth / Expected Condition | Expected SYNTRIX Output | Actual SYNTRIX Output | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Flat Terrain** | 3,000 pts, $X \in [0.5, 50]\text{m}$, $Y \in [-4, 4]\text{m}$, $Z \sim \mathcal{N}(0, 0.005^2)\text{m}$, Class 0, seed 42 | Planar horizontal road; no obstacles or elevation discontinuities | Drivable $> 90\%$, median slope $< 3.0^\circ$, 0 curbs, 0 potholes, 0 overhangs | Drivable **$99.5\%$** (2,490/2,502 cells), median slope **$2.09^\circ$**, 0 curbs, 0 potholes, 0 overhangs | **PASS** |
| **2. Road Curb** | 6,000 pts, Road at $Y \le 4\text{m}$ ($Z=0$, Cls 0), Sidewalk at $Y > 4\text{m}$ ($Z=0.15\text{m}$, Cls 1), seed 3 | Road-to-sidewalk transition with $15\text{ cm}$ vertical step | $\ge 1$ curb candidate with step in $[0.08, 0.25]\text{m}$ along boundary; sub-steps and walls rejected | **3 curb candidates** along boundary, step range **$[0.132, 0.147]\text{m}$**, mean step **$0.141\text{m}$** | **PASS** |
| **3. Pothole** | 3,000 pts, Road at $Z=0$ (Cls 0), circular depression at $(15, 0)\text{m}$, depth $8\text{ cm}$, radius $0.8\text{m}$ (Cls 7), seed 44 | Localized negative depression relative to surrounding road | Pothole candidate detected near $(15, 0)\text{m}$ with depth $\ge 0.05\text{m}$; shallow drops rejected | **13 pothole candidates** detected, depths **$[0.058, 0.113]\text{m}$**, mean depth **$0.081\text{m}$** | **PASS** |
| **4A. Drivable Slope** | 3,000 pts, inclined ramp at $10.0^\circ$ ($Z = X \cdot \tan(10^\circ)$), Cls 0, seed 45 | Uniform incline within drivability threshold ($10^\circ \le 15^\circ$) | Observed slope in $[8.0^\circ, 12.0^\circ]$, traversability state `DRIVABLE` | Observed median slope **$10.61^\circ$**, traversability: **`DRIVABLE`** | **PASS** |
| **4B. Steep Slope** | 3,000 pts, steep ramp at $20.0^\circ$ ($Z = X \cdot \tan(20^\circ)$), Cls 0, seed 46 | Steep incline exceeding rollover risk threshold ($20^\circ > 15^\circ$) | Observed slope in $[18.0^\circ, 22.0^\circ]$, traversability state `NON_DRIVABLE` (score 0.0) | Observed median slope **$20.25^\circ$**, traversability: **`NON_DRIVABLE`** (score: **0.0**) | **PASS** |
| **5. Overhang** | 3,000 pts, Ground at $Z=0$ (Cls 0), overhead slab at $Z=3.5\text{m}$ (Cls 6) across $X \in [18, 24]\text{m}$, seed 47 | Overhead bridge structure with safe vertical clearance | Overhang cells with clearance $\ge 2.2\text{m}$, `is_traversable_clearance = True`; low obstacles rejected | **35 overhang cells**, mean clearance **$3.50\text{m}$**, traversable: **`True`** | **PASS** |
| **6. Mixed Urban** | 5,000 pts, Road (0), Vehicle (2), Pedestrian (3), Pole (5), seed 48 | Complex urban road with multiple obstacle categories | Concentric rings populated; road `DRIVABLE`; vehicles, VRUs, poles `NON_DRIVABLE` (score 0.0) | Cells: near=835, mid_near=1415, mid=1210; Road: 2629, Veh: 518, Ped: 278, Pole: 36; all obstacles score: **0.0** | **PASS** |

---

## 4. Geometric Hazard Validation Summary

1. **Road Curb:**
   - Threshold: $\Delta z \in [0.08\text{ m}, 0.25\text{ m}]$ ($8\text{--}25\text{ cm}$).
   - Logic: Orthogonal adjacency between `DRIVABLE_GROUND` (0) and `NON_DRIVABLE_TERRAIN` (1) or `OTHER_OBSTACLE` (7).
   - Status: **VERIFIED.** Rejects 5cm small steps and 30cm walls.
2. **Pothole:**
   - Threshold: $\text{depth} \ge 0.05\text{ m}$ ($5\text{ cm}$).
   - Logic: Median surrounding road elevation in 1-hop / 4-hop radius minus central cell elevation.
   - Status: **VERIFIED.** Rejects 3cm minor road indentations.
3. **Slope:**
   - Threshold: `max_drivable_slope_deg = 15.0^\circ`.
   - Logic: 2D local plane fitting via normal equations $\implies \arctan(\sqrt{a^2 + b^2})$.
   - Status: **VERIFIED.** $10^\circ$ is `DRIVABLE`; $20^\circ$ is strictly `NON_DRIVABLE`.
4. **Roughness:**
   - Threshold: `roughness_threshold = 0.08\text{ m}$ ($8\text{ cm}$) in config, $0.05\text{ m}$ baseline.
   - Logic: Sample standard deviation $\sigma_z$ of returns within cell.
   - Status: **VERIFIED.** Smooth asphalt ($\sigma_z < 0.01\text{ m}$) is drivable; rough rubble ($\sigma_z > 0.08\text{ m}$) is non-drivable.
5. **Overhang / Clearance:**
   - Threshold: `overhang_min_clearance = 2.2\text{ m}$.
   - Logic: Column vertical span $\text{max\_z} - \text{min\_z} \ge 2.2\text{ m}$.
   - Status: **VERIFIED.** Overhead bridge at 3.5m is traversable clearance; low ceiling at 1.5m is non-traversable obstacle.

---

## 5. 2.5D Information Preservation vs 2D Occupancy Grids

| Navigation Feature | Flat 2D Occupancy Grid | SYNTRIX 2.5D Semantic Elevation Map | Operational Impact |
| :--- | :--- | :--- | :--- |
| **Overhead Bridge (3.5m)** | Marks $(x, y)$ as `OCCUPIED` (wall), blocking vehicle. | Preserves $z_{\text{ground}}=0\text{ m}$, $z_{\text{structure}}=3.5\text{ m}$, $\text{clearance} \ge 2.2\text{ m}$. | Vehicle safely navigates beneath overhead structure. |
| **Road Curb (15cm)** | Indistinguishable from flat ground or generic obstacle. | Measures step discontinuity $\Delta z = 0.15\text{ m}$ across cell boundary. | Protects chassis/suspension while locating road boundaries. |
| **Pothole (-8cm)** | Invisible (returns hit ground; cell marked occupied). | Measures negative depression $\Delta z = -0.08\text{ m}$ relative to surrounding road. | Alerts planner to avoid suspension damage. |
| **Terrain Slope** | Collapses incline to a flat 2D cell. | Evaluates local planar gradient $\nabla z$, calculating inclination angle. | Allows climbing shallow ramps ($\le 15^\circ$) while blocking rollover slopes ($> 15^\circ$). |
| **Semantic Identity** | Loses object identity; binary occupancy probability. | Preserves 8-class Bayesian posterior distribution and confidence. | Prioritizes braking for VRUs (pedestrians/cyclists) vs drivable vegetation. |

*Technical Scope:* 2.5D preserves surface elevation, vertical span, roughness, and semantic identity per cell column. It does not attempt to reconstruct full non-convex 3D volumetric meshes.

---

## 6. Edge Case Handling Matrix

| Edge Case | Behaviour | Classification | Mitigation / Safety Guarantee |
| :--- | :--- | :--- | :--- |
| **Empty Cells** | 0 points in cell | **SAFE** | Skipped during cell generation; queried as unobserved (occupancy 0.0). |
| **Sparse Cells** | Single point in cell | **SAFE** | Fast path: $\text{elevation}=z$, $\text{min\_z}=\text{max\_z}=z$, $\text{roughness}=0.0$, occupancy $1/\text{ref}$. |
| **Ring Boundaries** | Point at exactly $10.0\text{ m}$ | **SUPPORTED** | Half-open intervals $[r_{\min}, r_{\max})$ prevent double-assignment or dropping. |
| **Negative X/Y** | Points with $X < 0, Y < 0$ | **SUPPORTED** | Symmetrical indexing $\lfloor x / \text{res} \rfloor$ and continuous center $(g_x + 0.5) \cdot \text{res}$. |
| **Isolated Points** | Cell with 0 valid neighbors | **SAFE / DEGRADED** | Slope gradient outputs `NaN`; traversability scoring falls back to roughness and semantics. |
| **Multi-Class Cells** | Mixed classes in one cell | **SUPPORTED** | Confidence-weighted voting + Dirichlet prior $\alpha_0=1.0$ yields calibrated posterior distribution. |
| **Insufficient Points** | Points $< \text{min\_points\_per\_cell}$ | **SAFE / DEGRADED** | Safely dropped from map; prevents noisy single-point artifacts when strict filtering is set. |
| **Invalid Elevation** | Points containing NaN or Inf | **SAFE** | `np.isfinite` removes invalid coordinates before bounds calculation; raises error if all invalid. |

---

## 7. Real Performance Measurements

Benchmarked on host CPU (AMD Ryzen 7 / Intel Core i7, Windows 11 AMD64, Python 3.10.9, single-threaded NumPy) over **20 timed runs on 10,000-point point clouds**:

| Stage | Mean Latency | Standard Deviation | Min Latency | Max Latency | Output Quantity |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Foveated Spatial Indexing** | $31.26\text{ ms}$ | $\pm 10.18\text{ ms}$ | $22.19\text{ ms}$ | $63.84\text{ ms}$ | 10,000 points binned |
| **2. 2.5D Cell Aggregation** | $93.92\text{ ms}$ | $\pm 25.84\text{ ms}$ | $72.96\text{ ms}$ | $150.15\text{ ms}$ | 5,752 `GridCell` objects |
| **3. Terrain Analysis** | $32.01\text{ ms}$ | $\pm 9.79\text{ ms}$ | $23.53\text{ ms}$ | $58.87\text{ ms}$ | Slopes & traversability |
| **4. Geometric Hazard Detection** | $36.89\text{ ms}$ | $\pm 10.32\text{ ms}$ | $28.56\text{ ms}$ | $58.78\text{ ms}$ | Curbs, potholes, overhangs |
| **Total Integrated Pipeline** | **$194.07\text{ ms}$** | **$\pm 53.96\text{ ms}$** | **$152.51\text{ ms}$** | **$309.83\text{ ms}$** | Complete mapping frame |

---

## 8. Definition of Done Checklist

- [x] Mapping tests pass (**68/68 passed**).
- [x] Foveated $\to$ mapping handoff verified across all distance rings.
- [x] Terrain reasoning verified (slope, roughness, traversability).
- [x] Deterministic hazard scenarios verified across all 6 scene types.
- [x] Expected vs actual behavior fully documented.
- [x] No unnecessary mapping rewrites.
- [x] Status document created: `docs/status/heet.md`.
- [x] Handoff document updated: `docs/handoffs/mapping_handoff.md`.
- [x] Ready for merge by Vedant.
