"""Test configuration loading, schema structure, and parameter validation."""

from pathlib import Path
import pytest
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "default_config.yaml"


@pytest.fixture
def loaded_config():
    """Load default configuration YAML file."""
    assert CONFIG_PATH.is_file(), f"Configuration file not found at {CONFIG_PATH}"
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert isinstance(cfg, dict), "Configuration must parse to a dictionary"
    return cfg


def test_map_configuration(loaded_config):
    """Verify global map parameters conform to SIH 2026 specs."""
    map_cfg = loaded_config.get("map", {})
    assert map_cfg.get("max_radius") == 100.0, "Map max radius must be 100.0 meters"
    assert map_cfg.get("units") == "meters", "Units must be meters"

    coords = map_cfg.get("coordinate_convention", {})
    assert coords.get("forward") == "X", "Forward axis must be X"
    assert coords.get("left") == "Y", "Left axis must be Y"
    assert coords.get("up") == "Z", "Up axis must be Z"


def test_foveation_levels(loaded_config):
    """Verify all four initial foveation zones (Levels 0 through 3) and their resolutions."""
    foveation = loaded_config.get("foveation_levels", {})

    expected_levels = [
        {"key": "level_0", "name": "near", "max_range": 10.0, "resolution": 0.05},
        {"key": "level_1", "name": "mid_near", "max_range": 25.0, "resolution": 0.10},
        {"key": "level_2", "name": "mid", "max_range": 50.0, "resolution": 0.25},
        {"key": "level_3", "name": "far", "max_range": 100.0, "resolution": 0.50},
    ]

    for item in expected_levels:
        key = item["key"]
        assert key in foveation, f"Level key '{key}' missing from foveation_levels"
        cfg = foveation[key]
        assert cfg["max_range"] == pytest.approx(item["max_range"])
        assert cfg["resolution"] == pytest.approx(item["resolution"])

    # Monotonicity check: range and resolution increase outward
    keys = ["level_0", "level_1", "level_2", "level_3"]
    for i in range(len(keys) - 1):
        curr_lvl = foveation[keys[i]]
        next_lvl = foveation[keys[i + 1]]
        assert curr_lvl["max_range"] < next_lvl["max_range"], (
            f"max_range must increase monotonically: {keys[i]} vs {keys[i+1]}"
        )
        assert curr_lvl["resolution"] < next_lvl["resolution"], (
            f"resolution must coarsen outward: {keys[i]} vs {keys[i+1]}"
        )


def test_semantic_classes(loaded_config):
    """Verify standard initial 8 semantic classes."""
    classes = loaded_config.get("semantic_classes", {})
    expected_class_ids = [0, 1, 2, 3, 4, 5, 6, 7]

    for cid in expected_class_ids:
        assert cid in classes, f"Semantic class ID {cid} missing from config"
        assert "name" in classes[cid]
        assert "is_traversable" in classes[cid]
        assert isinstance(classes[cid]["is_traversable"], bool)

    # Specific class assertions
    assert classes[0]["name"].upper() == "DRIVABLE_GROUND"
    assert classes[0]["is_traversable"] is True
    assert classes[1]["name"].upper() == "NON_DRIVABLE_TERRAIN"
    assert classes[1]["is_traversable"] is False
    assert classes[2]["name"].upper() == "VEHICLE"
    assert classes[3]["name"].upper() == "PEDESTRIAN"


def test_dataset_mappings_configured(loaded_config):
    """Verify dataset label mapping tables for SemanticKITTI and nuScenes."""
    mappings = loaded_config.get("dataset_label_mappings", {})
    assert "semantickitti" in mappings, "SemanticKITTI mapping missing"
    assert "nuscenes" in mappings, "nuScenes mapping missing"

    kitti = mappings["semantickitti"]
    # Check that road maps to 0 (DRIVABLE_GROUND)
    assert kitti[9] == 0
    # Check that car maps to 2 (VEHICLE)
    assert kitti[1] == 2
    # Check that pedestrian (6) maps to 3
    assert kitti[6] == 3


def test_hazard_thresholds(loaded_config):
    """Verify geometric hazard detection thresholds."""
    mapping_cfg = loaded_config.get("mapping", {})
    hazards = mapping_cfg.get("hazards", {})

    assert hazards.get("curb_min_step") == 0.08
    assert hazards.get("curb_max_step") == 0.25
    assert hazards.get("pothole_min_depth") == 0.05
    assert hazards.get("overhang_min_clearance") == 2.2
