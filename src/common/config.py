"""
Central Configuration Loader and Strongly Typed Configuration Schemas.

Loads and validates config/config.yaml with zero external runtime dependencies.
Location: src/common/ (Shared Infrastructure - Consensus Maintained).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.common.types import FoveationLevelConfig, SemanticClass


@dataclass
class CoordinateConfig:
    convention: str = "FLU"
    axes: Dict[str, str] = field(default_factory=lambda: {"x": "forward", "y": "left", "z": "up"})
    units: str = "meters"


@dataclass
class FoveationConfig:
    min_range_m: float = 0.0
    max_range_m: float = 100.0
    levels: List[FoveationLevelConfig] = field(default_factory=lambda: [
        FoveationLevelConfig(0, 0.0, 10.0, 0.05, "Immediate proximity zone (ultra-high fidelity)"),
        FoveationLevelConfig(1, 10.0, 25.0, 0.10, "Short-range reaction zone (high fidelity)"),
        FoveationLevelConfig(2, 25.0, 50.0, 0.25, "Medium-range planning zone (standard fidelity)"),
        FoveationLevelConfig(3, 50.0, 100.0, 0.50, "Long-range situational awareness zone (coarse fidelity)"),
    ])
    adaptive_refinement_enabled: bool = False
    adaptive_importance_weight: float = 0.0
    adaptive_uncertainty_weight: float = 0.0

    def validate(self) -> None:
        if self.min_range_m < 0.0:
            raise ValueError(f"min_range_m must be non-negative, got {self.min_range_m}")
        if self.max_range_m <= self.min_range_m:
            raise ValueError(f"max_range_m ({self.max_range_m}) must be > min_range_m ({self.min_range_m})")
        if not self.levels:
            raise ValueError("Foveation levels must not be empty.")

        # Validate monotonic boundaries and continuity
        prev_max = self.min_range_m
        for i, lvl in enumerate(self.levels):
            if lvl.level != i:
                raise ValueError(f"Foveation level index mismatch: expected {i}, got {lvl.level}")
            if lvl.min_radius_m != prev_max:
                raise ValueError(f"Discontinuity at level {i}: min_radius {lvl.min_radius_m} != prev_max {prev_max}")
            if lvl.max_radius_m <= lvl.min_radius_m:
                raise ValueError(f"Invalid level {i} range: [{lvl.min_radius_m}, {lvl.max_radius_m}]")
            if lvl.cell_resolution_m <= 0:
                raise ValueError(f"Resolution must be positive, got {lvl.cell_resolution_m}")
            prev_max = lvl.max_radius_m

        if prev_max != self.max_range_m:
            raise ValueError(f"Outer boundary {prev_max} does not match max_range_m {self.max_range_m}")


@dataclass
class SemanticClassInfo:
    id: int
    name: str
    description: str
    is_obstacle: bool
    is_ground: bool
    default_traversable: bool


@dataclass
class SemanticTaxonomyConfig:
    num_classes: int = 8
    classes: Dict[int, SemanticClassInfo] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.classes:
            self.classes = {
                0: SemanticClassInfo(0, "DRIVABLE_GROUND", "Paved road, asphalt, smooth navigable terrain", False, True, True),
                1: SemanticClassInfo(1, "NON_DRIVABLE_TERRAIN", "Grass, dirt, gravel, vegetation", True, True, False),
                2: SemanticClassInfo(2, "VEHICLE", "Cars, trucks, buses, trailers", True, False, False),
                3: SemanticClassInfo(3, "PEDESTRIAN", "Pedestrians, standing/walking persons", True, False, False),
                4: SemanticClassInfo(4, "CYCLIST", "Bicyclists, motorcyclists", True, False, False),
                5: SemanticClassInfo(5, "POLE", "Traffic signs, utility poles, light poles", True, False, False),
                6: SemanticClassInfo(6, "WALL_BUILDING", "Walls, fences, building facades", True, False, False),
                7: SemanticClassInfo(7, "OTHER_OBSTACLE", "Debris, unclassified obstacles, curbs", True, False, False),
            }


@dataclass
class PreprocessingConfig:
    crop_box: Dict[str, float] = field(default_factory=lambda: {
        "min_x": -100.0, "max_x": 100.0,
        "min_y": -100.0, "max_y": 100.0,
        "min_z": -5.0, "max_z": 10.0
    })
    filter_nans: bool = True
    min_intensity: float = 0.0
    max_intensity: float = 255.0


@dataclass
class MappingConfig:
    temporal_decay_factor: float = 0.95
    max_points_per_cell: int = 500
    occupancy_threshold: float = 0.5
    ground_elevation_default: float = 0.0
    max_step_height_m: float = 0.15
    max_slope_rad: float = 0.35
    roughness_threshold_m: float = 0.05


@dataclass
class RuntimeConfig:
    enable_telemetry: bool = True
    timer_backend: str = "time.perf_counter"
    warmup_frames: int = 10
    profile_memory: bool = True


@dataclass
class VisualizationConfig:
    window_title: str = "Autonomous Perception Control Center - 2.5D Foveated LiDAR"
    default_view_mode: str = "FOVEATED_SEMANTIC_ELEVATION"
    color_map: str = "ACCENT"


@dataclass
class SystemConfig:
    version: str = "1.0.0"
    coordinate_system: CoordinateConfig = field(default_factory=CoordinateConfig)
    foveation: FoveationConfig = field(default_factory=FoveationConfig)
    semantics: SemanticTaxonomyConfig = field(default_factory=SemanticTaxonomyConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    mapping: MappingConfig = field(default_factory=MappingConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)

    def validate(self) -> None:
        self.foveation.validate()
        if len(self.semantics.classes) != self.semantics.num_classes:
            raise ValueError(
                f"Number of defined semantic classes ({len(self.semantics.classes)}) does not match num_classes ({self.semantics.num_classes})"
            )


def _simple_yaml_parse(text: str) -> Dict[str, Any]:
    """
    Lightweight, zero-dependency YAML subset parser for config/config.yaml.
    Handles nested dictionaries, lists of objects, numbers, booleans, and strings.
    """
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    # Pure Python fallback parser for clean YAML dictionaries and lists
    lines = [line.rstrip() for line in text.splitlines()]
    result: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, result)]

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(line.lstrip())

        # Unwind stack to current indent level
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        current_container = stack[-1][1]

        if stripped.startswith("- "):
            # List item
            item_text = stripped[2:].strip()
            if ":" in item_text:
                k, v = item_text.split(":", 1)
                item_dict: Dict[str, Any] = {k.strip(): _parse_scalar(v.strip())}
                if isinstance(current_container, list):
                    current_container.append(item_dict)
                stack.append((indent, item_dict))
            else:
                val = _parse_scalar(item_text)
                if isinstance(current_container, list):
                    current_container.append(val)
            i += 1
            continue

        if ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()

            # Strip inline comments
            if "#" in val:
                val = val.split("#", 1)[0].strip()

            if val == "":
                # Could be starting a nested dict or list
                next_is_list = False
                for next_line in lines[i + 1:]:
                    s = next_line.strip()
                    if s and not s.startswith("#"):
                        if s.startswith("- "):
                            next_is_list = True
                        break

                new_container: Any = [] if next_is_list else {}
                if isinstance(current_container, dict):
                    current_container[key] = new_container
                stack.append((indent, new_container))
            else:
                scalar = _parse_scalar(val)
                if isinstance(current_container, dict):
                    current_container[key] = scalar
            i += 1
            continue

        i += 1

    return result


def _parse_scalar(val: str) -> Any:
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1]
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "none", "~"):
        return None
    try:
        if "." in val or "e" in val.lower():
            return float(val)
        return int(val)
    except ValueError:
        return val


def get_default_config_path() -> Path:
    """Returns absolute path to project config/config.yaml dynamically."""
    base_dir = Path(__file__).resolve().parents[2]
    return base_dir / "config" / "config.yaml"


def load_config(config_path: Optional[Path | str] = None) -> SystemConfig:
    """
    Loads, parses, and validates the system configuration.
    """
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        cfg = SystemConfig()
        cfg.validate()
        return cfg

    text = config_path.read_text(encoding="utf-8")
    data = _simple_yaml_parse(text)

    # Construct strongly typed configuration
    coord_data = data.get("coordinate_system", {})
    coord_cfg = CoordinateConfig(
        convention=coord_data.get("convention", "FLU"),
        axes=coord_data.get("axes", {"x": "forward", "y": "left", "z": "up"}),
        units=coord_data.get("units", "meters"),
    )

    fov_data = data.get("foveation", {})
    levels_data = fov_data.get("levels", [])
    levels: List[FoveationLevelConfig] = []
    for l_dict in levels_data:
        levels.append(
            FoveationLevelConfig(
                level=int(l_dict.get("level", 0)),
                min_radius_m=float(l_dict.get("min_radius_m", 0.0)),
                max_radius_m=float(l_dict.get("max_radius_m", 10.0)),
                cell_resolution_m=float(l_dict.get("cell_resolution_m", 0.05)),
                description=str(l_dict.get("description", "")),
            )
        )
    if not levels:
        fov_cfg = FoveationConfig()
    else:
        fov_cfg = FoveationConfig(
            min_range_m=float(fov_data.get("min_range_m", 0.0)),
            max_range_m=float(fov_data.get("max_range_m", 100.0)),
            levels=levels,
            adaptive_refinement_enabled=bool(fov_data.get("adaptive_refinement", {}).get("enabled", False)),
            adaptive_importance_weight=float(fov_data.get("adaptive_refinement", {}).get("importance_weight", 0.0)),
            adaptive_uncertainty_weight=float(fov_data.get("adaptive_refinement", {}).get("uncertainty_weight", 0.0)),
        )

    sem_data = data.get("semantics", {})
    classes_dict = sem_data.get("classes", {})
    classes: Dict[int, SemanticClassInfo] = {}
    for cid_raw, c_info in classes_dict.items():
        cid = int(cid_raw)
        classes[cid] = SemanticClassInfo(
            id=cid,
            name=c_info.get("name", f"CLASS_{cid}"),
            description=c_info.get("description", ""),
            is_obstacle=bool(c_info.get("is_obstacle", False)),
            is_ground=bool(c_info.get("is_ground", False)),
            default_traversable=bool(c_info.get("default_traversable", False)),
        )
    sem_cfg = SemanticTaxonomyConfig(
        num_classes=int(sem_data.get("num_classes", len(classes) or 8)),
        classes=classes if classes else SemanticTaxonomyConfig().classes,
    )

    prep_data = data.get("preprocessing", {})
    prep_cfg = PreprocessingConfig(
        crop_box=prep_data.get("crop_box", PreprocessingConfig().crop_box),
        filter_nans=bool(prep_data.get("filter_nans", True)),
        min_intensity=float(prep_data.get("min_intensity", 0.0)),
        max_intensity=float(prep_data.get("max_intensity", 255.0)),
    )

    map_data = data.get("mapping", {})
    trav_data = map_data.get("traversability", {})
    map_cfg = MappingConfig(
        temporal_decay_factor=float(map_data.get("temporal_decay_factor", 0.95)),
        max_points_per_cell=int(map_data.get("max_points_per_cell", 500)),
        occupancy_threshold=float(map_data.get("occupancy_threshold", 0.5)),
        ground_elevation_default=float(map_data.get("ground_elevation_default", 0.0)),
        max_step_height_m=float(trav_data.get("max_step_height_m", 0.15)),
        max_slope_rad=float(trav_data.get("max_slope_rad", 0.35)),
        roughness_threshold_m=float(trav_data.get("roughness_threshold_m", 0.05)),
    )

    # Runtime and telemetry configuration
    runtime_data = data.get("runtime", data.get("performance", {}))
    runtime_cfg = RuntimeConfig(
        enable_telemetry=bool(runtime_data.get("enable_telemetry", True)),
        timer_backend=str(runtime_data.get("timer_backend", "time.perf_counter")),
        warmup_frames=int(runtime_data.get("warmup_frames", 10)),
        profile_memory=bool(runtime_data.get("profile_memory", True)),
    )

    vis_data = data.get("visualization", {})
    vis_cfg = VisualizationConfig(
        window_title=vis_data.get("window_title", "Autonomous Perception Control Center - 2.5D Foveated LiDAR"),
        default_view_mode=vis_data.get("default_view_mode", "FOVEATED_SEMANTIC_ELEVATION"),
        color_map=vis_data.get("color_map", "ACCENT"),
    )

    sys_config = SystemConfig(
        version=data.get("version", "1.0.0"),
        coordinate_system=coord_cfg,
        foveation=fov_cfg,
        semantics=sem_cfg,
        preprocessing=prep_cfg,
        mapping=map_cfg,
        runtime=runtime_cfg,
        visualization=vis_cfg,
    )
    sys_config.validate()
    return sys_config
