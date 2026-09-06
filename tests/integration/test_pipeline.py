"""Unit tests for Pipeline Orchestrator and End-to-End Execution."""

from src.contracts import SyntheticSceneConfig
from src.integration import PipelineMode, PipelineOrchestrator, SequencePlayer
from src.preprocessing.synthetic import generate_synthetic_scene


def test_pipeline_orchestrator_synthetic_execution() -> None:
    """Ensure end-to-end pipeline processes frame and returns valid data contracts and telemetry."""
    orchestrator = PipelineOrchestrator(mode=PipelineMode.SYNTHETIC)

    frame, sem_cloud, sem_map, telemetry = orchestrator.process_frame()

    assert frame.points.shape[0] > 0
    assert sem_cloud.semantic_class.shape[0] == frame.points.shape[0]
    assert len(sem_map.cells) > 0
    assert "stage_latencies_ms" in telemetry
    assert "preprocessing" in telemetry["stage_latencies_ms"]
    assert "inference" in telemetry["stage_latencies_ms"]
    assert "mapping" in telemetry["stage_latencies_ms"]
    assert telemetry["pipeline_mode"] == "SYNTHETIC"


def test_pipeline_fallback_to_synthetic() -> None:
    """Ensure pipeline gracefully falls back to synthetic data when real data source is missing."""
    orchestrator = PipelineOrchestrator(mode=PipelineMode.REAL)

    frame, sem_cloud, sem_map, telemetry = orchestrator.process_frame()

    assert frame.points.shape[0] > 0
    assert orchestrator.active_source_mode == PipelineMode.SYNTHETIC
    assert telemetry["pipeline_mode"] == "SYNTHETIC"


def test_sequence_player_step() -> None:
    """Ensure SequencePlayer steps forward and triggers callbacks."""
    orchestrator = PipelineOrchestrator()
    frames_received = []

    def callback(f, sc, sm, t):
        frames_received.append(t["frame_count"])

    player = SequencePlayer(orchestrator=orchestrator, on_frame_callback=callback)
    player.step()
    player.step()

    assert len(frames_received) == 2
    assert frames_received == [1, 2]


def test_pipeline_evaluation_consumption() -> None:
    """Ensure pipeline automatically computes and attaches evaluation metrics when GT is present."""
    orchestrator = PipelineOrchestrator(mode=PipelineMode.SYNTHETIC)
    frame, sem_cloud, sem_map, telemetry = orchestrator.process_frame()

    assert "evaluation" in sem_map.metadata
    eval_meta = sem_map.metadata["evaluation"]
    assert "mIoU" in eval_meta
    assert eval_meta["mIoU"] >= 0.0
    assert "distance_stratified" in eval_meta
    assert "evaluation" in telemetry
    assert telemetry["evaluation"]["metric_type"] == "MEASURED"
