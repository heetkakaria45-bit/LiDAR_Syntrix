export interface SemanticClassInfo {
  id: number;
  name: string;
  label: string;
  description: string;
  isTraversable: boolean;
  color: string; // hex
  colorRgb: [number, number, number];
  priorityWeight: number;
}

export const SEMANTIC_CLASSES: Record<number, SemanticClassInfo> = {
  0: {
    id: 0,
    name: 'DRIVABLE_GROUND',
    label: 'Drivable Road',
    description: 'Asphalt, smooth drivable road & parking surfaces',
    isTraversable: true,
    color: '#804080',
    colorRgb: [128, 64, 128],
    priorityWeight: 0.1,
  },
  1: {
    id: 1,
    name: 'NON_DRIVABLE_TERRAIN',
    label: 'Sidewalk / Terrain',
    description: 'Grass, dirt, gravel, rough unpaved ground, sidewalk',
    isTraversable: false,
    color: '#006400',
    colorRgb: [0, 100, 0],
    priorityWeight: 0.4,
  },
  2: {
    id: 2,
    name: 'VEHICLE',
    label: 'Vehicle',
    description: 'Cars, trucks, buses, vans',
    isTraversable: false,
    color: '#0055ff',
    colorRgb: [0, 85, 255],
    priorityWeight: 0.9,
  },
  3: {
    id: 3,
    name: 'PEDESTRIAN',
    label: 'Pedestrian',
    description: 'Walking people, dynamic vulnerable humans',
    isTraversable: false,
    color: '#dc143c',
    colorRgb: [220, 20, 60],
    priorityWeight: 1.0,
  },
  4: {
    id: 4,
    name: 'CYCLIST',
    label: 'Cyclist / Biker',
    description: 'Bicyclists, motorcyclists',
    isTraversable: false,
    color: '#ff3333',
    colorRgb: [255, 51, 51],
    priorityWeight: 1.0,
  },
  5: {
    id: 5,
    name: 'POLE',
    label: 'Pole / Trunk',
    description: 'Traffic signs, light poles, tree trunks',
    isTraversable: false,
    color: '#999999',
    colorRgb: [153, 153, 153],
    priorityWeight: 0.6,
  },
  6: {
    id: 6,
    name: 'WALL_BUILDING',
    label: 'Wall / Structure',
    description: 'Buildings, walls, concrete barriers, fences',
    isTraversable: false,
    color: '#464646',
    colorRgb: [70, 70, 70],
    priorityWeight: 0.5,
  },
  7: {
    id: 7,
    name: 'OTHER_OBSTACLE',
    label: 'Other Obstacle',
    description: 'Debris, unclassified hazards, temporary barriers',
    isTraversable: false,
    color: '#faaa1e',
    colorRgb: [250, 170, 30],
    priorityWeight: 0.7,
  },
};

export interface FoveationRing {
  id: number;
  name: string;
  label: string;
  minRange: number;
  maxRange: number;
  resolution: number; // meters per cell
  description: string;
  color: string;
}

export const FOVEATION_RINGS: FoveationRing[] = [
  {
    id: 0,
    name: 'near',
    label: 'Ring 0: Near Zone',
    minRange: 0.0,
    maxRange: 10.0,
    resolution: 0.05,
    description: 'High-res immediate vehicle vicinity (5 cm)',
    color: '#00ff9d',
  },
  {
    id: 1,
    name: 'mid_near',
    label: 'Ring 1: Mid-Near',
    minRange: 10.0,
    maxRange: 25.0,
    resolution: 0.10,
    description: 'Tactical maneuvering zone (10 cm)',
    color: '#00f0ff',
  },
  {
    id: 2,
    name: 'mid',
    label: 'Ring 2: Mid Range',
    minRange: 25.0,
    maxRange: 50.0,
    resolution: 0.25,
    description: 'Intermediate perception zone (25 cm)',
    color: '#8b5cf6',
  },
  {
    id: 3,
    name: 'far',
    label: 'Ring 3: Far Horizon',
    minRange: 50.0,
    maxRange: 100.0,
    resolution: 0.50,
    description: 'Coarse long-range horizon zone (50 cm)',
    color: '#ec4899',
  },
];

export interface GridCellData {
  resolution_level: string;
  cell_x: number;
  cell_y: number;
  elevation: number;
  min_z: number;
  max_z: number;
  semantic_class: number;
  confidence: number;
  point_count: number;
  roughness: number;
  uncertainty?: number;
  occupancy?: number;
}

export interface HazardItem {
  id: string;
  type: 'curb' | 'pothole' | 'overhang' | 'dynamic_obstacle';
  x: number;
  y: number;
  z: number;
  severity: number; // 0..1
  details: string;
  step_height?: number; // for curb (m)
  depth?: number; // for pothole (m)
  clearance?: number; // for overhang (m)
  velocity?: [number, number, number];
}

export interface BoundingBox {
  id: string;
  classId: number;
  className: string;
  center: [number, number, number]; // x, y, z
  size: [number, number, number]; // dx, dy, dz
  rotation: number; // yaw in rad
  confidence: number;
  velocity?: [number, number, number];
}

export interface PipelineStageLatency {
  preprocessing: number;
  inference: number;
  grid_indexing: number;
  mapping: number;
  hazard_analysis: number;
}

export interface TelemetryData {
  fps: number;
  latency_ms: number;
  total_time_ms: number;
  point_count: number;
  cell_count: number;
  memory_rss_mb: number;
  memory_savings_pct: number;
  compression_ratio: number;
  pipeline_mode: string;
  frame_count: number;
  stage_latencies: PipelineStageLatency;
  hazards: {
    curb_count: number;
    pothole_count: number;
    overhang_count: number;
    obstacle_count: number;
  };
}

export interface FramePayload {
  timestamp: number;
  frame_id: string;
  points: number[][]; // [x, y, z]
  semantic_classes: number[];
  intensity?: number[];
  cells: Record<string, GridCellData>;
  boundingBoxes?: BoundingBox[];
  hazards?: HazardItem[];
  telemetry: TelemetryData;
}

export type ColorMode = 'foveated' | 'semantic' | 'elevation' | 'traversability' | 'intensity' | 'occupancy' | 'terrain_3d' | 'anomaly_3d';
export type ScenarioType = 'urban' | 'highway' | 'offroad' | 'hazard_course' | 'pedestrian_cross' | 'slope_overhang';
export type CameraViewPreset = 'birds_eye' | 'ego_follow' | 'cockpit' | 'isometric' | 'free';
export type VideoBgMode = 'ambient' | 'pip' | 'off';

export interface PipelineStageInfo {
  stage_id: number;
  name: string;
  owner: string;
  module: string;
  input: string;
  output: string;
  resolution: string;
  status: 'ONLINE' | 'ACTIVE' | 'PROCESSING' | 'STANDBY';
}
