import { FramePayload, GridCellData, BoundingBox, HazardItem, ScenarioType, FOVEATION_RINGS } from '../types';
import { TeleopState } from '../components/teleop/TeleopConsole';

/**
 * Procedural infinite-world autonomous LiDAR & Foveated Grid simulation engine.
 * Generates continuous streaming roads, sidewalks, buildings, traffic, slow walking pedestrians,
 * wildlife creatures, bus stops, crosswalks, and multiple detected road potholes up to 100m range.
 */
export class SimulationEngine {
  private frameCount = 0;
  private scenario: ScenarioType = 'urban';
  private distanceTraveled = 0; // meters
  private egoSpeed = 8.0; // m/s (~28.8 km/h)
  private steerAngle = 0; // deg
  private targetSpeed = 8.0;

  constructor(initialScenario: ScenarioType = 'urban') {
    this.scenario = initialScenario;
  }

  public setScenario(sc: ScenarioType) {
    this.scenario = sc;
    this.frameCount = 0;
    this.distanceTraveled = 0;
  }

  public updateTeleop(teleop: Partial<TeleopState>) {
    if (teleop.speed !== undefined) this.egoSpeed = teleop.speed;
    if (teleop.steerAngle !== undefined) this.steerAngle = teleop.steerAngle;
    if (teleop.targetSpeedKmh !== undefined) this.targetSpeed = teleop.targetSpeedKmh / 3.6;
    if (teleop.distanceTraveled !== undefined) this.distanceTraveled = teleop.distanceTraveled;
  }

  public generateFrame(teleop?: TeleopState): FramePayload {
    this.frameCount++;
    const dt = 0.05;

    if (teleop) {
      this.egoSpeed = teleop.speed;
      this.steerAngle = teleop.steerAngle;
      this.distanceTraveled = teleop.distanceTraveled;
    } else {
      this.distanceTraveled += this.egoSpeed * dt;
    }

    const t = this.frameCount * 0.08;
    const currentDist = this.distanceTraveled;

    const points: number[][] = [];
    const classes: number[] = [];
    const intensity: number[] = [];
    const boundingBoxes: BoundingBox[] = [];
    const hazards: HazardItem[] = [];
    const cells: Record<string, GridCellData> = {};

    // Generate Infinite Procedural Urban Environment, Traffic, Potholes & Dynamic Actors
    this.populateInfiniteWorld(t, currentDist, points, classes, intensity, boundingBoxes, hazards);

    // Compute Foveated Multi-Ring 2.5D Elevation & Semantic Grid
    this.aggregateFoveatedGrid(points, classes, cells);

    // Hazard metrics
    const curbCount = hazards.filter((h) => h.type === 'curb').length;
    const potholeCount = hazards.filter((h) => h.type === 'pothole').length;
    const overhangCount = hazards.filter((h) => h.type === 'overhang').length;
    const obstacleCount = boundingBoxes.length;

    // Profiling
    const prepLatency = 2.8 + Math.sin(t * 1.5) * 0.4;
    const inferLatency = 8.5 + Math.cos(t * 0.8) * 0.9;
    const indexLatency = 2.1 + Math.sin(t * 2.1) * 0.3;
    const mapLatency = 3.6 + Math.cos(t * 1.2) * 0.5;
    const hazardLatency = 1.4 + Math.sin(t * 0.9) * 0.2;
    const totalLatency = prepLatency + inferLatency + indexLatency + mapLatency + hazardLatency;
    const fps = Math.min(60, Math.max(30, 1000 / totalLatency));

    const uniformCellsCount = 400000;
    const foveatedCellsCount = Object.keys(cells).length;
    const memoryUniformMb = ((uniformCellsCount * 64) / (1024 * 1024)) * 4;
    const memoryFoveatedMb = Math.max(3.8, ((foveatedCellsCount * 64) / (1024 * 1024)) * 3.5);
    const memorySavingsPct = Number((((memoryUniformMb - memoryFoveatedMb) / memoryUniformMb) * 100).toFixed(1));
    const compressionRatio = Number((memoryUniformMb / memoryFoveatedMb).toFixed(1));

    return {
      timestamp: Date.now() / 1000,
      frame_id: `FRAME_${String(this.frameCount).padStart(5, '0')}`,
      points,
      semantic_classes: classes,
      intensity,
      cells,
      boundingBoxes,
      hazards,
      telemetry: {
        fps: Number(fps.toFixed(1)),
        latency_ms: Number(totalLatency.toFixed(1)),
        total_time_ms: Number(totalLatency.toFixed(1)),
        point_count: points.length,
        cell_count: foveatedCellsCount,
        memory_rss_mb: Number(memoryFoveatedMb.toFixed(2)),
        memory_savings_pct: Math.min(97.8, Math.max(92.4, memorySavingsPct)),
        compression_ratio: Math.min(32, Math.max(16, compressionRatio)),
        pipeline_mode: 'ADAPTIVE_FOVEATED',
        frame_count: this.frameCount,
        stage_latencies: {
          preprocessing: Number(prepLatency.toFixed(2)),
          inference: Number(inferLatency.toFixed(2)),
          grid_indexing: Number(indexLatency.toFixed(2)),
          mapping: Number(mapLatency.toFixed(2)),
          hazard_analysis: Number(hazardLatency.toFixed(2)),
        },
        hazards: {
          curb_count: curbCount,
          pothole_count: potholeCount,
          overhang_count: overhangCount,
          obstacle_count: obstacleCount,
        },
      },
    };
  }

