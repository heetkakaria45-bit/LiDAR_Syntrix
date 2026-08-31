"""
Dataset Adapters for External Autonomous Driving LiDAR Datasets.
Module Owner: Vedant (src/perception/)

Maps external dataset semantic labels (SemanticKITTI, nuScenes, Waymo, etc.)
into the frozen project taxonomy (0..7):
    0 = DRIVABLE_GROUND
    1 = NON_DRIVABLE_TERRAIN
    2 = VEHICLE
    3 = PEDESTRIAN
    4 = CYCLIST
    5 = POLE
    6 = WALL_BUILDING
    7 = OTHER_OBSTACLE
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, Union
import numpy as np

from src.common.types import PointCloudFrame, SemanticClass, SemanticPointCloud


class BaseDatasetAdapter(ABC):
    """Abstract base class for dataset adapters."""

    @abstractmethod
    def map_label(self, raw_label: int) -> int:
        """Maps a single dataset-specific label to project taxonomy (0..7)."""
        raise NotImplementedError

    @abstractmethod
    def map_labels(self, raw_labels: np.ndarray) -> np.ndarray:
        """Vectorized mapping of dataset-specific labels to project taxonomy."""
        raise NotImplementedError

    @abstractmethod
    def get_dataset_name(self) -> str:
        """Returns the canonical dataset name."""
        raise NotImplementedError


class SemanticKITTIAdapter(BaseDatasetAdapter):
    """
    SemanticKITTI Dataset Adapter.
    Maps SemanticKITTI raw label IDs (0..259) to the frozen project taxonomy.

    SemanticKITTI official label taxonomy reference:
        0: "unlabeled" -> OTHER_OBSTACLE (7)
        1: "outlier" -> OTHER_OBSTACLE (7)
        10: "car" -> VEHICLE (2)
        11: "bicycle" -> CYCLIST (4)
        13: "bus" -> VEHICLE (2)
        15: "motorcycle" -> CYCLIST (4)
        16: "on-rails" -> VEHICLE (2)
        18: "truck" -> VEHICLE (2)
        20: "other-vehicle" -> VEHICLE (2)
        30: "person" -> PEDESTRIAN (3)
        31: "bicyclist" -> CYCLIST (4)
        32: "motorcyclist" -> CYCLIST (4)
        40: "road" -> DRIVABLE_GROUND (0)
        44: "parking" -> DRIVABLE_GROUND (0)
        48: "sidewalk" -> NON_DRIVABLE_TERRAIN (1)
        49: "other-ground" -> NON_DRIVABLE_TERRAIN (1)
        50: "building" -> WALL_BUILDING (6)
        51: "fence" -> WALL_BUILDING (6)
        52: "other-structure" -> WALL_BUILDING (6)
        60: "lane-marking" -> DRIVABLE_GROUND (0)
        70: "vegetation" -> NON_DRIVABLE_TERRAIN (1)
        71: "trunk" -> POLE (5)
        72: "terrain" -> NON_DRIVABLE_TERRAIN (1)
        80: "pole" -> POLE (5)
        81: "traffic-sign" -> POLE (5)
        99: "other-object" -> OTHER_OBSTACLE (7)
        252: "moving-car" -> VEHICLE (2)
        253: "moving-bicyclist" -> CYCLIST (4)
        254: "moving-person" -> PEDESTRIAN (3)
        255: "moving-motorcyclist" -> CYCLIST (4)
        256: "moving-on-rails" -> VEHICLE (2)
        257: "moving-bus" -> VEHICLE (2)
        258: "moving-truck" -> VEHICLE (2)
        259: "moving-other-ground" -> NON_DRIVABLE_TERRAIN (1)
    """

    LABEL_MAP: Dict[int, int] = {
        0: SemanticClass.OTHER_OBSTACLE,       # unlabeled
        1: SemanticClass.OTHER_OBSTACLE,       # outlier
        10: SemanticClass.VEHICLE,             # car
        11: SemanticClass.CYCLIST,             # bicycle
        13: SemanticClass.VEHICLE,             # bus
        15: SemanticClass.CYCLIST,             # motorcycle
        16: SemanticClass.VEHICLE,             # on-rails
        18: SemanticClass.VEHICLE,             # truck
        20: SemanticClass.VEHICLE,             # other-vehicle
        30: SemanticClass.PEDESTRIAN,          # person
        31: SemanticClass.CYCLIST,             # bicyclist
        32: SemanticClass.CYCLIST,             # motorcyclist
        40: SemanticClass.DRIVABLE_GROUND,      # road
        44: SemanticClass.DRIVABLE_GROUND,      # parking
        48: SemanticClass.NON_DRIVABLE_TERRAIN, # sidewalk
        49: SemanticClass.NON_DRIVABLE_TERRAIN, # other-ground
        50: SemanticClass.WALL_BUILDING,        # building
        51: SemanticClass.WALL_BUILDING,        # fence
        52: SemanticClass.WALL_BUILDING,        # other-structure
        60: SemanticClass.DRIVABLE_GROUND,      # lane-marking
        70: SemanticClass.NON_DRIVABLE_TERRAIN, # vegetation
        71: SemanticClass.POLE,                 # trunk
        72: SemanticClass.NON_DRIVABLE_TERRAIN, # terrain
        80: SemanticClass.POLE,                 # pole
        81: SemanticClass.POLE,                 # traffic-sign
        99: SemanticClass.OTHER_OBSTACLE,       # other-object
        252: SemanticClass.VEHICLE,            # moving-car
        253: SemanticClass.CYCLIST,            # moving-bicyclist
        254: SemanticClass.PEDESTRIAN,         # moving-person
        255: SemanticClass.CYCLIST,            # moving-motorcyclist
        256: SemanticClass.VEHICLE,            # moving-on-rails
        257: SemanticClass.VEHICLE,            # moving-bus
        258: SemanticClass.VEHICLE,            # moving-truck
        259: SemanticClass.NON_DRIVABLE_TERRAIN,# moving-other-ground
    }

    def __init__(self) -> None:
        self._lut = np.full(512, SemanticClass.OTHER_OBSTACLE, dtype=np.uint8)
        for src_id, dst_id in self.LABEL_MAP.items():
            if src_id < 512:
                self._lut[src_id] = dst_id

    def get_dataset_name(self) -> str:
        return "SemanticKITTI"

    def map_label(self, raw_label: int) -> int:
        class_id = raw_label & 0xFFFF
        return int(self.LABEL_MAP.get(class_id, SemanticClass.OTHER_OBSTACLE))

    def map_labels(self, raw_labels: np.ndarray) -> np.ndarray:
        if raw_labels.size == 0:
            return np.zeros(0, dtype=np.uint8)
        class_ids = (raw_labels & 0xFFFF).astype(np.int64)
        mask = (class_ids >= 0) & (class_ids < 512)
        mapped = np.full(raw_labels.shape, SemanticClass.OTHER_OBSTACLE, dtype=np.uint8)
        mapped[mask] = self._lut[class_ids[mask]]
        return mapped


class NuScenesAdapter(BaseDatasetAdapter):
    """
    nuScenes-lidarseg Dataset Adapter.
    Supports official 32-class nuScenes lidarseg IDs and 16-class challenges.
    """

    LABEL_MAP: Dict[int, int] = {
        0: SemanticClass.OTHER_OBSTACLE,        # noise
        1: SemanticClass.OTHER_OBSTACLE,        # animal / barrier
        2: SemanticClass.PEDESTRIAN,            # human.pedestrian.adult
        3: SemanticClass.PEDESTRIAN,            # human.pedestrian.child
        4: SemanticClass.PEDESTRIAN,            # human.pedestrian.construction_worker
        5: SemanticClass.PEDESTRIAN,            # human.pedestrian.personal_mobility
        6: SemanticClass.PEDESTRIAN,            # human.pedestrian.police_officer
        7: SemanticClass.OTHER_OBSTACLE,        # human.pedestrian.stroller
        8: SemanticClass.OTHER_OBSTACLE,        # human.pedestrian.wheelchair / traffic_cone
        9: SemanticClass.OTHER_OBSTACLE,        # movable_object.barrier / trailer
        10: SemanticClass.OTHER_OBSTACLE,       # movable_object.debris / truck
        11: SemanticClass.OTHER_OBSTACLE,       # movable_object.pushable_pullable
        12: SemanticClass.OTHER_OBSTACLE,       # movable_object.trafficcone
        13: SemanticClass.OTHER_OBSTACLE,       # static_object.bicycle_rack
        14: SemanticClass.CYCLIST,              # vehicle.bicycle
        15: SemanticClass.VEHICLE,              # vehicle.bus.bendy
        16: SemanticClass.VEHICLE,              # vehicle.bus.rigid
        17: SemanticClass.VEHICLE,              # vehicle.car
        18: SemanticClass.VEHICLE,              # vehicle.construction
        19: SemanticClass.VEHICLE,              # vehicle.emergency.ambulance
        20: SemanticClass.VEHICLE,              # vehicle.emergency.police
        21: SemanticClass.CYCLIST,              # vehicle.motorcycle
        22: SemanticClass.VEHICLE,              # vehicle.trailer
        23: SemanticClass.VEHICLE,              # vehicle.truck
        24: SemanticClass.DRIVABLE_GROUND,      # flat.driveable_surface
        25: SemanticClass.DRIVABLE_GROUND,      # flat.other
        26: SemanticClass.NON_DRIVABLE_TERRAIN, # flat.sidewalk
        27: SemanticClass.NON_DRIVABLE_TERRAIN, # flat.terrain
        28: SemanticClass.WALL_BUILDING,        # static.manmade
        29: SemanticClass.OTHER_OBSTACLE,       # static.other
        30: SemanticClass.NON_DRIVABLE_TERRAIN, # static.vegetation
        31: SemanticClass.OTHER_OBSTACLE,       # vehicle.ego
    }

    def __init__(self) -> None:
        self._lut = np.full(64, SemanticClass.OTHER_OBSTACLE, dtype=np.uint8)
        for src_id, dst_id in self.LABEL_MAP.items():
            if src_id < 64:
                self._lut[src_id] = dst_id

    def get_dataset_name(self) -> str:
        return "nuScenes"

    def map_label(self, raw_label: int) -> int:
        return int(self.LABEL_MAP.get(raw_label, SemanticClass.OTHER_OBSTACLE))

    def map_labels(self, raw_labels: np.ndarray) -> np.ndarray:
        if raw_labels.size == 0:
            return np.zeros(0, dtype=np.uint8)
        mask = (raw_labels >= 0) & (raw_labels < 64)
        mapped = np.full(raw_labels.shape, SemanticClass.OTHER_OBSTACLE, dtype=np.uint8)
        mapped[mask] = self._lut[raw_labels[mask]]
        return mapped


class WaymoDatasetAdapter(BaseDatasetAdapter):
    """
    Waymo Open Dataset LiDAR Segmentation Adapter.
    Maps Waymo segmentation IDs (0..22) to project taxonomy.
    """

    LABEL_MAP: Dict[int, int] = {
        0: SemanticClass.OTHER_OBSTACLE,        # TYPE_UNDEFINED
        1: SemanticClass.VEHICLE,               # TYPE_CAR
        2: SemanticClass.VEHICLE,               # TYPE_TRUCK
        3: SemanticClass.VEHICLE,               # TYPE_BUS
        4: SemanticClass.VEHICLE,               # TYPE_OTHER_VEHICLE
        5: SemanticClass.CYCLIST,               # TYPE_MOTORCYCLIST
        6: SemanticClass.CYCLIST,               # TYPE_BICYCLIST
        7: SemanticClass.PEDESTRIAN,            # TYPE_PEDESTRIAN
        8: SemanticClass.POLE,                  # TYPE_SIGN
        9: SemanticClass.POLE,                  # TYPE_TRAFFIC_LIGHT
        10: SemanticClass.POLE,                 # TYPE_POLE
        11: SemanticClass.OTHER_OBSTACLE,       # TYPE_CONSTRUCTION_CONE
        12: SemanticClass.CYCLIST,              # TYPE_BICYCLE
        13: SemanticClass.CYCLIST,              # TYPE_MOTORCYCLE
        14: SemanticClass.WALL_BUILDING,        # TYPE_BUILDING
        15: SemanticClass.NON_DRIVABLE_TERRAIN, # TYPE_VEGETATION
        16: SemanticClass.POLE,                 # TYPE_TREE_TRUNK
        17: SemanticClass.OTHER_OBSTACLE,       # TYPE_CURB
        18: SemanticClass.DRIVABLE_GROUND,      # TYPE_ROAD
        19: SemanticClass.DRIVABLE_GROUND,      # TYPE_LANE_MARKER
        20: SemanticClass.OTHER_OBSTACLE,       # TYPE_OTHER_GROUND
        21: SemanticClass.NON_DRIVABLE_TERRAIN, # TYPE_WALKABLE (sidewalk)
        22: SemanticClass.NON_DRIVABLE_TERRAIN, # TYPE_OTHER_TERRAIN
    }

    def __init__(self) -> None:
        self._lut = np.full(64, SemanticClass.OTHER_OBSTACLE, dtype=np.uint8)
        for src_id, dst_id in self.LABEL_MAP.items():
            if src_id < 64:
                self._lut[src_id] = dst_id

    def get_dataset_name(self) -> str:
        return "Waymo"

    def map_label(self, raw_label: int) -> int:
        return int(self.LABEL_MAP.get(raw_label, SemanticClass.OTHER_OBSTACLE))

    def map_labels(self, raw_labels: np.ndarray) -> np.ndarray:
        if raw_labels.size == 0:
            return np.zeros(0, dtype=np.uint8)
        mask = (raw_labels >= 0) & (raw_labels < 64)
        mapped = np.full(raw_labels.shape, SemanticClass.OTHER_OBSTACLE, dtype=np.uint8)
        mapped[mask] = self._lut[raw_labels[mask]]
        return mapped


def get_adapter(dataset_name: str) -> BaseDatasetAdapter:
    """Factory helper to obtain the appropriate dataset adapter."""
    name_lower = dataset_name.lower().replace("_", "").replace("-", "")
    if "kitti" in name_lower:
        return SemanticKITTIAdapter()
    elif "nuscene" in name_lower:
        return NuScenesAdapter()
    elif "waymo" in name_lower:
        return WaymoDatasetAdapter()
    raise ValueError(f"Unknown dataset name '{dataset_name}'. Supported: 'kitti', 'nuscenes', 'waymo'.")
