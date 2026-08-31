# Stage Handoff Protocols & Checklists

This directory defines the formal handoff protocols between upstream and downstream module owners.

---

## 1. Upstream-Downstream Dependency & Handoff Map

```text
+-----------------------+
| Amulya                |
| (src/preprocessing/)  |
+-----------------------+
           |
           | Handoff Contract: PointCloudFrame (Clean, FLU frame, meters)
           v
+-----------------------+
| Vedant                |
| (src/perception/)     |
+-----------------------+
           |
           | Handoff Contract: SemanticPointCloud (Taxonomy 0..7, confidence [0,1])
           +---------------------------------------+
           |                                       |
           v                                       v
+-----------------------+               +-----------------------+
| Manashri              |               | Heet                  |
| (src/foveated_grid/)  |               | (src/mapping/)        |
+-----------------------+               +-----------------------+
           |                                       |
           | Handoff: Foveated Spatial Indexing    |
           +---------------------------------------+
                               |
                               | Handoff Contract: SemanticMap & Traversability
                               v
               +-------------------------------+
               | Atharva                       |
               | (src/integration/ & vis/)     |
               +-------------------------------+
                               |
                               | Handoff Contract: Pipeline Runner & Telemetry
                               v
               +-------------------------------+
               | Himisha                       |
               | (src/evaluation/)             |
               +-------------------------------+
```

---

## 2. Formal Stage Handoff Checklists

### Handoff 1: Preprocessing (`Amulya`) $\to$ Perception (`Vedant`)
- [ ] Ingested points are validated as `PointCloudFrame`.
- [ ] Coordinates are in Forward-Left-Up (FLU) meters.
- [ ] No NaNs, Infs, or duplicate coordinate artifacts.
- [ ] Points outside $[-100, 100]\,m$ range box are trimmed.
- [ ] Unit tests pass with `test_preprocessing.py`.

### Handoff 2: Perception (`Vedant`) $\to$ Spatial Indexing (`Manashri`) & Mapping (`Heet`)
- [ ] Output conforms to `SemanticPointCloud`.
- [ ] Point count matches input frame exactly.
- [ ] Semantic labels strictly in $[0..7]$ (Taxonomy compliance).
- [ ] Confidence array values strictly in $[0.0, 1.0]$.
- [ ] Inference latency benchmarked and documented.

### Handoff 3: Spatial Grid (`Manashri`) $\to$ 2.5D Mapping (`Heet`)
- [ ] `IFoveatedGrid` interface fully implemented.
- [ ] Deterministic world-to-cell and cell-to-world conversion tests pass.
- [ ] Boundary tests ($9.999m$, $10.000m$, $10.001m$, etc.) pass.
- [ ] Symmetric handling of negative coordinate quadrants ($X < 0, Y < 0$).
- [ ] Spatial hashing performance verified without memory leaks.

### Handoff 4: Mapping (`Heet`) $\to$ Integration & Visualization (`Atharva`)
- [ ] Output conforms to `SemanticMap` container.
- [ ] Elevation stats ($min\_z, max\_z, mean\_z, roughness$) computed for each cell.
- [ ] Traversability scores and navigation costs in $[0.0, 1.0]$.
- [ ] Temporal integration preserves observation counts across frames.

### Handoff 5: Integration (`Atharva`) $\to$ Evaluation (`Himisha`)
- [ ] `IPipelineIntegrator.step()` and `run_stream()` execute reliably.
- [ ] Wall-clock latency metrics logged per stage without artificial delays.
- [ ] Control Center UI renders all 12 operational views in live/dataset modes.
- [ ] Clean headless mode supported for automated benchmarking.