  private populateInfiniteWorld(
    t: number,
    distTraveled: number,
    points: number[][],
    classes: number[],
    intensity: number[],
    boxes: BoundingBox[],
    hazards: HazardItem[]
  ) {
    const numPoints = 9200;
    const roadWidth = 9.0;
    const curbHeight = 0.16;

    // Periodic road feature cycles
    const crosswalkSpacing = 65.0;
    const crosswalkRelX = ((crosswalkSpacing - (distTraveled % crosswalkSpacing)) % crosswalkSpacing);

    const busStopSpacing = 85.0;
    const busStopRelX = ((busStopSpacing - (distTraveled % busStopSpacing)) % busStopSpacing);

    // Multiple Potholes along the road (placed at distinct relative offsets)
    const potholeConfigs = [
      { baseDist: 25.0, laneY: 1.6, depth: 0.14, radius: 1.1 },
      { baseDist: 55.0, laneY: -1.8, depth: 0.12, radius: 0.9 },
      { baseDist: 90.0, laneY: 0.8, depth: 0.15, radius: 1.2 },
    ];

    const activePotholes = potholeConfigs.map((cfg, idx) => {
      const cycle = 80.0;
      const relX = ((cfg.baseDist + cycle - (distTraveled % cycle)) % cycle);
      return {
        id: `hz-pothole-${idx + 1}`,
        relX,
        y: cfg.laneY,
        depth: cfg.depth,
        radius: cfg.radius,
      };
    });

    // Speed Breakers along the road (placed periodically every 45m)
    const speedBreakerConfigs = [
      { baseDist: 15.0, height: 0.08, width: 1.8 },
      { baseDist: 60.0, height: 0.08, width: 1.8 },
    ];

    const activeSpeedBreakers = speedBreakerConfigs.map((cfg, idx) => {
      const cycle = 90.0;
      const relX = ((cfg.baseDist + cycle - (distTraveled % cycle)) % cycle);
      return {
        id: `hz-speedbreaker-${idx + 1}`,
        relX,
        height: cfg.height,
        width: cfg.width,
      };
    });

    // 1. Drivable Road Surface, Sidewalks, Pothole Depressions & Speed Breakers
    for (let i = 0; i < numPoints * 0.42; i++) {
      const r = Math.pow(Math.random(), 1.5) * 85.0 + 0.5;
      const angle = (Math.random() - 0.5) * Math.PI * 1.9;
      const x = r * Math.cos(angle);
      const y = r * Math.sin(angle);

      let z = 0.0;
      let semClass = 0;
      let intens = 0.65;

      if (Math.abs(y) <= roadWidth / 2) {
        semClass = 0; // Road
        z = -0.015 * Math.sin(x * 0.04);
        intens = 0.6;

        // Zebra Crossing reflectance
        if (Math.abs(x - crosswalkRelX) < 2.0) {
          const stripe = Math.abs((y + 4.5) % 1.0);
          if (stripe < 0.55) intens = 0.98;
        }

        // Check if point falls inside any active pothole
        for (const ph of activePotholes) {
          const distToHole = Math.hypot(x - ph.relX, y - ph.y);
          if (distToHole < ph.radius) {
            const depression = Math.max(0, (ph.radius - distToHole) * (ph.depth / ph.radius));
            z -= depression;
            intens = 0.15; // Darker asphalt reflectance in crater
            break;
          }
        }

        // Check if point falls on an elevated speed breaker hump
        for (const sb of activeSpeedBreakers) {
          const dx = Math.abs(x - sb.relX);
          if (dx < sb.width / 2) {
            const hump = sb.height * Math.max(0, 1 - Math.pow(dx / (sb.width / 2), 2));
            z += hump;
            // High-visibility yellow/black stripe reflectance
            const stripe = Math.abs((y + 4.5) % 0.8);
            if (stripe < 0.4) intens = 0.96;
            break;
          }
        }
      } else if (Math.abs(y) <= roadWidth / 2 + 0.45) {
        semClass = 1; // Curb
        z = curbHeight + (Math.random() * 0.02);
        intens = 0.88;
      } else {
        semClass = 1; // Sidewalk / Terrain
        z = curbHeight + (Math.random() * 0.04);
        intens = 0.5;
      }

      z += (Math.random() - 0.5) * 0.015;
      points.push([x, y, z]);
      classes.push(semClass);
      intensity.push(intens);
    }

    // 2. Register Active Pothole & Speed Breaker Hazards for Detection & HUD
    activePotholes.forEach((ph) => {
      if (ph.relX > 1.5 && ph.relX < 60.0) {
        hazards.push({
          id: ph.id,
          type: 'pothole',
          x: Number(ph.relX.toFixed(2)),
          y: ph.y,
          z: -ph.depth,
          severity: Number((ph.depth / 0.15).toFixed(2)),
          depth: ph.depth,
          details: `Road depression (-${Math.round(ph.depth * 100)}cm) detected in lane`,
        });

        boxes.push({
          id: `box-${ph.id}`,
          classId: 7, // hazard marker
          className: `POTHOLE (-${Math.round(ph.depth * 100)}cm)`,
          center: [ph.relX, ph.y, -ph.depth / 2],
          size: [ph.radius * 2, ph.radius * 2, ph.depth + 0.1],
          rotation: 0,
          confidence: 0.96,
          velocity: [0, 0, 0],
        });
      }
    });

    activeSpeedBreakers.forEach((sb) => {
      if (sb.relX > 1.5 && sb.relX < 60.0) {
        hazards.push({
          id: sb.id,
          type: 'curb',
          x: Number(sb.relX.toFixed(2)),
          y: 0.0,
          z: sb.height,
          severity: 0.35,
          step_height: sb.height,
          details: `Traversable speed breaker (+${Math.round(sb.height * 100)}cm) traffic calming hump`,
        });
      }
    });

    // 3. Curb Hazards
    hazards.push({
      id: 'hz-curb-left',
      type: 'curb',
      x: 6.0,
      y: -4.5,
      z: curbHeight,
      severity: 0.65,
      step_height: curbHeight,
      details: 'Left road border curb (+16cm)',
    });
    hazards.push({
      id: 'hz-curb-right',
      type: 'curb',
      x: 6.0,
      y: 4.5,
      z: curbHeight,
      severity: 0.65,
      step_height: curbHeight,
      details: 'Right road border curb (+16cm)',
    });

    // 4. Procedural Buildings & Architectural Facades along Avenue
    const buildingBlockLength = 35.0;
    const buildingOffset = distTraveled % buildingBlockLength;

    for (let bIdx = -1; bIdx <= 3; bIdx++) {
      const bx = bIdx * buildingBlockLength - buildingOffset + 15.0;
      if (bx < -30 || bx > 90) continue;

      // Left Building
      const bLeftHeight = 8.0 + ((bIdx * 7) % 6);
      this.generateBoxPoints(points, classes, intensity, bx, -17.0, bLeftHeight / 2, 28.0, 12.0, bLeftHeight, 6, 260);

      // Right Building
      const bRightHeight = 9.0 + ((bIdx * 5) % 8);
      this.generateBoxPoints(points, classes, intensity, bx + 5.0, 17.5, bRightHeight / 2, 26.0, 11.0, bRightHeight, 6, 260);
    }

    // 5. Bus Stop Shelter with Passenger
    if (busStopRelX > -15 && busStopRelX < 75) {
      const bsX = busStopRelX;
      const bsY = 6.2;
      this.generateBoxPoints(points, classes, intensity, bsX, bsY, 2.7, 5.0, 2.2, 0.25, 6, 180);
      this.generateBoxPoints(points, classes, intensity, bsX, bsY + 0.9, 1.4, 4.8, 0.15, 2.4, 6, 140);
      this.generateBoxPoints(points, classes, intensity, bsX, bsY + 0.3, 0.45, 2.8, 0.5, 0.45, 6, 90);
      this.generateCylinderPoints(points, classes, intensity, bsX - 2.8, bsY - 0.6, 1.4, 0.08, 2.6, 5, 60);

      // Waiting passenger
      this.generateCylinderPoints(points, classes, intensity, bsX + 0.4, bsY + 0.2, 0.85, 0.3, 1.7, 3, 120);
      boxes.push({
        id: 'ped-bus-wait',
        classId: 3,
        className: 'PEDESTRIAN (WAITING)',
        center: [bsX + 0.4, bsY + 0.2, 0.85],
        size: [0.6, 0.6, 1.7],
        rotation: 0,
        confidence: 0.96,
        velocity: [0, 0, 0],
      });
    }

    // 6. Slow Walking Pedestrian on Zebra Crosswalk (Calm, Natural Speed ~0.85 m/s)
    // 6. Slow Walking Pedestrian on Zebra Crosswalk with Active Collision Avoidance
    // Oncoming Sedan in opposite left lane (Y = -2.4m, calm speed = 3.5 m/s)
    const car1X = 45.0 - ((t * 3.2 + distTraveled * 0.4) % 110);
    const car1Y = -2.4;

    if (crosswalkRelX > -10 && crosswalkRelX < 65) {
      // Check if oncoming car is close to the crosswalk
      const isCarNearCrosswalk = Math.abs(car1X - crosswalkRelX) < 7.0;
      
      // Calculate pedestrian position across crosswalk (one-way calm walk)
      let pedProgress = (t * 0.12) % 1.0;
      let pedY = -3.5 + pedProgress * 7.0;

      // If oncoming car is in the lane (Y around -2.4m) and near, pedestrian yields at current position
      const isPedNearLane = pedY < -0.8;
      const isYielding = isCarNearCrosswalk && isPedNearLane;

      if (isYielding) {
        pedY = -3.2; // Halt at road edge
      }

      this.generateCylinderPoints(points, classes, intensity, crosswalkRelX, pedY, 0.9, 0.32, 1.75, 3, 180);
      boxes.push({
        id: 'ped-crosswalk',
        classId: 3,
        className: isYielding ? 'PEDESTRIAN (YIELDING)' : 'PEDESTRIAN (CROSSING)',
        center: [crosswalkRelX, pedY, 0.9],
        size: [0.6, 0.6, 1.75],
        rotation: Math.PI / 2,
        confidence: 0.98,
        velocity: isYielding ? [0, 0, 0] : [0, 0.6, 0],
      });
    }

    // 7. Dynamic Traffic with Calm Urban Speeds (Never Collide)
    if (car1X > -25 && car1X < 85) {
      this.generateBoxPoints(points, classes, intensity, car1X, car1Y, 0.75, 4.6, 1.9, 1.45, 2, 360);
      boxes.push({
        id: 'veh-oncoming',
        classId: 2,
        className: 'SEDAN (ONCOMING)',
        center: [car1X, car1Y, 0.75],
        size: [4.6, 1.9, 1.45],
        rotation: Math.PI,
        confidence: 0.97,
        velocity: [-3.5, 0, 0],
      });
    }

    // Leading SUV in forward right lane (Y = +2.4m, safe following distance ahead)
    const car2X = 32.0;
    const car2Y = 2.4;
    this.generateBoxPoints(points, classes, intensity, car2X, car2Y, 0.9, 5.1, 2.1, 1.8, 2, 340);
    boxes.push({
      id: 'veh-leading',
      classId: 2,
      className: 'SUV (LEADING)',
      center: [car2X, car2Y, 0.9],
      size: [5.1, 2.1, 1.8],
      rotation: 0,
      confidence: 0.95,
      velocity: [3.0, 0, 0],
    });

    // 8. Wildlife Deer near roadside terrain
    const deerX = 28.0 + Math.sin(t * 0.25) * 1.2;
    const deerY = -8.2;
    this.generateBoxPoints(points, classes, intensity, deerX, deerY, 0.9, 1.6, 0.6, 1.0, 3, 140);
    this.generateCylinderPoints(points, classes, intensity, deerX + 0.7, deerY, 1.3, 0.2, 0.7, 3, 60);
    boxes.push({
      id: 'creature-deer-01',
      classId: 3,
      className: 'WILDLIFE (DEER)',
      center: [deerX, deerY, 0.9],
      size: [1.6, 0.6, 1.4],
      rotation: -Math.PI / 4,
      confidence: 0.91,
      velocity: [0.15, 0, 0],
    });

    // 9. Streetlights & Trees
    const poleSpacing = 24.0;
    const poleOffset = distTraveled % poleSpacing;
    for (let pIdx = -1; pIdx <= 4; pIdx++) {
      const px = pIdx * poleSpacing - poleOffset + 12.0;
      if (px < -25 || px > 85) continue;
      this.generateCylinderPoints(points, classes, intensity, px, -5.2, 2.8, 0.15, 5.6, 5, 70);
      this.generateCylinderPoints(points, classes, intensity, px, 5.2, 2.8, 0.15, 5.6, 5, 70);

      // Trees
      this.generateCylinderPoints(points, classes, intensity, px + 8.0, -7.0, 1.4, 0.22, 2.8, 5, 60);
      this.generateSpherePoints(points, classes, intensity, px + 8.0, -7.0, 3.8, 1.8, 5, 110);
      this.generateCylinderPoints(points, classes, intensity, px + 8.0, 7.0, 1.4, 0.22, 2.8, 5, 60);
      this.generateSpherePoints(points, classes, intensity, px + 8.0, 7.0, 3.8, 1.8, 5, 110);
    }
  }

