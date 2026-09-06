# Module Handoff & Interface Specification: Integration & Visualization

- **Module Path:** `src/integration/`, `src/evaluation/`, `src/visualization/`, `frontend/`
- **Owner:** Atharva
- **Role:** System Integration, Real-Time Orchestration, Benchmarking & Advanced UI
- **Status:** Complete / Ready for Merge
- **Official Specification:** [atharva_integration_handoff.md](atharva_integration_handoff.md)
- **Commit Hash:** `297b2ea7c5417855bfa3d88bcfcb00fbf28562d9`

---

## 1. Quick Verification Commands
```bash
# 1. Run all unit and integration tests
pytest tests/ -v

# 2. Run automated comparative benchmark
python3 -c "from src.evaluation.benchmark import BenchmarkRunner; BenchmarkRunner.run_comparative_benchmark(scene_type='urban', num_runs=5, save_to_file=True)"

# 3. Launch the Web Visualizer Server
python3 -m src.visualization.server --port 8080
```
