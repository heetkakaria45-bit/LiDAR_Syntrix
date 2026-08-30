"""Test configuration loading, schema structure, and parameter validation."""

from pathlib import Path
import yaml
import pytest


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
    """Verify all four initial foveation zones and their resolutions."""
    foveation = loaded_config.get("foveation_levels", {})

    expected_levels = {
        "near": {"max_range": 10.0, "resolution": 0.05},
        "mid_near": {"max_range": 25.0, "resolution": 0.10},
        "mid": {"max_range": 50.0, "resolution": 0.25},
        "far": {"max_range": 100.0, "resolution": 0.50},
    }

    for level_name, expected_params in expected_levels.items():
        assert level_name in foveation, f"Foveation level '{level_name}' missing from config"
        level_cfg = foveation[level_name]
        assert level_cfg["max_range"] == pytest.approx(expected_params["max_range"]), (
            f"Level '{level_name}' max_range mismatch: expected {expected_params['max_range']}, "
            f"got {level_cfg.get('max_range')}"
        )
        assert level_cfg["resolution"] == pytest.approx(expected_params["resolution"]), (
            f"Level '{level_name}' resolution mismatch: expected {expected_params['resolution']}, "
            f"got {level_cfg.get('resolution')}"
        )

    # Monotonicity check: range and resolution increase outward
    levels = ["near", "mid_near", "mid", "far"]
    for i in range(len(levels) - 1):
        curr_lvl = foveation[levels[i]]
        next_lvl = foveation[levels[i + 1]]
        assert curr_lvl["max_range"] < next_lvl["max_range"], (
            f"max_range must increase monotonically: {levels[i]} vs {levels[i+1]}"
        )
        assert curr_lvl["resolution"] < next_lvl["resolution"], (
            f"resolution must coarsen outward: {levels[i]} vs {levels[i+1]}"
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
    assert classes[0]["name"] == "drivable_ground"
    assert classes[0]["is_traversable"] is True
    assert classes[1]["name"] == "non_drivable_terrain"
    assert classes[1]["is_traversable"] is False