  private generateBoxPoints(
    points: number[][],
    classes: number[],
    intensity: number[],
    cx: number, cy: number, cz: number,
    dx: number, dy: number, dz: number,
    cls: number,
    count: number
  ) {
    for (let i = 0; i < count; i++) {
      const face = Math.floor(Math.random() * 5);
      let x = cx;
      let y = cy;
      let z = cz;

      if (face === 0) {
        x = cx + (Math.random() - 0.5) * dx;
        y = cy - dy / 2;
        z = cz + (Math.random() - 0.5) * dz;
      } else if (face === 1) {
        x = cx + (Math.random() - 0.5) * dx;
        y = cy + dy / 2;
        z = cz + (Math.random() - 0.5) * dz;
      } else if (face === 2) {
        x = cx - dx / 2;
        y = cy + (Math.random() - 0.5) * dy;
        z = cz + (Math.random() - 0.5) * dz;
      } else if (face === 3) {
        x = cx + dx / 2;
        y = cy + (Math.random() - 0.5) * dy;
        z = cz + (Math.random() - 0.5) * dz;
      } else {
        x = cx + (Math.random() - 0.5) * dx;
        y = cy + (Math.random() - 0.5) * dy;
        z = cz + dz / 2;
      }

      points.push([x, y, z]);
      classes.push(cls);
      intensity.push(0.75 + Math.random() * 0.25);
    }
  }

