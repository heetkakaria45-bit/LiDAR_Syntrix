# Module Handoff & Interface Specification: Evaluation & Benchmarking

- **Module Path:** `src/evaluation/`
- **Owner:** Himisha
- **Status:** Phase 2 Architecture Frozen

---

## 1. Responsibilities
- Quantitative evaluation metrics:
  - Per-class IoU, precision, recall, and overall mIoU.
  - Elevation RMSE and MAE against ground truth surfaces.
  - Distance-stratified accuracy breakdown across 4 concentric bins ($0\text{--}10\text{m}, 10\text{--}25\text{m}, 25\text{--}50\text{m}, 50\text{--}100\text{m}$).
- Comparative benchmarking: Uniform 5cm Grid ($16\text{M}$ cells, $1,024\text{MB}$) vs Foveated Multi-Ring ($\sim 650\text{k}$ cells, $\sim 41\text{MB}$) demonstrating $\ge 95\%$ memory reduction.
- Enforce strict prohibition on fabricated performance metrics.

## 2. Shared Data Contract & API
```python
from src.evaluation import (
    BenchmarkRunner,
    compute_semantic_iou,
    compute_elevation_rmse,
    compute_distance_stratified_metrics,
)

stats = BenchmarkRunner.compare_uniform_vs_foveated()
iou_results = compute_semantic_iou(pred_classes, gt_classes)
elev_err = compute_elevation_rmse(pred_elevations, gt_elevations)
```

## 3. Verification Command
```bash
pytest tests/evaluation/ -v
```
