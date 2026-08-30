"""Deterministic Synthetic Scene Generator for LiDAR Simulation & Testing.

Provides synthetic geometric point clouds representing urban road scenes:
    - Flat road
    - Slopes & ramps
    - Road curbs (8-25 cm step changes)
    - Potholes (negative road depressions)
    - Vehicles (box bounding obstacles)
    - Pedestrians (cylindrical clusters)
    - Poles & trees
    - Walls & building facades
    - Overhead bridges / overhanging structures

Enables all 6 developers to test perception, spatial indexing, mapping,
integration, and benchmarking deterministically before live datasets are ingested.
"""

from typing import Optional, Tuple
import numpy as np

from src.contracts import PointCloudFrame, SemanticPointCloud, SyntheticSceneConfig


def generate_synthetic_scene(
    config: Optional[SyntheticSceneConfig] = None,
) -> Tuple[PointCloudFrame, SemanticPointCloud]:
    """Generate a deterministic synthetic LiDAR scene complying with project contracts.

    Returns:
        frame: PointCloudFrame with (N, 3) points, intensity, timestamp, and frame_id.
        semantic_cloud: Matching SemanticPointCloud with ground truth classes and confidences.
    """
    if config is None:
        config = SyntheticSceneConfig()

    rng = np.random.default_rng(config.seed)
    scene_type = config.scene_type

    if scene_type == "flat_road":
        points, classes = _generate_flat_road(config, rng)
    elif scene_type == "curb":
        points, classes = _generate_curb_scene(config, rng)
    elif scene_type == "pothole":
        points, classes = _generate_pothole_scene(config, rng)
    elif scene_type == "slope":
        points, classes = _generate_slope_scene(config, rng)
    elif scene_type == "overhang":
        points, classes = _generate_overhang_scene(config, rng)
    else:
        # Default comprehensive multi-obstacle urban scene
        points, classes = _generate_urban_scene(config, rng)

    n_points = points.shape[0]
    # Simulated calibrated intensity: road ~0.2, curbs/poles ~0.6, vehicles ~0.8
    intensity = np.zeros((n_points,), dtype=np.float32)
    intensity[classes == 0] = 0.25  # DRIVABLE_GROUND
    intensity[classes == 1] = 0.15  # NON_DRIVABLE_TERRAIN
    intensity[classes == 2] = 0.85  # VEHICLE
    intensity[classes == 3] = 0.40  # PEDESTRIAN
    intensity[classes == 5] = 0.70  # POLE
    intensity[classes == 6] = 0.50  # WALL_BUILDING

    # Ground truth confidence is 1.0
    confidence = np.ones((n_points,), dtype=np.float32)
    timestamp = 1700000000.0
    frame_id = "synthetic_lidar"

    frame = PointCloudFrame(
        points=points,
        intensity=intensity,
        timestamp=timestamp,
        frame_id=frame_id,
        sensor_pose=np.eye(4, dtype=np.float64),
    )

    semantic_cloud = SemanticPointCloud(
        points=points,
        semantic_class=classes,
        confidence=confidence,
        timestamp=timestamp,
        frame_id=frame_id,
        intensity=intensity,
    )

    return frame, semantic_cloud