  private generateCylinderPoints(
    points: number[][],
    classes: number[],
    intensity: number[],
    cx: number, cy: number, cz: number,
    radius: number,
    height: number,
    cls: number,
    count: number
  ) {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const z = cz - height / 2 + Math.random() * height;
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);

      points.push([x, y, z]);
      classes.push(cls);
      intensity.push(0.8);
    }
  }

  private generateSpherePoints(
    points: number[][],
    classes: number[],
    intensity: number[],
    cx: number, cy: number, cz: number,
    radius: number,
    cls: number,
    count: number
  ) {
    for (let i = 0; i < count; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = radius * (0.85 + Math.random() * 0.15);
      const x = cx + r * Math.sin(phi) * Math.cos(theta);
      const y = cy + r * Math.sin(phi) * Math.sin(theta);
      const z = cz + r * Math.cos(phi);

      points.push([x, y, z]);
      classes.push(cls);
      intensity.push(0.65);
    }
  }

  private aggregateFoveatedGrid(
    points: number[][],
    classes: number[],
    cells: Record<string, GridCellData>
  ) {
    const minZByCell: Record<string, number> = {};
    const maxZByCell: Record<string, number> = {};
    const sumZByCell: Record<string, number> = {};
    const countByCell: Record<string, number> = {};
    const classCountsByCell: Record<string, Record<number, number>> = {};
    const cellMeta: Record<
      string,
      { resName: string; resMeters: number; ringId: number; cx: number; cy: number }
    > = {};

    for (let i = 0; i < points.length; i++) {
      const [x, y, z] = points[i];
      const cls = classes[i] ?? 0;
      const dist = Math.hypot(x, y);

      let ringId = 3;
      let resName = 'far';
      let resMeters = 0.50;

      if (dist < 10) {
        ringId = 0; resName = 'near'; resMeters = 0.05;
      } else if (dist < 25) {
        ringId = 1; resName = 'mid_near'; resMeters = 0.10;
      } else if (dist < 50) {
        ringId = 2; resName = 'mid'; resMeters = 0.25;
      }

      const cellXIdx = Math.floor(x / resMeters);
      const cellYIdx = Math.floor(y / resMeters);
      const cellKey = `${resName}_${cellXIdx}_${cellYIdx}`;

      if (!countByCell[cellKey]) {
        countByCell[cellKey] = 0;
        minZByCell[cellKey] = z;
        maxZByCell[cellKey] = z;
        sumZByCell[cellKey] = 0;
        classCountsByCell[cellKey] = {};
        cellMeta[cellKey] = {
          resName,
          resMeters,
          ringId,
          cx: (cellXIdx + 0.5) * resMeters,
          cy: (cellYIdx + 0.5) * resMeters,
        };
      }

      countByCell[cellKey]++;
      sumZByCell[cellKey] += z;
      if (z < minZByCell[cellKey]) minZByCell[cellKey] = z;
      if (z > maxZByCell[cellKey]) maxZByCell[cellKey] = z;

      classCountsByCell[cellKey][cls] = (classCountsByCell[cellKey][cls] || 0) + 1;
    }

    for (const [key, cnt] of Object.entries(countByCell)) {
      const meta = cellMeta[key];
      const minZ = minZByCell[key];
      const maxZ = maxZByCell[key];
      const elev = sumZByCell[key] / cnt;

      let dominantClass = 0;
      let maxCnt = 0;
      for (const [c, count] of Object.entries(classCountsByCell[key])) {
        if (count > maxCnt) {
          maxCnt = count;
          dominantClass = parseInt(c);
        }
      }

      const occ = dominantClass === 0 ? 0.05 : Math.min(1.0, 0.4 + (cnt / 25) * 0.6);
      const roughness = Math.max(0.01, (maxZ - minZ) * 0.1);

      cells[key] = {
        resolution_level: meta.resName,
        cell_x: Number(meta.cx.toFixed(2)),
        cell_y: Number(meta.cy.toFixed(2)),
        elevation: Number(elev.toFixed(3)),
        min_z: Number(minZ.toFixed(3)),
        max_z: Number(maxZ.toFixed(3)),
        semantic_class: dominantClass,
        confidence: Number((maxCnt / cnt).toFixed(2)),
        occupancy: Number(occ.toFixed(2)),
        point_count: cnt,
        roughness: Number(roughness.toFixed(3)),
      };
    }
  }
}