def _generate_flat_road(
    cfg: SyntheticSceneConfig, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate planar horizontal road surface (class 0)."""
    n = cfg.num_points
    x = rng.uniform(0.5, 60.0, n).astype(np.float32)
    y = rng.uniform(-cfg.road_width / 2.0, cfg.road_width / 2.0, n).astype(np.float32)
    z = rng.normal(0.0, cfg.noise_std, n).astype(np.float32)

    points = np.stack([x, y, z], axis=1)
    classes = np.zeros((n,), dtype=np.int32)  # DRIVABLE_GROUND
    return points, classes


def _generate_curb_scene(
    cfg: SyntheticSceneConfig, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate drivable road with an elevated sidewalk curb at y = +road_width/2."""
    n = cfg.num_points
    half_w = cfg.road_width / 2.0
    x = rng.uniform(1.0, 40.0, n).astype(np.float32)
    y = rng.uniform(-half_w, half_w + 3.0, n).astype(np.float32)
    z = np.zeros((n,), dtype=np.float32)
    classes = np.zeros((n,), dtype=np.int32)

    # Road points (y <= half_w) are at elevation 0
    # Sidewalk points (y > half_w) are elevated by curb_height (e.g. 0.15m)
    sidewalk_mask = y > half_w
    z[sidewalk_mask] = cfg.curb_height
    classes[sidewalk_mask] = 1  # NON_DRIVABLE_TERRAIN

    z += rng.normal(0.0, cfg.noise_std, n).astype(np.float32)
    points = np.stack([x, y, z], axis=1)
    return points, classes


def _generate_pothole_scene(
    cfg: SyntheticSceneConfig, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate drivable road with a depressed circular pothole centered at (x=15m, y=0m)."""
    n = cfg.num_points
    x = rng.uniform(1.0, 30.0, n).astype(np.float32)
    y = rng.uniform(-4.0, 4.0, n).astype(np.float32)
    z = rng.normal(0.0, cfg.noise_std, n).astype(np.float32)
    classes = np.zeros((n,), dtype=np.int32)

    # Pothole centered at (15.0, 0.0) with radius 0.8m and depth pothole_depth
    pothole_radius = 0.8
    dist_sq = (x - 15.0) ** 2 + y**2
    pothole_mask = dist_sq < pothole_radius**2
    z[pothole_mask] -= cfg.pothole_depth
    classes[pothole_mask] = 7  # OTHER_OBSTACLE / hazard

    points = np.stack([x, y, z], axis=1)
    return points, classes


def _generate_slope_scene(
    cfg: SyntheticSceneConfig, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate inclined ramp/slope along forward axis."""
    n = cfg.num_points
    x = rng.uniform(0.5, 40.0, n).astype(np.float32)
    y = rng.uniform(-4.0, 4.0, n).astype(np.float32)

    slope_rad = np.radians(cfg.slope_deg)
    z = (x * np.tan(slope_rad) + rng.normal(0.0, cfg.noise_std, n)).astype(np.float32)

    classes = np.zeros((n,), dtype=np.int32)
    points = np.stack([x, y, z], axis=1)
    return points, classes


def _generate_overhang_scene(
    cfg: SyntheticSceneConfig, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate ground road with an overhead bridge structure at z = 3.5m."""
    n_ground = int(cfg.num_points * 0.7)
    n_overhang = cfg.num_points - n_ground

    # Ground road
    xg = rng.uniform(1.0, 40.0, n_ground).astype(np.float32)
    yg = rng.uniform(-4.0, 4.0, n_ground).astype(np.float32)
    zg = rng.normal(0.0, cfg.noise_std, n_ground).astype(np.float32)
    cg = np.zeros((n_ground,), dtype=np.int32)

    # Overhang slab located across x in [18m, 24m] at height 3.5m
    xo = rng.uniform(18.0, 24.0, n_overhang).astype(np.float32)
    yo = rng.uniform(-6.0, 6.0, n_overhang).astype(np.float32)
    zo = (3.5 + rng.normal(0.0, cfg.noise_std, n_overhang)).astype(np.float32)
    co = np.full((n_overhang,), 6, dtype=np.int32)  # WALL_BUILDING / structural

    points = np.vstack([np.stack([xg, yg, zg], axis=1), np.stack([xo, yo, zo], axis=1)])
    classes = np.concatenate([cg, co])
    return points, classes


def _generate_urban_scene(
    cfg: SyntheticSceneConfig, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate comprehensive urban scene: road, sidewalk, parked vehicle, pedestrian, pole."""
    pts_list = []
    cls_list = []

    # 1. Road (drivable ground)
    n_road = int(cfg.num_points * 0.6)
    xr = rng.uniform(0.5, 50.0, n_road).astype(np.float32)
    yr = rng.uniform(-4.0, 4.0, n_road).astype(np.float32)
    zr = rng.normal(0.0, cfg.noise_std, n_road).astype(np.float32)
    pts_list.append(np.stack([xr, yr, zr], axis=1))
    cls_list.append(np.zeros((n_road,), dtype=np.int32))

    # 2. Parked Vehicle at (x=12m, y=2.2m)
    n_veh = int(cfg.num_points * 0.2)
    xv = rng.uniform(10.0, 14.5, n_veh).astype(np.float32)
    yv = rng.uniform(1.4, 3.0, n_veh).astype(np.float32)
    zv = rng.uniform(0.1, 1.6, n_veh).astype(np.float32)
    pts_list.append(np.stack([xv, yv, zv], axis=1))
    cls_list.append(np.full((n_veh,), 2, dtype=np.int32))  # VEHICLE

    # 3. Pedestrian at (x=8m, y=-2.5m)
    n_ped = int(cfg.num_points * 0.1)
    xp = rng.normal(8.0, 0.25, n_ped).astype(np.float32)
    yp = rng.normal(-2.5, 0.25, n_ped).astype(np.float32)
    zp = rng.uniform(0.0, 1.75, n_ped).astype(np.float32)
    pts_list.append(np.stack([xp, yp, zp], axis=1))
    cls_list.append(np.full((n_ped,), 3, dtype=np.int32))  # PEDESTRIAN

    # 4. Pole at (x=18m, y=-4.5m)
    n_pole = cfg.num_points - (n_road + n_veh + n_ped)
    xpo = rng.normal(18.0, 0.1, n_pole).astype(np.float32)
    ypo = rng.normal(-4.5, 0.1, n_pole).astype(np.float32)
    zpo = rng.uniform(0.0, 4.0, n_pole).astype(np.float32)
    pts_list.append(np.stack([xpo, ypo, zpo], axis=1))
    cls_list.append(np.full((n_pole,), 5, dtype=np.int32))  # POLE

    points = np.vstack(pts_list)
    classes = np.concatenate(cls_list)
    return points, classes
