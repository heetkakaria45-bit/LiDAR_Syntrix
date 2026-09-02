import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Maximize,
  Minimize,
  RotateCcw,
  Compass,
  Layers,
  Box,
  Eye,
  EyeOff,
  Sliders,
  AlertTriangle,
  Radio,
  Crosshair,
  Grid,
  ZoomIn,
  ZoomOut,
  Move,
  Navigation,
  Activity,
  Zap,
  Target,
  Sparkles,
  Cpu,
  Info,
  ChevronDown,
  ChevronUp,
  BarChart2,
  TrendingUp,
  SlidersHorizontal,
  Pin,
  PinOff,
  X,
  Car,
  ShieldAlert,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Ruler,
  Scan,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';
import {
  FramePayload,
  ColorMode,
  CameraViewPreset,
  SEMANTIC_CLASSES,
  FOVEATION_RINGS,
  GridCellData,
  HazardItem,
} from '../../types';
import { TeleopState } from '../teleop/TeleopConsole';

interface LidarViewportProps {
  frame: FramePayload | null;
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
  selectedRingId: number | null;
  onSelectRing: (ringId: number | null) => void;
  visibleClasses: Set<number>;
  onInspectCell?: (cell: GridCellData | null) => void;
  onOpenResolution?: () => void;
  teleop?: TeleopState;
}

export interface SelectedAnomalyData {
  id: string;
  name: string;
  type: 'pothole' | 'curb' | 'ridge' | 'obstacle' | 'cell' | 'vehicle' | 'structure';
  x: number;
  y: number;
  z: number;
  minZ: number;
  maxZ: number;
  elevation: number;
  deltaZ: number;
  radius: number;
  roughness: number;
  traversability: string;
  isTraversable: boolean;
  semanticClass: string;
  confidence: number;
  pointCount: number;
  resolution: string;
  distance: number;
  provenance: string;
}

const createCirclePointTexture = (): THREE.Texture => {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 30);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.7, 'rgba(255, 255, 255, 0.9)');
    grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(32, 32, 30, 0, Math.PI * 2);
    ctx.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return texture;
};

const globalPointTexture = createCirclePointTexture();

export const LidarViewport: React.FC<LidarViewportProps> = ({
  frame,
  colorMode,
  onColorModeChange,
  selectedRingId,
  onSelectRing,
  visibleClasses,
  onInspectCell,
  onOpenResolution,
  teleop,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasWrapperRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);

  // Mesh References
  const pointsMeshRef = useRef<THREE.Points | null>(null);
  const analyticalSurfaceGroupRef = useRef<THREE.Group | null>(null);
  const foveatedGridGroupRef = useRef<THREE.Group | null>(null);
  const zoneDiscsGroupRef = useRef<THREE.Group | null>(null);
  const ringsGroupRef = useRef<THREE.Group | null>(null);
  const axesGroupRef = useRef<THREE.Group | null>(null);
  const egoVehicleRef = useRef<THREE.Group | null>(null);
  const sweepGroupRef = useRef<THREE.Group | null>(null);
  const urbanChunksGroupRef = useRef<THREE.Group | null>(null);
  const anomalySelectionGroupRef = useRef<THREE.Group | null>(null);
  const potholeHitMeshesRef = useRef<THREE.Mesh[]>([]);

  // Dynamic Actor References for continuous unidirectional motion
  const oncomingCarRef = useRef<THREE.Group | null>(null);
  const leadingCarRef = useRef<THREE.Group | null>(null);
  const pedCrossingRef = useRef<THREE.Group | null>(null);
  const wildlifeDeerRef = useRef<THREE.Group | null>(null);

  // Viewport & Analytical Surface State
  const [pointSize, setPointSize] = useState<number>(3.2);
  const [showPoints, setShowPoints] = useState<boolean>(true);
  const [showAnalyticalSurface, setShowAnalyticalSurface] = useState<boolean>(true);
  const [showFoveatedGrid, setShowFoveatedGrid] = useState<boolean>(true);
  const [showRings, setShowRings] = useState<boolean>(true);
  const [showZones, setShowZones] = useState<boolean>(true);
  const [showAxes, setShowAxes] = useState<boolean>(true);
  const [showSweep, setShowSweep] = useState<boolean>(true);
  const [showUrbanEnvironment, setShowUrbanEnvironment] = useState<boolean>(true);
  const [showElevationParametersHUD, setShowElevationParametersHUD] = useState<boolean>(false);
  const [selectedAnomaly, setSelectedAnomaly] = useState<SelectedAnomalyData | null>(null);
  const [activeCameraPreset, setActiveCameraPreset] = useState<CameraViewPreset>('isometric');
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const teleopRef = useRef(teleop);
  useEffect(() => {
    teleopRef.current = teleop;
  }, [teleop]);

  // -------------------------------------------------------------
  // 1. INITIALIZE THREE.JS SCENE & ORBIT CONTROLS
  // -------------------------------------------------------------
  useEffect(() => {
    if (!canvasWrapperRef.current) return;
    const container = canvasWrapperRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e14); // Scientific Dark Graphite
    scene.fog = new THREE.FogExp2(0x0a0e14, 0.005);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 500);
    camera.position.set(-22, 24, -26);
    camera.lookAt(0, 0, 10);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance',
      alpha: false,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.touchAction = 'none';
    renderer.domElement.style.userSelect = 'none';
    renderer.domElement.style.cursor = 'grab';

    renderer.domElement.addEventListener('pointerdown', () => {
      renderer.domElement.style.cursor = 'grabbing';
    });
    window.addEventListener('pointerup', () => {
      if (renderer.domElement) renderer.domElement.style.cursor = 'grab';
    });

    // Raycaster for precision Click & Hover inspection of anomalies / cells
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(potholeHitMeshesRef.current, false);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        const u = hit.userData;
        if (u && u.isPothole) {
          const dist = Math.hypot(u.xM, u.zM);
          const anomalyData: SelectedAnomalyData = {
            id: `ANOMALY-PH-${Math.abs(Math.round(u.zM))}`,
            name: `Pothole Depression (-${u.depthCm}cm)`,
            type: 'pothole',
            x: u.xM,
            y: 0,
            z: u.zM,
            minZ: -u.depthCm / 100,
            maxZ: 0.005,
            elevation: -u.depthCm / 100,
            deltaZ: u.depthCm / 100,
            radius: u.radiusM,
            roughness: 0.016,
            traversability: 'NON-TRAVERSABLE (Step Drop > 8cm)',
            isTraversable: false,
            semanticClass: 'DRIVABLE_GROUND',
            confidence: 0.98,
            pointCount: 168,
            resolution: '5cm (Refined Zone 0)',
            distance: Number(dist.toFixed(1)),
            provenance: 'SYNTHETIC BENCHMARK SPLIT',
          };
          setSelectedAnomaly(anomalyData);
          highlightSelectedAnomaly(anomalyData);
          if (onInspectCell) {
            onInspectCell({
              resolution_level: 'near',
              cell_x: u.xM,
              cell_y: u.zM,
              elevation: -u.depthCm / 100,
              min_z: -u.depthCm / 100,
              max_z: 0.005,
              semantic_class: 0,
              confidence: 0.98,
              point_count: 168,
              roughness: 0.016,
              occupancy: 0.95,
            });
          }
        } else if (u && u.isSpeedBreaker) {
          const dist = Math.hypot(u.xM, u.zM);
          const anomalyData: SelectedAnomalyData = {
            id: `ANOMALY-SB-${Math.abs(Math.round(u.zM))}`,
            name: `Speed Breaker Hump (+${u.heightCm}cm)`,
            type: 'curb',
            x: u.xM,
            y: 0.08,
            z: u.zM,
            minZ: 0.0,
            maxZ: u.heightCm / 100,
            elevation: u.heightCm / 100,
            deltaZ: u.heightCm / 100,
            radius: 1.2,
            roughness: 0.008,
            traversability: 'TRAVERSABLE (Safe speed <= 15 km/h)',
            isTraversable: true,
            semanticClass: 'DRIVABLE_GROUND',
            confidence: 0.99,
            pointCount: 220,
            resolution: '5cm (Refined Zone 0)',
            distance: Number(dist.toFixed(1)),
            provenance: 'SYNTHETIC BENCHMARK SPLIT',
          };
          setSelectedAnomaly(anomalyData);
          highlightSelectedAnomaly(anomalyData);
          if (onInspectCell) {
            onInspectCell({
              resolution_level: 'near',
              cell_x: u.xM,
              cell_y: u.zM,
              elevation: u.heightCm / 100,
              min_z: 0.0,
              max_z: u.heightCm / 100,
              semantic_class: 0,
              confidence: 0.99,
              point_count: 220,
              roughness: 0.008,
              occupancy: 0.9,
            });
          }
        }
      }
    };

    renderer.domElement.addEventListener('click', handlePointerClick);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enableRotate = true;
    controls.enableZoom = true;
    controls.enablePan = true;
    controls.rotateSpeed = 0.9;
    controls.zoomSpeed = 1.2;
    controls.panSpeed = 0.8;
    controls.maxDistance = 280;
    controls.minDistance = 2;
    controls.maxPolarAngle = Math.PI / 2 + 0.06;
    controls.target.set(0, 0, 8);
    controlsRef.current = controls;

    // Lighting (DRDO Technical Laboratory Lighting)
    const ambientLight = new THREE.AmbientLight(0xe2e8f0, 1.1);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.4);
    dirLight1.position.set(40, 70, 40);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x84cc16, 0.9);
    dirLight2.position.set(-40, 50, -40);
    scene.add(dirLight2);

    // Groups
    const urbanChunksGroup = new THREE.Group();
    scene.add(urbanChunksGroup);
    urbanChunksGroupRef.current = urbanChunksGroup;

    const analyticalSurfaceGroup = new THREE.Group();
    scene.add(analyticalSurfaceGroup);
    analyticalSurfaceGroupRef.current = analyticalSurfaceGroup;

    const anomalySelectionGroup = new THREE.Group();
    scene.add(anomalySelectionGroup);
    anomalySelectionGroupRef.current = anomalySelectionGroup;

    const foveatedGridGroup = new THREE.Group();
    scene.add(foveatedGridGroup);
    foveatedGridGroupRef.current = foveatedGridGroup;

    const zoneDiscsGroup = new THREE.Group();
    scene.add(zoneDiscsGroup);
    zoneDiscsGroupRef.current = zoneDiscsGroup;

    const ringsGroup = new THREE.Group();
    scene.add(ringsGroup);
    ringsGroupRef.current = ringsGroup;

    const axesGroup = new THREE.Group();
    scene.add(axesGroup);
    axesGroupRef.current = axesGroup;

    // Build Static Spatial Elements
    buildFoveatedSpatialGrid(foveatedGridGroup);
    buildFoveatedZoneDiscs(zoneDiscsGroup);
    buildFoveatedRingsAndSpokes(ringsGroup);
    buildCoordinateAxesAndScales(axesGroup);

    // Build Canonical Autonomous Research UGV
    const egoRover = createCanonicalResearchUGV();
    scene.add(egoRover);
    egoVehicleRef.current = egoRover;

    // Build 360-degree LiDAR Radar Scanner Sweep Beam
    const sweepGroup = createLiDARRadarSweep();
    scene.add(sweepGroup);
    sweepGroupRef.current = sweepGroup;

    // Build Procedural Infinite Urban World Chunks with Depth Grids inside Potholes
    potholeHitMeshesRef.current = [];
    buildInfiniteUrbanChunks(urbanChunksGroup);

    // Build 3D Topographic Analytical Surface
    build3DAnalyticalSurface(analyticalSurfaceGroup);

    // Render Animation Loop (Strictly One-Way Unidirectional Motion)
    let animationFrameId: number;
    let sweepAngle = 0;
    let pulseTime = 0;
    let wheelRotation = 0;
    let pedWalkProgress = 0;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();

      pulseTime += 0.04;

      if (sweepGroupRef.current) {
        sweepAngle += 0.022;
        sweepGroupRef.current.rotation.y = sweepAngle;
      }

      const curTeleop = teleopRef.current;
      const speed = curTeleop?.speed || 0;
      const steer = curTeleop?.steerAngle || 0;
      const dist = curTeleop?.distanceTraveled || 0;

      // 1. Procedural Continuous World Streaming (Only shifts when vehicle actually drives)
      const chunkLength = 120.0;
      const chunkOffset = dist % chunkLength;
      if (urbanChunksGroupRef.current) {
        urbanChunksGroupRef.current.position.z = chunkOffset;
      }
      if (analyticalSurfaceGroupRef.current) {
        analyticalSurfaceGroupRef.current.position.z = chunkOffset;
      }

      // 2. Unidirectional Continuous Traffic Motion with Realistic Slow Urban Speed
      const oncomingZ = -70.0 + ((pulseTime * 3.6 + dist * 0.4) % 180.0);
      if (oncomingCarRef.current) {
        oncomingCarRef.current.position.set(2.4, 0, oncomingZ);
      }

      if (leadingCarRef.current) {
        const leadingZ = -32.0;
        leadingCarRef.current.position.set(-2.4, 0, leadingZ);
      }

      // 3. Intelligent Pedestrian Crossing with Active Collision Avoidance & Vehicle Yielding
      const crosswalkZ = -18.0;
      const distToOncomingCar = Math.abs(oncomingZ - crosswalkZ);
      const isCarApproaching = distToOncomingCar < 7.5;
      const currentPedX = -3.8 + pedWalkProgress * 7.6;
      const isPedInCarLane = currentPedX > 0.6 && currentPedX < 3.8;

      const shouldYield = isCarApproaching && isPedInCarLane;

      if (pedCrossingRef.current) {
        if (!shouldYield) {
          pedWalkProgress = (pedWalkProgress + 0.0018) % 1.0;
        }

        const pedX = -3.8 + pedWalkProgress * 7.6;
        pedCrossingRef.current.position.x = pedX;

        const legLeft = pedCrossingRef.current.getObjectByName('leg_left');
        const legRight = pedCrossingRef.current.getObjectByName('leg_right');
        if (legLeft && legRight) {
          if (shouldYield) {
            legLeft.rotation.x = 0;
            legRight.rotation.x = 0;
          } else {
            legLeft.rotation.x = Math.sin(pedWalkProgress * 30.0) * 0.28;
            legRight.rotation.x = -Math.sin(pedWalkProgress * 30.0) * 0.28;
          }
        }
      }

      // 4. Wildlife Deer
      if (wildlifeDeerRef.current) {
        const head = wildlifeDeerRef.current.getObjectByName('deer_head');
        if (head) {
          head.rotation.y = Math.sin(pulseTime * 0.6) * 0.12;
          head.rotation.x = Math.sin(pulseTime * 0.9) * 0.06;
        }
      }

      // 5. Dynamic Ego Rover steering & wheel spin
      if (egoVehicleRef.current) {
        const targetX = (-steer / 30) * 1.8;
        egoVehicleRef.current.position.x = THREE.MathUtils.lerp(egoVehicleRef.current.position.x, targetX, 0.08);

        egoVehicleRef.current.rotation.y = (-steer * 0.008);
        egoVehicleRef.current.rotation.z = (steer * 0.004);

        if (speed > 0.05) {
          wheelRotation += (speed * 0.06);
        }

        const frontWheels = egoVehicleRef.current.getObjectByName('front_wheels_group');
        if (frontWheels) {
          frontWheels.rotation.y = (-steer * Math.PI) / 180;
        }

        const puck = egoVehicleRef.current.getObjectByName('lidar_puck');
        if (puck) puck.rotation.y += 0.08;

        const halo = egoVehicleRef.current.getObjectByName('ground_halo');
        if (halo) {
          const s = 1.0 + Math.sin(pulseTime * 2.5) * 0.08;
          halo.scale.set(s, s, s);
        }
      }

      renderer.render(scene, camera);
    };
    animate();

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        const h = entry.contentRect.height;
        if (w > 0 && h > 0 && renderer && camera) {
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }
      }
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener('click', handlePointerClick);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  // -------------------------------------------------------------
  // 2. BUILD 3D TOPOGRAPHIC ANALYTICAL SURFACE (DEFORMED ELEVATION)
  // -------------------------------------------------------------
  const build3DAnalyticalSurface = (group: THREE.Group) => {
    while (group.children.length > 0) group.remove(group.children[0]);

    // Construct analytical elevation surface grid from actual spatial data
    const roadWidth = 9.0;
    const roadLength = 120.0;
    const nx = 48;
    const nz = 120;

    const surfaceGeom = new THREE.PlaneGeometry(roadWidth, roadLength, nx, nz);
    surfaceGeom.rotateX(-Math.PI / 2);

    const pos = surfaceGeom.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    const potholeLocations = [
      { x: -1.6, z: -15.0, r: 1.1, depth: 0.14 },
      { x: 1.8, z: -42.0, r: 0.9, depth: 0.12 },
      { x: -0.8, z: 25.0, r: 1.2, depth: 0.15 },
    ];

    for (let i = 0; i < pos.count; i++) {
      const vx = pos.getX(i);
      const vz = pos.getZ(i);
      let elevY = 0.01; // Base road level

      // Calculate downward deformation for potholes
      potholeLocations.forEach((ph) => {
        const dist = Math.hypot(vx - ph.x, vz - ph.z);
        if (dist < ph.r * 1.6) {
          const t = Math.min(1.0, dist / (ph.r * 1.2));
          // Parabolic / Lorentzian downward deformation
          const drop = ph.depth * (1.0 - t * t);
          if (drop > 0) {
            elevY -= drop * 3.5; // Visual scientific scaling
          }
        }
      });

      pos.setY(i, elevY);

      // Scientific DRDO Elevation Colormap: Subdued Cyan (Flat) -> Muted Olive -> Restrained Amber (Negative Drop)
      if (elevY < -0.1) {
        colors[i * 3 + 0] = 0.93; // Restrained Amber / Red
        colors[i * 3 + 1] = 0.45;
        colors[i * 3 + 2] = 0.15;
      } else if (elevY < -0.02) {
        colors[i * 3 + 0] = 0.52; // Muted Olive
        colors[i * 3 + 1] = 0.65;
        colors[i * 3 + 2] = 0.20;
      } else {
        colors[i * 3 + 0] = 0.15; // Scientific Graphite / Cyan
        colors[i * 3 + 1] = 0.45;
        colors[i * 3 + 2] = 0.65;
      }
    }

    surfaceGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    pos.needsUpdate = true;
    surfaceGeom.computeVertexNormals();

    // Translucent Topographic Analytical Surface
    const surfaceMat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.7,
      metalness: 0.2,
      wireframe: false,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const surfaceMesh = new THREE.Mesh(surfaceGeom, surfaceMat);
    group.add(surfaceMesh);

    // Wireframe Topographic Isocline Lines Overlay
    const wireGeom = new THREE.WireframeGeometry(surfaceGeom);
    const wireMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.35,
    });
    const wireMesh = new THREE.LineSegments(wireGeom, wireMat);
    group.add(wireMesh);
  };

  // -------------------------------------------------------------
  // 3. ANOMALY HIGHLIGHTING & TARGET CALIPERS
  // -------------------------------------------------------------
  const highlightSelectedAnomaly = (anomaly: SelectedAnomalyData) => {
    if (!anomalySelectionGroupRef.current) return;
    const group = anomalySelectionGroupRef.current;
    while (group.children.length > 0) group.remove(group.children[0]);

    // 1. DRDO Target Inspection Bracket Box
    const boxSize = anomaly.radius * 2.2;
    const boxH = Math.max(0.6, anomaly.deltaZ * 4.0);
    const boxGeom = new THREE.BoxGeometry(boxSize, boxH, boxSize);
    const edgesGeom = new THREE.EdgesGeometry(boxGeom);
    const boxMat = new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 2 });
    const targetBox = new THREE.LineSegments(edgesGeom, boxMat);
    targetBox.position.set(anomaly.x, -boxH / 2 + 0.05, anomaly.z);
    group.add(targetBox);

    // 2. Corner Bracket Reticles
    const ringGeom = new THREE.RingGeometry(anomaly.radius * 1.15, anomaly.radius * 1.28, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.9, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(anomaly.x, 0.04, anomaly.z);
    group.add(ring);

    // 3. Crosshair Axis Ticks
    const crossLines: THREE.Vector3[] = [
      new THREE.Vector3(anomaly.x - boxSize, 0.05, anomaly.z),
      new THREE.Vector3(anomaly.x + boxSize, 0.05, anomaly.z),
      new THREE.Vector3(anomaly.x, 0.05, anomaly.z - boxSize),
      new THREE.Vector3(anomaly.x, 0.05, anomaly.z + boxSize),
    ];
    const crossGeom = new THREE.BufferGeometry().setFromPoints(crossLines);
    const crossMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85 });
    group.add(new THREE.LineSegments(crossGeom, crossMat));
  };

  const focusCameraOnAnomaly = (anomaly: SelectedAnomalyData) => {
    if (!cameraRef.current || !controlsRef.current) return;
    controlsRef.current.target.set(anomaly.x, 0, anomaly.z);
    cameraRef.current.position.set(anomaly.x - 6, 8, anomaly.z - 8);
    controlsRef.current.update();
  };

  // POV Helper functions
  const orbitLeft = () => {
    if (!cameraRef.current || !controlsRef.current) return;
    const offset = new THREE.Vector3().subVectors(cameraRef.current.position, controlsRef.current.target);
    const theta = Math.PI / 12;
    const x = offset.x * Math.cos(theta) - offset.z * Math.sin(theta);
    const z = offset.x * Math.sin(theta) + offset.z * Math.cos(theta);
    offset.x = x;
    offset.z = z;
    cameraRef.current.position.addVectors(controlsRef.current.target, offset);
    controlsRef.current.update();
  };

  const orbitRight = () => {
    if (!cameraRef.current || !controlsRef.current) return;
    const offset = new THREE.Vector3().subVectors(cameraRef.current.position, controlsRef.current.target);
    const theta = -Math.PI / 12;
    const x = offset.x * Math.cos(theta) - offset.z * Math.sin(theta);
    const z = offset.x * Math.sin(theta) + offset.z * Math.cos(theta);
    offset.x = x;
    offset.z = z;
    cameraRef.current.position.addVectors(controlsRef.current.target, offset);
    controlsRef.current.update();
  };

  const tiltUp = () => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.y = Math.min(120, cameraRef.current.position.y + 4);
    controlsRef.current.update();
  };

  const tiltDown = () => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.y = Math.max(2, cameraRef.current.position.y - 4);
    controlsRef.current.update();
  };

  const zoomIn = () => {
    if (!cameraRef.current || !controlsRef.current) return;
    const offset = new THREE.Vector3().subVectors(cameraRef.current.position, controlsRef.current.target);
    offset.multiplyScalar(0.85);
    cameraRef.current.position.addVectors(controlsRef.current.target, offset);
    controlsRef.current.update();
  };

  const zoomOut = () => {
    if (!cameraRef.current || !controlsRef.current) return;
    const offset = new THREE.Vector3().subVectors(cameraRef.current.position, controlsRef.current.target);
    offset.multiplyScalar(1.18);
    cameraRef.current.position.addVectors(controlsRef.current.target, offset);
    controlsRef.current.update();
  };

  // -------------------------------------------------------------
  // 4. BUILD INFINITE URBAN CHUNKS WITH 3D U-SHAPED POTHOLE GRIDS
  // -------------------------------------------------------------
  const buildInfiniteUrbanChunks = (mainGroup: THREE.Group) => {
    while (mainGroup.children.length > 0) {
      mainGroup.remove(mainGroup.children[0]);
    }

    [-120.0, 0.0, 120.0].forEach((chunkZOffset) => {
      const chunk = createUrbanChunk(chunkZOffset);
      mainGroup.add(chunk);
    });

    const oncomingCar = createRealisticTrafficCar(0x38bdf8, 'oncoming');
    oncomingCar.position.set(2.4, 0, -40);
    mainGroup.add(oncomingCar);
    oncomingCarRef.current = oncomingCar;

    const leadingCar = createRealisticTrafficCar(0xef4444, 'leading');
    leadingCar.position.set(-2.4, 0, -28);
    mainGroup.add(leadingCar);
    leadingCarRef.current = leadingCar;

    const pedestrianCrossing = createRealisticPedestrian();
    pedestrianCrossing.position.set(0, 0.16, -18);
    mainGroup.add(pedestrianCrossing);
    pedCrossingRef.current = pedestrianCrossing;

    const deerWildlife = createRealisticDeer();
    deerWildlife.position.set(8.5, 0.16, -32);
    mainGroup.add(deerWildlife);
    wildlifeDeerRef.current = deerWildlife;
  };

  const createUrbanChunk = (chunkZOffset: number): THREE.Group => {
    const chunk = new THREE.Group();
    chunk.position.set(0, 0, chunkZOffset);

    // 1. Asphalt Roadway
    const roadGeom = new THREE.PlaneGeometry(9.0, 120.0);
    const roadMat = new THREE.MeshStandardMaterial({
      color: 0x141820,
      roughness: 0.85,
      metalness: 0.15,
    });
    const road = new THREE.Mesh(roadGeom, roadMat);
    road.rotation.x = -Math.PI / 2;
    chunk.add(road);

    // Centerline Dashes
    for (let z = -55; z <= 55; z += 6) {
      const dashGeom = new THREE.PlaneGeometry(0.18, 3.5);
      const dashMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85 });
      const dash = new THREE.Mesh(dashGeom, dashMat);
      dash.rotation.x = -Math.PI / 2;
      dash.position.set(0, 0.005, z);
      chunk.add(dash);
    }

    // Road Edge Solid White Lines
    [-4.3, 4.3].forEach((lx) => {
      const edgeGeom = new THREE.PlaneGeometry(0.16, 120.0);
      const edgeMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.75 });
      const edge = new THREE.Mesh(edgeGeom, edgeMat);
      edge.rotation.x = -Math.PI / 2;
      edge.position.set(lx, 0.005, 0);
      chunk.add(edge);
    });

    // Zebra Crosswalk at z = -18
    for (let y = -3.8; y <= 3.8; y += 0.9) {
      const stripeGeom = new THREE.PlaneGeometry(0.5, 4.0);
      const stripeMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 });
      const stripe = new THREE.Mesh(stripeGeom, stripeMat);
      stripe.rotation.x = -Math.PI / 2;
      stripe.position.set(y, 0.006, -18);
      chunk.add(stripe);
    }

    // 2. Realistic 3D Potholes with 3D U-Shaped Parabolic Graph Grid & Depth Light Beams
    const potholeLocations = [
      { x: -1.6, z: -15.0, r: 1.1, depth: 0.14 },
      { x: 1.8, z: -42.0, r: 0.9, depth: 0.12 },
      { x: -0.8, z: 25.0, r: 1.2, depth: 0.15 },
    ];

    potholeLocations.forEach((ph) => {
      const potholeMesh = createPothole3DMesh(ph.r, ph.depth, ph.x, ph.z + chunkZOffset);
      potholeMesh.position.set(ph.x, 0, ph.z);
      chunk.add(potholeMesh);
    });

    // 2b. Speed Breakers (Traffic Calming Humps) at adequate intervals on the road
    const speedBreakerZLocations = [-32.0, 32.0];
    speedBreakerZLocations.forEach((sbZ) => {
      const sbMesh = createSpeedBreaker3DMesh(0, sbZ + chunkZOffset);
      sbMesh.position.set(0, 0, sbZ);
      chunk.add(sbMesh);
    });

    // 3. Raised Concrete Sidewalks (+0.16m Curb Step)
    [-6.8, 6.8].forEach((sideX) => {
      const sidewalkGeom = new THREE.BoxGeometry(4.6, 0.16, 120.0);
      const sidewalkMat = new THREE.MeshStandardMaterial({ color: 0x222a36, roughness: 0.7 });
      const sidewalk = new THREE.Mesh(sidewalkGeom, sidewalkMat);
      sidewalk.position.set(sideX, 0.08, 0);
      chunk.add(sidewalk);

      const curbEdgeGeom = new THREE.BoxGeometry(0.2, 0.18, 120.0);
      const curbEdgeMat = new THREE.MeshStandardMaterial({
        color: 0xf59e0b,
        emissive: 0xf59e0b,
        emissiveIntensity: 0.25,
      });
      const curbEdge = new THREE.Mesh(curbEdgeGeom, curbEdgeMat);
      curbEdge.position.set(sideX > 0 ? 4.5 : -4.5, 0.09, 0);
      chunk.add(curbEdge);
    });

    // 4. Modern Multi-Story Buildings with 2.5D Height Grids
    const buildingConfigs = [
      { x: 17.5, z: -35, dx: 15, dy: 14, dz: 28, color: 0x141a24, windowColor: 0x38bdf8 },
      { x: 16.5, z: 15, dx: 13, dy: 10, dz: 24, color: 0x1a2230, windowColor: 0xf59e0b },
      { x: -17.5, z: -40, dx: 15, dy: 16, dz: 30, color: 0x101620, windowColor: 0x10b981 },
      { x: -16.5, z: 20, dx: 13, dy: 11, dz: 26, color: 0x161f2c, windowColor: 0x38bdf8 },
    ];

    buildingConfigs.forEach((b) => {
      const bGeom = new THREE.BoxGeometry(b.dx, b.dy, b.dz);
      const bMat = new THREE.MeshStandardMaterial({ color: b.color, roughness: 0.6, metalness: 0.3 });
      const bMesh = new THREE.Mesh(bGeom, bMat);
      bMesh.position.set(b.x, b.dy / 2 + 0.16, b.z);
      chunk.add(bMesh);

      const heightGrid = create25DHeightGrid(b.dx, b.dy, b.dz, b.windowColor);
      heightGrid.position.set(b.x, 0.16, b.z);
      chunk.add(heightGrid);

      for (let floor = 2; floor < b.dy - 1; floor += 3) {
        for (let wZ = -b.dz / 2 + 3; wZ < b.dz / 2 - 2; wZ += 4) {
          const winGeom = new THREE.PlaneGeometry(1.8, 1.4);
          const winMat = new THREE.MeshBasicMaterial({
            color: b.windowColor,
            transparent: true,
            opacity: 0.55,
          });
          const win = new THREE.Mesh(winGeom, winMat);
          win.position.set(b.x > 0 ? b.x - b.dx / 2 - 0.02 : b.x + b.dx / 2 + 0.02, floor + 0.16, b.z + wZ);
          win.rotation.y = b.x > 0 ? -Math.PI / 2 : Math.PI / 2;
          chunk.add(win);
        }
      }
    });

    // 5. Streetlights & Trees
    [-45, -15, 15, 45].forEach((lz) => {
      [-5.2, 5.2].forEach((lx) => {
        const pole = new THREE.Mesh(
          new THREE.CylinderGeometry(0.08, 0.12, 5.5, 12),
          new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8 })
        );
        pole.position.set(lx, 2.75 + 0.16, lz);
        chunk.add(pole);

        const lamp = new THREE.Mesh(
          new THREE.BoxGeometry(0.3, 0.15, 0.7),
          new THREE.MeshStandardMaterial({ color: 0xffb703, emissive: 0xffb703, emissiveIntensity: 0.9 })
        );
        lamp.position.set(lx > 0 ? lx - 0.4 : lx + 0.4, 5.4 + 0.16, lz);
        chunk.add(lamp);
      });

      [-7.2, 7.2].forEach((tx) => {
        const trunk = new THREE.Mesh(
          new THREE.CylinderGeometry(0.18, 0.24, 2.8, 10),
          new THREE.MeshStandardMaterial({ color: 0x3d2718, roughness: 0.9 })
        );
        trunk.position.set(tx, 1.4 + 0.16, lz + 6);
        chunk.add(trunk);

        const canopy = new THREE.Mesh(
          new THREE.SphereGeometry(1.6, 12, 10),
          new THREE.MeshStandardMaterial({ color: 0x10b981, roughness: 0.7, emissive: 0x059669, emissiveIntensity: 0.25 })
        );
        canopy.position.set(tx, 3.6 + 0.16, lz + 6);
        chunk.add(canopy);
      });
    });

    const bsGroup = createBusStopShelter();
    bsGroup.position.set(-6.2, 0.16, -28);
    chunk.add(bsGroup);

    return chunk;
  };

  const createDepthTextBadge = (text: string, colorHex: string): THREE.Sprite => {
    const canvas = document.createElement('canvas');
    canvas.width = 384;
    canvas.height = 110;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = 'rgba(10, 14, 20, 0.92)';
      ctx.strokeStyle = colorHex;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.roundRect(10, 10, 364, 90, 24);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = colorHex;
      ctx.font = 'bold 20px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText('▼ MEASURED ELEVATION', 192, 20);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 36px monospace';
      ctx.fillText(text, 192, 50);
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMat = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
    });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(2.4, 0.7, 1.0);
    return sprite;
  };

  const createPotholeDepthLightBeam = (radius: number, depth: number): THREE.Group => {
    const beamGroup = new THREE.Group();
    const beamHeight = 3.2;

    // 1. Volumetric Light Column rising out of the crater floor (Z = -depth)
    const beamGeom = new THREE.CylinderGeometry(radius * 0.35, radius * 0.8, beamHeight, 24, 1, true);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b,
      transparent: true,
      opacity: 0.28,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const beamMesh = new THREE.Mesh(beamGeom, beamMat);
    beamMesh.position.y = beamHeight / 2 - depth;
    beamGroup.add(beamMesh);

    // 2. Optical Center Laser Line
    const laserGeom = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, -depth, 0),
      new THREE.Vector3(0, beamHeight - depth, 0),
    ]);
    const laserMat = new THREE.LineBasicMaterial({
      color: 0xffb703,
      transparent: true,
      opacity: 0.9,
    });
    beamGroup.add(new THREE.Line(laserGeom, laserMat));

    // 3. Depth Caliper Level Rings along the beam
    const depthLevels = [
      { y: -depth, r: radius * 0.75, color: 0xef4444 },
      { y: 0.01, r: radius * 0.65, color: 0x38bdf8 },
      { y: 1.2, r: radius * 0.52, color: 0xf59e0b },
      { y: 2.4, r: radius * 0.42, color: 0xf59e0b },
    ];

    depthLevels.forEach((dl) => {
      const ringGeom = new THREE.RingGeometry(dl.r - 0.02, dl.r + 0.02, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: dl.color,
        transparent: true,
        opacity: 0.85,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeom, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = dl.y;
      beamGroup.add(ring);
    });

    // 4. Floating 3D Depth Readout Badge at top of the light column
    const depthCm = Math.round(depth * 100);
    const depthBadge = createDepthTextBadge(`-${depthCm}.0 cm DEPTH`, '#f59e0b');
    depthBadge.position.set(0, beamHeight - depth + 0.45, 0);
    beamGroup.add(depthBadge);

    // 5. Pulsing Optical Light Emitter Flare at Crater Base
    const flareGeom = new THREE.RingGeometry(0.05, radius * 0.4, 24);
    const flareMat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      transparent: true,
      opacity: 0.9,
      side: THREE.DoubleSide,
    });
    const flare = new THREE.Mesh(flareGeom, flareMat);
    flare.rotation.x = -Math.PI / 2;
    flare.position.y = -depth + 0.005;
    beamGroup.add(flare);

    return beamGroup;
  };

  const createSpeedBreaker3DMesh = (worldX: number, worldZ: number): THREE.Group => {
    const sbGroup = new THREE.Group();
    const width = 8.6; // across both lanes
    const length = 1.8; // along road Z
    const height = 0.08; // 8cm high hump

    // 1. Curved Parabolic Speed Breaker Hump Surface
    const humpGeom = new THREE.CylinderGeometry(length / 2, length / 2, width, 32, 12, false, 0, Math.PI);
    humpGeom.rotateZ(Math.PI / 2);
    humpGeom.scale(1.0, height / (length / 2), 1.0);

    const humpMat = new THREE.MeshStandardMaterial({
      color: 0x1f2937,
      roughness: 0.7,
      metalness: 0.2,
    });
    const humpMesh = new THREE.Mesh(humpGeom, humpMat);
    humpMesh.position.set(0, 0, 0);
    sbGroup.add(humpMesh);

    // 2. High-Visibility Yellow Hazard Chevron Stripes
    const stripeCount = 14;
    const stripeWidth = width / stripeCount;
    for (let s = 0; s < stripeCount; s++) {
      if (s % 2 === 0) {
        const sx = -width / 2 + s * stripeWidth + stripeWidth / 2;
        const stripeGeom = new THREE.PlaneGeometry(stripeWidth * 0.85, length * 0.92);
        const stripeMat = new THREE.MeshBasicMaterial({
          color: 0xfbbf24,
          transparent: true,
          opacity: 0.92,
        });
        const stripe = new THREE.Mesh(stripeGeom, stripeMat);
        stripe.rotation.x = -Math.PI / 2;
        stripe.position.set(sx, height * 0.95 + 0.002, 0);
        sbGroup.add(stripe);
      }
    }

    // 3. Side Warning Reflector Studs
    [-width / 2 + 0.2, width / 2 - 0.2].forEach((studX) => {
      const stud = new THREE.Mesh(
        new THREE.CylinderGeometry(0.06, 0.06, 0.04, 12),
        new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 1.0 })
      );
      stud.position.set(studX, height + 0.01, 0);
      sbGroup.add(stud);
    });

    // 4. Floating Speed Breaker Tag / Caliper
    const sbBadge = createDepthTextBadge(`+8.0 cm STEP`, '#10b981');
    sbBadge.position.set(0, 1.8, 0);
    sbBadge.scale.set(2.0, 0.6, 1.0);
    sbGroup.add(sbBadge);

    // 5. Invisible Hitbox for Raycast Inspector
    const hitGeom = new THREE.BoxGeometry(width, 0.6, length * 1.4);
    const hitMat = new THREE.MeshBasicMaterial({ visible: false });
    const hitMesh = new THREE.Mesh(hitGeom, hitMat);
    hitMesh.position.y = 0.2;
    hitMesh.userData = {
      isSpeedBreaker: true,
      heightCm: 8,
      xM: worldX,
      zM: worldZ,
    };
    sbGroup.add(hitMesh);
    potholeHitMeshesRef.current.push(hitMesh);

    return sbGroup;
  };

  const create25DHeightGrid = (dx: number, dy: number, dz: number, colorHex: number): THREE.Group => {
    const gridGroup = new THREE.Group();

    [[-dx / 2, -dz / 2], [dx / 2, -dz / 2], [-dx / 2, dz / 2], [dx / 2, dz / 2]].forEach(([cx, cz]) => {
      const lineGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(cx, 0, cz),
        new THREE.Vector3(cx, dy, cz),
      ]);
      const lineMat = new THREE.LineBasicMaterial({ color: colorHex, transparent: true, opacity: 0.85 });
      gridGroup.add(new THREE.Line(lineGeom, lineMat));
    });

    for (let h = 3; h <= dy; h += 3) {
      const rectGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-dx / 2, h, -dz / 2),
        new THREE.Vector3(dx / 2, h, -dz / 2),
        new THREE.Vector3(dx / 2, h, dz / 2),
        new THREE.Vector3(-dx / 2, h, dz / 2),
        new THREE.Vector3(-dx / 2, h, -dz / 2),
      ]);
      const rectMat = new THREE.LineBasicMaterial({ color: colorHex, transparent: true, opacity: 0.4 });
      gridGroup.add(new THREE.Line(rectGeom, rectMat));
    }

    return gridGroup;
  };

  const createPothole3DMesh = (radius: number, depth: number, worldX: number, worldZ: number): THREE.Group => {
    const pothole = new THREE.Group();

    const uShapedGrid = createUShapedGraphGrid(radius, depth);
    pothole.add(uShapedGrid);

    // Vertical Volumetric Hazard Light Column denoting exact pothole depth
    const lightBeam = createPotholeDepthLightBeam(radius, depth);
    pothole.add(lightBeam);

    const surfaceRingGeom = new THREE.RingGeometry(radius, radius + 0.18, 32);
    const surfaceRingMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b,
      transparent: true,
      opacity: 0.9,
      side: THREE.DoubleSide,
    });
    const surfaceRing = new THREE.Mesh(surfaceRingGeom, surfaceRingMat);
    surfaceRing.rotation.x = -Math.PI / 2;
    surfaceRing.position.y = 0.01;
    pothole.add(surfaceRing);

    const hitGeom = new THREE.CylinderGeometry(radius * 1.4, radius * 1.4, 1.0, 16);
    const hitMat = new THREE.MeshBasicMaterial({ visible: false });
    const hitMesh = new THREE.Mesh(hitGeom, hitMat);
    hitMesh.position.y = 0;
    hitMesh.userData = {
      isPothole: true,
      depthCm: Math.round(depth * 100),
      radiusM: radius,
      xM: worldX,
      zM: worldZ,
    };
    pothole.add(hitMesh);
    potholeHitMeshesRef.current.push(hitMesh);

    return pothole;
  };

  const createUShapedGraphGrid = (radius: number, depth: number): THREE.Group => {
    const group = new THREE.Group();
    const visualDepth = 0.55;
    const numRibs = 14;
    const ptsPerRib = 36;

    const lines: THREE.Vector3[] = [];
    const colors: number[] = [];

    const getDepthColor = (y: number): THREE.Color => {
      const norm = Math.min(1.0, Math.max(0.0, -y / visualDepth));
      if (norm < 0.2) return new THREE.Color(0x38bdf8); // Neon Cyan
      if (norm < 0.6) return new THREE.Color(0xf59e0b); // Warning Amber
      return new THREE.Color(0xef4444); // Crimson Red
    };

    // 1. Parallel U-Shaped Parabolic Graph Ribs along X-axis
    for (let i = -numRibs / 2; i <= numRibs / 2; i++) {
      const zOffset = (i / (numRibs / 2)) * (radius * 0.95);
      const spanX = Math.sqrt(Math.max(0, radius * radius - zOffset * zOffset));
      if (spanX < 0.08) continue;

      for (let j = 0; j < ptsPerRib; j++) {
        const t1 = (j / ptsPerRib) * 2 - 1;
        const t2 = ((j + 1) / ptsPerRib) * 2 - 1;
        const x1 = t1 * spanX;
        const x2 = t2 * spanX;

        const r1 = Math.hypot(x1, zOffset) / radius;
        const r2 = Math.hypot(x2, zOffset) / radius;
        const y1 = -visualDepth * Math.max(0, 1 - r1 * r1);
        const y2 = -visualDepth * Math.max(0, 1 - r2 * r2);

        lines.push(new THREE.Vector3(x1, y1, zOffset));
        lines.push(new THREE.Vector3(x2, y2, zOffset));

        const c1 = getDepthColor(y1);
        const c2 = getDepthColor(y2);
        colors.push(c1.r, c1.g, c1.b, c2.r, c2.g, c2.b);
      }
    }

    // 2. Parallel U-Shaped Parabolic Graph Ribs along Z-axis
    for (let i = -numRibs / 2; i <= numRibs / 2; i++) {
      const xOffset = (i / (numRibs / 2)) * (radius * 0.95);
      const spanZ = Math.sqrt(Math.max(0, radius * radius - xOffset * xOffset));
      if (spanZ < 0.08) continue;

      for (let j = 0; j < ptsPerRib; j++) {
        const t1 = (j / ptsPerRib) * 2 - 1;
        const t2 = ((j + 1) / ptsPerRib) * 2 - 1;
        const z1 = t1 * spanZ;
        const z2 = t2 * spanZ;

        const r1 = Math.hypot(xOffset, z1) / radius;
        const r2 = Math.hypot(xOffset, z2) / radius;
        const y1 = -visualDepth * Math.max(0, 1 - r1 * r1);
        const y2 = -visualDepth * Math.max(0, 1 - r2 * r2);

        lines.push(new THREE.Vector3(xOffset, y1, z1));
        lines.push(new THREE.Vector3(xOffset, y2, z2));

        const c1 = getDepthColor(y1);
        const c2 = getDepthColor(y2);
        colors.push(c1.r, c1.g, c1.b, c2.r, c2.g, c2.b);
      }
    }

    // 3. Vertical Drop Projection Grid Lines around perimeter
    const perimeterSegs = 20;
    for (let p = 0; p < perimeterSegs; p++) {
      const theta = (p / perimeterSegs) * Math.PI * 2;
      const px = Math.cos(theta) * radius;
      const pz = Math.sin(theta) * radius;
      lines.push(new THREE.Vector3(px, 0.01, pz));
      lines.push(new THREE.Vector3(px * 0.5, -visualDepth * 0.75, pz * 0.5));
      const cTop = new THREE.Color(0x38bdf8);
      const cBot = new THREE.Color(0xf59e0b);
      colors.push(cTop.r, cTop.g, cTop.b, cBot.r, cBot.g, cBot.b);
    }

    const wireGeom = new THREE.BufferGeometry().setFromPoints(lines);
    wireGeom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    const wireMat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
    });
    group.add(new THREE.LineSegments(wireGeom, wireMat));

    // 4. Concentric Horizontal Depth Contour Rings
    const numRings = 5;
    for (let k = 1; k <= numRings; k++) {
      const ringFraction = k / numRings;
      const ringDepth = -visualDepth * (1 - Math.pow(ringFraction, 2));
      const ringR = radius * ringFraction;
      const rPts: THREE.Vector3[] = [];
      const rSegs = 36;
      for (let s = 0; s <= rSegs; s++) {
        const th = (s / rSegs) * Math.PI * 2;
        rPts.push(new THREE.Vector3(Math.cos(th) * ringR, ringDepth, Math.sin(th) * ringR));
      }
      const rGeom = new THREE.BufferGeometry().setFromPoints(rPts);
      const rColor = getDepthColor(ringDepth);
      const rMat = new THREE.LineBasicMaterial({
        color: rColor,
        transparent: true,
        opacity: 0.8,
      });
      group.add(new THREE.Line(rGeom, rMat));
    }

    // 5. Translucent 3D Parabolic Shaded Volume
    const paraGeom = new THREE.CylinderGeometry(radius, 0.05, visualDepth, 24, 8, true);
    const pos = paraGeom.attributes.position;
    for (let idx = 0; idx < pos.count; idx++) {
      const vx = pos.getX(idx);
      const vy = pos.getY(idx);
      const vz = pos.getZ(idx);
      const t = (vy + visualDepth / 2) / visualDepth;
      const rScale = Math.sqrt(Math.max(0, t));
      const currentR = Math.hypot(vx, vz);
      if (currentR > 0.001) {
        const targetR = radius * rScale;
        pos.setX(idx, (vx / currentR) * targetR);
        pos.setZ(idx, (vz / currentR) * targetR);
      }
      pos.setY(idx, (t - 1) * visualDepth);
    }
    pos.needsUpdate = true;
    paraGeom.computeVertexNormals();

    const paraMat = new THREE.MeshStandardMaterial({
      color: 0x0ea5e9,
      emissive: 0xef4444,
      emissiveIntensity: 0.35,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const paraMesh = new THREE.Mesh(paraGeom, paraMat);
    group.add(paraMesh);

    return group;
  };

  // -------------------------------------------------------------
  // 5. SCULPTED CANONICAL AUTONOMOUS RESEARCH UGV (SMOOTH PBR & VIDEO ASSET INTEGRATION)
  // -------------------------------------------------------------
  const createCanonicalResearchUGV = (): THREE.Group => {
    const rover = new THREE.Group();
    rover.name = 'ego_rover';

    // Premium PBR Automotive Clearcoat Materials
    const bodyMetallicMat = new THREE.MeshStandardMaterial({
      color: 0x1a222c, // Metallic Graphite / Charcoal
      metalness: 0.88,
      roughness: 0.22,
    });

    const oliveAccentMat = new THREE.MeshStandardMaterial({
      color: 0x4d7c0f, // Muted Military Olive Trim
      metalness: 0.45,
      roughness: 0.35,
    });

    const carbonTrimMat = new THREE.MeshStandardMaterial({
      color: 0x0c1117, // Carbon Fiber Slate Black
      metalness: 0.92,
      roughness: 0.18,
    });

    const canopyGlassMat = new THREE.MeshStandardMaterial({
      color: 0x040608, // Dark Tinted Panoramic Polycarbonate
      metalness: 0.98,
      roughness: 0.04,
      transparent: true,
      opacity: 0.94,
    });

    const emeraldOpticMat = new THREE.MeshStandardMaterial({
      color: 0x10b981, // Emerald LiDAR Optic Emitter
      emissive: 0x10b981,
      emissiveIntensity: 0.95,
      metalness: 0.95,
      roughness: 0.05,
    });

    // 1. Sleek Aerodynamic Lower Body & Sculpted Underbody
    const mainFuselageGeom = new THREE.CylinderGeometry(1.02, 1.05, 4.2, 32);
    mainFuselageGeom.rotateX(Math.PI / 2);
    mainFuselageGeom.scale(1.0, 0.4, 1.0);
    const mainFuselage = new THREE.Mesh(mainFuselageGeom, bodyMetallicMat);
    mainFuselage.position.y = 0.44;
    rover.add(mainFuselage);

    // Sculpted Protective Skidplate
    const skidplateGeom = new THREE.CylinderGeometry(0.85, 0.88, 3.8, 24);
    skidplateGeom.rotateX(Math.PI / 2);
    skidplateGeom.scale(1.0, 0.18, 1.0);
    const skidplate = new THREE.Mesh(skidplateGeom, carbonTrimMat);
    skidplate.position.set(0, 0.22, 0);
    rover.add(skidplate);

    // 2. Curved Aerodynamic Hood & Sculpted Nose Cone
    const noseGeom = new THREE.SphereGeometry(0.96, 32, 16);
    noseGeom.scale(1.02, 0.36, 1.2);
    const nose = new THREE.Mesh(noseGeom, bodyMetallicMat);
    nose.position.set(0, 0.58, -1.55);
    rover.add(nose);

    // Olive Accent Center Intake Cowl
    const cowlGeom = new THREE.CylinderGeometry(0.45, 0.48, 1.4, 16);
    cowlGeom.rotateX(Math.PI / 2);
    cowlGeom.scale(1.0, 0.15, 1.0);
    const cowl = new THREE.Mesh(cowlGeom, oliveAccentMat);
    cowl.position.set(0, 0.76, -1.2);
    rover.add(cowl);

    // 3. Streamlined Panoramic Teardrop Cabin Dome
    const canopyGeom = new THREE.SphereGeometry(0.88, 32, 20);
    canopyGeom.scale(0.92, 0.56, 1.5);
    const canopy = new THREE.Mesh(canopyGeom, canopyGlassMat);
    canopy.position.set(0, 1.06, 0.2);
    rover.add(canopy);

    // Muted Olive Roof Sensor Deck
    const roofDeckGeom = new THREE.CylinderGeometry(0.72, 0.78, 0.1, 24);
    roofDeckGeom.scale(1.0, 1.0, 1.3);
    const roofDeck = new THREE.Mesh(roofDeckGeom, oliveAccentMat);
    roofDeck.position.set(0, 1.38, 0.25);
    rover.add(roofDeck);

    // 4. Smooth Curved Wheel Arch Fenders
    [
      { x: -1.02, z: -1.35 },
      { x: 1.02, z: -1.35 },
      { x: -1.02, z: 1.35 },
      { x: 1.02, z: 1.35 },
    ].forEach((archPos) => {
      const archGeom = new THREE.TorusGeometry(0.52, 0.08, 16, 24, Math.PI);
      archGeom.rotateY(archPos.x > 0 ? Math.PI / 2 : -Math.PI / 2);
      const arch = new THREE.Mesh(archGeom, bodyMetallicMat);
      arch.position.set(archPos.x, 0.44, archPos.z);
      rover.add(arch);
    });

    // 5. Cylindrical 360° Rotating LiDAR Sensor Turret (Point Cloud Origin at Z = 1.90m)
    const mastBase = new THREE.Mesh(
      new THREE.CylinderGeometry(0.24, 0.28, 0.18, 24),
      carbonTrimMat
    );
    mastBase.position.set(0, 1.5, 0.05);
    rover.add(mastBase);

    const mastShaft = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.1, 0.25, 16),
      carbonTrimMat
    );
    mastShaft.position.set(0, 1.68, 0.05);
    rover.add(mastShaft);

    const puckGroup = new THREE.Group();
    puckGroup.name = 'lidar_puck';
    puckGroup.position.set(0, 1.90, 0.05);

    // Sensor Turret Lower Housing
    const puckLower = new THREE.Mesh(
      new THREE.CylinderGeometry(0.26, 0.26, 0.12, 32),
      carbonTrimMat
    );
    puckGroup.add(puckLower);

    // Spinning Optical Sensor Lens
    const puckOptic = new THREE.Mesh(
      new THREE.CylinderGeometry(0.24, 0.24, 0.14, 32),
      emeraldOpticMat
    );
    puckOptic.position.y = 0.11;
    puckGroup.add(puckOptic);

    // Protective Top Cap
    const puckCap = new THREE.Mesh(
      new THREE.CylinderGeometry(0.26, 0.26, 0.06, 32),
      carbonTrimMat
    );
    puckCap.position.y = 0.2;
    puckGroup.add(puckCap);

    rover.add(puckGroup);

    // 6. Auxiliary Perception Sensors
    // Stereo Camera Brow Bar
    const camBarGeom = new THREE.CylinderGeometry(0.06, 0.06, 0.84, 16);
    camBarGeom.rotateZ(Math.PI / 2);
    const camBar = new THREE.Mesh(camBarGeom, carbonTrimMat);
    camBar.position.set(0, 1.36, -0.68);
    rover.add(camBar);

    [-0.32, 0.32].forEach((camX) => {
      const lens = new THREE.Mesh(
        new THREE.SphereGeometry(0.045, 16, 12),
        new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x38bdf8, emissiveIntensity: 1.2 })
      );
      lens.position.set(camX, 1.36, -0.73);
      rover.add(lens);
    });

    // GNSS / RTK Antenna Pod
    const gnssDome = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 16, 12),
      new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.6, roughness: 0.2 })
    );
    gnssDome.scale.set(1.0, 0.4, 1.0);
    gnssDome.position.set(0, 1.48, 0.85);
    rover.add(gnssDome);

    // 7. Sleek Dynamic Scientific Lighting Strips
    const frontLightMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x38bdf8, emissiveIntensity: 2.0 });
    const frontLightStrip = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.8, 16), frontLightMat);
    frontLightStrip.rotateZ(Math.PI / 2);
    frontLightStrip.position.set(0, 0.52, -2.12);
    rover.add(frontLightStrip);

    const rearLightMat = new THREE.MeshStandardMaterial({ color: 0xff0033, emissive: 0xff0033, emissiveIntensity: 1.8 });
    const rearLightStrip = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.8, 16), rearLightMat);
    rearLightStrip.rotateZ(Math.PI / 2);
    rearLightStrip.position.set(0, 0.58, 2.12);
    rover.add(rearLightStrip);

    // 8. Four High-Poly Smooth All-Terrain Wheels
    const frontWheelsGroup = new THREE.Group();
    frontWheelsGroup.name = 'front_wheels_group';
    frontWheelsGroup.position.set(0, 0.42, -1.35);

    [-1.12, 1.12].forEach((wx) => {
      const wheel = createCanonicalRuggedWheel();
      wheel.position.set(wx, 0, 0);
      frontWheelsGroup.add(wheel);
    });
    rover.add(frontWheelsGroup);

    [-1.12, 1.12].forEach((wx) => {
      const wheel = createCanonicalRuggedWheel();
      wheel.position.set(wx, 0.42, 1.35);
      rover.add(wheel);
    });

    // 9. Sensor Beam & Ground Halo
    const headlightCone = new THREE.Mesh(
      new THREE.ConeGeometry(3.8, 18, 32, 1, true),
      new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false })
    );
    headlightCone.rotation.x = -Math.PI / 2;
    headlightCone.position.set(0, 0.52, -9.5);
    rover.add(headlightCone);

    const groundHalo = new THREE.Mesh(
      new THREE.RingGeometry(2.6, 2.9, 48),
      new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.45, side: THREE.DoubleSide })
    );
    groundHalo.name = 'ground_halo';
    groundHalo.rotation.x = -Math.PI / 2;
    groundHalo.position.set(0, 0.04, 0);
    rover.add(groundHalo);

    return rover;
  };

  const createCanonicalRuggedWheel = (): THREE.Group => {
    const wheelGroup = new THREE.Group();

    // Smooth Round Rubber Pneumatic Tire (Torus Profile for Curvature)
    const tire = new THREE.Mesh(
      new THREE.TorusGeometry(0.34, 0.11, 24, 36),
      new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.88, metalness: 0.08 })
    );
    tire.rotation.y = Math.PI / 2;
    wheelGroup.add(tire);

    // Inner Tread Hub Ring
    const innerTire = new THREE.Mesh(
      new THREE.CylinderGeometry(0.36, 0.36, 0.28, 32),
      new THREE.MeshStandardMaterial({ color: 0x0a0f16, roughness: 0.95 })
    );
    innerTire.rotation.z = Math.PI / 2;
    wheelGroup.add(innerTire);

    // Multi-Spoke Graphite Alloy Wheel Rim
    const rim = new THREE.Mesh(
      new THREE.CylinderGeometry(0.26, 0.26, 0.3, 24),
      new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.92, roughness: 0.2 })
    );
    rim.rotation.z = Math.PI / 2;
    wheelGroup.add(rim);

    // Central Axle Cap & Blue Telemetry Accent
    const hub = new THREE.Mesh(
      new THREE.CylinderGeometry(0.09, 0.09, 0.32, 16),
      new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x38bdf8, emissiveIntensity: 0.5, metalness: 0.9 })
    );
    hub.rotation.z = Math.PI / 2;
    wheelGroup.add(hub);

    return wheelGroup;
  };

  const createRealisticTrafficCar = (colorHex: number, type: 'oncoming' | 'leading'): THREE.Group => {
    const car = new THREE.Group();

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(1.9, 0.65, 4.4),
      new THREE.MeshStandardMaterial({ color: colorHex, metalness: 0.85, roughness: 0.25 })
    );
    body.position.y = 0.55;
    car.add(body);

    const cabin = new THREE.Mesh(
      new THREE.BoxGeometry(1.5, 0.55, 2.3),
      new THREE.MeshStandardMaterial({ color: 0x0a0e14, metalness: 0.95, roughness: 0.1 })
    );
    cabin.position.set(0, 1.15, -0.2);
    car.add(cabin);

    const frontLightMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 1.2 });
    const rearLightMat = new THREE.MeshStandardMaterial({ color: 0xff0033, emissive: 0xff0033, emissiveIntensity: 1.0 });

    [-0.7, 0.7].forEach((lx) => {
      const fLight = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.15, 0.1), type === 'oncoming' ? frontLightMat : rearLightMat);
      fLight.position.set(lx, 0.55, 2.2);
      car.add(fLight);

      const rLight = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.15, 0.1), type === 'oncoming' ? rearLightMat : frontLightMat);
      rLight.position.set(lx, 0.55, -2.2);
      car.add(rLight);
    });

    [[-1.0, 1.3], [1.0, 1.3], [-1.0, -1.3], [1.0, -1.3]].forEach(([wx, wz]) => {
      const wheel = new THREE.Mesh(
        new THREE.CylinderGeometry(0.36, 0.36, 0.28, 16),
        new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.8 })
      );
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(wx, 0.36, wz);
      car.add(wheel);
    });

    if (type === 'oncoming') {
      car.rotation.y = Math.PI;
    }

    return car;
  };

  const createRealisticPedestrian = (): THREE.Group => {
    const ped = new THREE.Group();

    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.18, 12, 10),
      new THREE.MeshStandardMaterial({ color: 0xf6d8ae })
    );
    head.position.y = 1.6;
    ped.add(head);

    const torso = new THREE.Mesh(
      new THREE.BoxGeometry(0.45, 0.65, 0.25),
      new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.7 })
    );
    torso.position.y = 1.15;
    ped.add(torso);

    const legLeft = new THREE.Mesh(
      new THREE.BoxGeometry(0.18, 0.75, 0.2),
      new THREE.MeshStandardMaterial({ color: 0x1e293b })
    );
    legLeft.name = 'leg_left';
    legLeft.position.set(-0.12, 0.4, 0);
    ped.add(legLeft);

    const legRight = new THREE.Mesh(
      new THREE.BoxGeometry(0.18, 0.75, 0.2),
      new THREE.MeshStandardMaterial({ color: 0x1e293b })
    );
    legRight.name = 'leg_right';
    legRight.position.set(0.12, 0.4, 0);
    ped.add(legRight);

    return ped;
  };

  const createRealisticDeer = (): THREE.Group => {
    const deer = new THREE.Group();

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.6, 0.65, 1.4),
      new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.8 })
    );
    body.position.y = 0.85;
    deer.add(body);

    const headGroup = new THREE.Group();
    headGroup.name = 'deer_head';
    headGroup.position.set(0, 1.1, -0.6);

    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(0.12, 0.16, 0.5, 8),
      new THREE.MeshStandardMaterial({ color: 0x8b5a2b })
    );
    neck.rotation.x = Math.PI / 4;
    headGroup.add(neck);

    const head = new THREE.Mesh(
      new THREE.ConeGeometry(0.15, 0.4, 8),
      new THREE.MeshStandardMaterial({ color: 0x6e431f })
    );
    head.rotation.x = -Math.PI / 3;
    head.position.set(0, 0.3, -0.2);
    headGroup.add(head);

    const antler = new THREE.Mesh(
      new THREE.CylinderGeometry(0.02, 0.02, 0.4, 6),
      new THREE.MeshBasicMaterial({ color: 0xfafafa })
    );
    antler.position.set(0, 0.45, -0.15);
    headGroup.add(antler);

    deer.add(headGroup);

    [[-0.22, -0.45], [0.22, -0.45], [-0.22, 0.45], [0.22, 0.45]].forEach(([lx, lz]) => {
      const leg = new THREE.Mesh(
        new THREE.CylinderGeometry(0.05, 0.04, 0.75, 8),
        new THREE.MeshStandardMaterial({ color: 0x6e431f })
      );
      leg.position.set(lx, 0.38, lz);
      deer.add(leg);
    });

    return deer;
  };

  const createBusStopShelter = (): THREE.Group => {
    const busShelter = new THREE.Group();

    const roof = new THREE.Mesh(
      new THREE.BoxGeometry(2.4, 0.12, 5.2),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.2 })
    );
    roof.position.set(0, 2.7, 0);
    busShelter.add(roof);

    const glass = new THREE.Mesh(
      new THREE.BoxGeometry(0.08, 2.5, 4.8),
      new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.35, roughness: 0.1 })
    );
    glass.position.set(-1.0, 1.35, 0);
    busShelter.add(glass);

    [[-1.0, -2.3], [-1.0, 2.3], [1.0, -2.3], [1.0, 2.3]].forEach(([px, pz]) => {
      const pillar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.06, 0.06, 2.7, 12),
        new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.9 })
      );
      pillar.position.set(px, 1.35, pz);
      busShelter.add(pillar);
    });

    const bench = new THREE.Mesh(
      new THREE.BoxGeometry(0.6, 0.08, 3.2),
      new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.5 })
    );
    bench.position.set(-0.5, 0.45, 0);
    busShelter.add(bench);

    return busShelter;
  };

  // -------------------------------------------------------------
  // 6. FOVEATED SPATIAL GRIDS, RINGS & AXES
  // -------------------------------------------------------------
  const buildFoveatedSpatialGrid = (group: THREE.Group) => {
    while (group.children.length > 0) group.remove(group.children[0]);

    const createAnnularGridLines = (
      rMin: number,
      rMax: number,
      spacing: number,
      colorHex: number,
      opacity: number
    ): THREE.LineSegments => {
      const linePts: THREE.Vector3[] = [];
      const numLines = Math.floor(rMax / spacing);

      for (let i = -numLines; i <= numLines; i++) {
        const coord = i * spacing;
        if (Math.abs(coord) >= rMax) continue;

        const maxSpan = Math.sqrt(rMax * rMax - coord * coord);
        const minSpan = Math.abs(coord) < rMin ? Math.sqrt(rMin * rMin - coord * coord) : 0;

        if (minSpan === 0) {
          linePts.push(new THREE.Vector3(-maxSpan, 0.005, coord));
          linePts.push(new THREE.Vector3(maxSpan, 0.005, coord));
        } else {
          linePts.push(new THREE.Vector3(-maxSpan, 0.005, coord));
          linePts.push(new THREE.Vector3(-minSpan, 0.005, coord));
          linePts.push(new THREE.Vector3(minSpan, 0.005, coord));
          linePts.push(new THREE.Vector3(maxSpan, 0.005, coord));
        }
      }

      for (let i = -numLines; i <= numLines; i++) {
        const coord = i * spacing;
        if (Math.abs(coord) >= rMax) continue;

        const maxSpan = Math.sqrt(rMax * rMax - coord * coord);
        const minSpan = Math.abs(coord) < rMin ? Math.sqrt(rMin * rMin - coord * coord) : 0;

        if (minSpan === 0) {
          linePts.push(new THREE.Vector3(coord, 0.005, -maxSpan));
          linePts.push(new THREE.Vector3(coord, 0.005, maxSpan));
        } else {
          linePts.push(new THREE.Vector3(coord, 0.005, -maxSpan));
          linePts.push(new THREE.Vector3(coord, 0.005, -minSpan));
          linePts.push(new THREE.Vector3(coord, 0.005, minSpan));
          linePts.push(new THREE.Vector3(coord, 0.005, maxSpan));
        }
      }

      const geom = new THREE.BufferGeometry().setFromPoints(linePts);
      const mat = new THREE.LineBasicMaterial({ color: colorHex, transparent: true, opacity });
      return new THREE.LineSegments(geom, mat);
    };

    group.add(createAnnularGridLines(0.0, 10.0, 0.5, 0x10b981, 0.45));
    group.add(createAnnularGridLines(10.0, 25.0, 1.0, 0x38bdf8, 0.35));
    group.add(createAnnularGridLines(25.0, 50.0, 2.5, 0x8b5cf6, 0.3));
    group.add(createAnnularGridLines(50.0, 100.0, 5.0, 0xec4899, 0.25));
  };

  const buildFoveatedZoneDiscs = (group: THREE.Group) => {
    while (group.children.length > 0) group.remove(group.children[0]);

    const r0Mesh = new THREE.Mesh(
      new THREE.RingGeometry(0.8, 10.0, 64),
      new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.06, side: THREE.DoubleSide })
    );
    r0Mesh.rotation.x = -Math.PI / 2;
    group.add(r0Mesh);

    const r1Mesh = new THREE.Mesh(
      new THREE.RingGeometry(10.0, 25.0, 64),
      new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.04, side: THREE.DoubleSide })
    );
    r1Mesh.rotation.x = -Math.PI / 2;
    group.add(r1Mesh);

    const r2Mesh = new THREE.Mesh(
      new THREE.RingGeometry(25.0, 50.0, 64),
      new THREE.MeshBasicMaterial({ color: 0x8b5cf6, transparent: true, opacity: 0.03, side: THREE.DoubleSide })
    );
    r2Mesh.rotation.x = -Math.PI / 2;
    group.add(r2Mesh);

    const r3Mesh = new THREE.Mesh(
      new THREE.RingGeometry(50.0, 100.0, 64),
      new THREE.MeshBasicMaterial({ color: 0xec4899, transparent: true, opacity: 0.02, side: THREE.DoubleSide })
    );
    r3Mesh.rotation.x = -Math.PI / 2;
    group.add(r3Mesh);
  };

  const buildFoveatedRingsAndSpokes = (group: THREE.Group) => {
    while (group.children.length > 0) group.remove(group.children[0]);

    [
      { r: 5.0, color: 0x10b981 },
      { r: 10.0, color: 0x10b981 },
      { r: 25.0, color: 0x38bdf8 },
      { r: 50.0, color: 0x8b5cf6 },
      { r: 75.0, color: 0xc084fc },
      { r: 100.0, color: 0xec4899 },
    ].forEach((ring) => {
      const segments = 128;
      const geom = new THREE.BufferGeometry();
      const points: THREE.Vector3[] = [];
      for (let i = 0; i <= segments; i++) {
        const theta = (i / segments) * Math.PI * 2;
        points.push(new THREE.Vector3(Math.cos(theta) * ring.r, 0.02, Math.sin(theta) * ring.r));
      }
      geom.setFromPoints(points);
      const line = new THREE.Line(
        geom,
        new THREE.LineBasicMaterial({ color: ring.color, transparent: true, opacity: 0.75 })
      );
      group.add(line);
    });
  };

  const buildCoordinateAxesAndScales = (group: THREE.Group) => {
    while (group.children.length > 0) group.remove(group.children[0]);

    const xLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0.06, 30), new THREE.Vector3(0, 0.06, -100)]),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85 })
    );
    group.add(xLine);

    const yLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(60, 0.06, 0), new THREE.Vector3(-60, 0.06, 0)]),
      new THREE.LineBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.8 })
    );
    group.add(yLine);
  };

  // -------------------------------------------------------------
  // 7. UPDATE 3D LIDAR POINT CLOUD BUFFER
  // -------------------------------------------------------------
  useEffect(() => {
    if (!sceneRef.current) return;
    const scene = sceneRef.current;

    if (!showPoints || !frame || !frame.points || frame.points.length === 0) {
      if (pointsMeshRef.current) pointsMeshRef.current.visible = false;
      return;
    }

    const pts = frame.points;
    const classes = frame.semantic_classes || [];
    const intensities = frame.intensity || [];

    const validIndices: number[] = [];
    for (let i = 0; i < pts.length; i++) {
      const cls = classes[i] ?? 0;
      if (visibleClasses.has(cls)) validIndices.push(i);
    }

    const count = validIndices.length;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let idx = 0; idx < count; idx++) {
      const i = validIndices[idx];
      const [x_fwd, y_left, z_up] = pts[i];
      const cls = classes[i] ?? 0;
      const intens = intensities[i] ?? 0.5;

      positions[idx * 3] = -y_left;
      positions[idx * 3 + 1] = z_up;
      positions[idx * 3 + 2] = -x_fwd;

      const [r, g, b] = computePointColor(x_fwd, y_left, z_up, cls, intens, colorMode);
      colors[idx * 3] = r;
      colors[idx * 3 + 1] = g;
      colors[idx * 3 + 2] = b;
    }

    if (!pointsMeshRef.current) {
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const mat = new THREE.PointsMaterial({
        size: pointSize,
        map: globalPointTexture,
        vertexColors: true,
        sizeAttenuation: false,
        transparent: true,
        alphaTest: 0.02,
        opacity: 0.95,
      });

      const pointsMesh = new THREE.Points(geom, mat);
      scene.add(pointsMesh);
      pointsMeshRef.current = pointsMesh;
    } else {
      const geom = pointsMeshRef.current.geometry;
      geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      geom.attributes.position.needsUpdate = true;
      geom.attributes.color.needsUpdate = true;
      pointsMeshRef.current.visible = true;
      const mat = pointsMeshRef.current.material as THREE.PointsMaterial;
      mat.size = pointSize;
      mat.map = globalPointTexture;
      mat.needsUpdate = true;
    }
  }, [frame, colorMode, pointSize, visibleClasses, showPoints]);

  const computePointColor = (
    x: number,
    y: number,
    z: number,
    cls: number,
    intensity: number,
    mode: ColorMode
  ): [number, number, number] => {
    const dist = Math.hypot(x, y);

    if (mode === 'semantic') {
      const classInfo = SEMANTIC_CLASSES[cls] || SEMANTIC_CLASSES[7];
      return [classInfo.colorRgb[0] / 255, classInfo.colorRgb[1] / 255, classInfo.colorRgb[2] / 255];
    }

    if (mode === 'foveated') {
      if (dist < 10) return [0.06, 0.72, 0.5];
      if (dist < 25) return [0.22, 0.74, 0.97];
      if (dist < 50) return [0.65, 0.36, 0.97];
      return [0.93, 0.28, 0.6];
    }

    if (mode === 'elevation' || mode === 'terrain_3d') {
      const normZ = Math.min(1.0, Math.max(0.0, (z + 0.5) / 3.2));
      return [normZ * 0.8, 0.9 - normZ * 0.4, 0.95 - normZ * 0.6];
    }

    if (mode === 'anomaly_3d') {
      if (z < -0.05) return [0.95, 0.35, 0.15]; // Negative anomaly (Pothole drop)
      if (z > 0.1) return [0.95, 0.75, 0.05]; // Positive anomaly (Curb / Ridge / Obstacle)
      return [0.25, 0.55, 0.75]; // Stable road grade
    }

    if (mode === 'traversability') {
      if (cls === 0) return [0.06, 0.72, 0.5];
      if (cls === 1) return [0.96, 0.62, 0.04];
      return [0.95, 0.25, 0.37];
    }

    const val = Math.min(1.0, Math.max(0.1, intensity));
    return [val * 0.3, val * 0.85, val * 1.0];
  };

  // -------------------------------------------------------------
  // 8. TOGGLE LAYER VISIBILITIES
  // -------------------------------------------------------------
  useEffect(() => {
    if (foveatedGridGroupRef.current) foveatedGridGroupRef.current.visible = showFoveatedGrid;
    if (analyticalSurfaceGroupRef.current) analyticalSurfaceGroupRef.current.visible = showAnalyticalSurface;
    if (ringsGroupRef.current) ringsGroupRef.current.visible = showRings;
    if (zoneDiscsGroupRef.current) zoneDiscsGroupRef.current.visible = showZones;
    if (axesGroupRef.current) axesGroupRef.current.visible = showAxes;
    if (sweepGroupRef.current) sweepGroupRef.current.visible = showSweep;
    if (urbanChunksGroupRef.current) urbanChunksGroupRef.current.visible = showUrbanEnvironment;
  }, [showFoveatedGrid, showAnalyticalSurface, showRings, showZones, showAxes, showSweep, showUrbanEnvironment]);

  const applyCameraPreset = (preset: CameraViewPreset) => {
    if (!cameraRef.current || !controlsRef.current) return;
    setActiveCameraPreset(preset);

    if (preset === 'birds_eye') {
      cameraRef.current.position.set(0, 85, -0.01);
      controlsRef.current.target.set(0, 0, 15);
    } else if (preset === 'isometric') {
      cameraRef.current.position.set(-22, 24, -26);
      controlsRef.current.target.set(0, 0, 10);
    } else if (preset === 'ego_follow') {
      cameraRef.current.position.set(0, 5.5, 11);
      controlsRef.current.target.set(0, 1.6, -25);
    } else if (preset === 'cockpit') {
      cameraRef.current.position.set(0, 1.45, 0.4);
      controlsRef.current.target.set(0, 1.3, -40);
    }
    controlsRef.current.update();
  };

  const createLiDARRadarSweep = (): THREE.Group => {
    const sweepGroup = new THREE.Group();
    const sweepLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0.15, 0), new THREE.Vector3(0, 0.15, -100)]),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 3, transparent: true, opacity: 0.9 })
    );
    sweepGroup.add(sweepLine);

    const fanSegments = 24;
    const fanAngle = Math.PI / 4;
    const fanGeom = new THREE.BufferGeometry();
    const fanPositions: number[] = [];
    const fanColors: number[] = [];
    const sweepColor = new THREE.Color(0x38bdf8);

    for (let i = 0; i < fanSegments; i++) {
      const a1 = (i / fanSegments) * fanAngle;
      const a2 = ((i + 1) / fanSegments) * fanAngle;
      const alpha1 = Math.pow(1 - i / fanSegments, 1.8) * 0.25;
      const alpha2 = Math.pow(1 - (i + 1) / fanSegments, 1.8) * 0.25;
      const r = 98.0;

      fanPositions.push(0, 0.12, 0);
      fanPositions.push(Math.sin(a1) * r, 0.12, -Math.cos(a1) * r);
      fanPositions.push(Math.sin(a2) * r, 0.12, -Math.cos(a2) * r);

      fanColors.push(sweepColor.r, sweepColor.g, sweepColor.b);
      fanColors.push(sweepColor.r * alpha1, sweepColor.g * alpha1, sweepColor.b * alpha1);
      fanColors.push(sweepColor.r * alpha2, sweepColor.g * alpha2, sweepColor.b * alpha2);
    }

    fanGeom.setAttribute('position', new THREE.Float32BufferAttribute(fanPositions, 3));
    fanGeom.setAttribute('color', new THREE.Float32BufferAttribute(fanColors, 3));

    const fanMesh = new THREE.Mesh(
      fanGeom,
      new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false })
    );
    sweepGroup.add(fanMesh);

    return sweepGroup;
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-[#0a0e14] overflow-hidden select-none border border-hud-border/70 rounded-2xl shadow-panel ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none border-none' : ''
      }`}
    >
      <div
        ref={canvasWrapperRef}
        className="w-full h-full touch-none select-none relative"
        style={{ touchAction: 'none' }}
      />

      {/* TOP FLOATING HUD BAR */}
      <div className="absolute top-3.5 left-4 right-4 z-20 flex items-center justify-between pointer-events-none gap-2">
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="glass-panel px-3 py-1.5 rounded-xl flex items-center gap-2 text-xs font-mono">
            <span className="w-2.5 h-2.5 rounded-full bg-hud-cyan animate-ping shadow-cyan-glow-sm" />
            <span className="text-hud-cyan font-bold tracking-wider font-display">3D SCIENTIFIC ANOMALY SURFACE</span>
            <span className="text-slate-600">|</span>
            <span className="text-hud-emerald font-semibold">0m – 100m TOPOGRAPHIC ELEVATION</span>
          </div>

          <div className="glass-panel p-1 rounded-xl flex items-center gap-1 text-xs">
            {(['isometric', 'birds_eye', 'ego_follow', 'cockpit'] as const).map((preset) => (
              <button
                key={preset}
                onClick={() => applyCameraPreset(preset)}
                className={`px-2.5 py-1 rounded-lg font-mono font-bold transition uppercase text-[10.5px] ${
                  activeCameraPreset === preset
                    ? 'bg-hud-cyan text-slate-950 shadow-cyan-glow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                {preset === 'isometric' ? '2.5D ISO' : preset === 'birds_eye' ? 'TOP-DOWN' : preset === 'ego_follow' ? 'EGO-CHASE' : 'COCKPIT'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="glass-panel p-1 rounded-xl flex items-center gap-1 text-[11px] font-mono">
            {/* Toggle 3D Analytical Surface */}
            <button
              onClick={() => setShowAnalyticalSurface(!showAnalyticalSurface)}
              className={`px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition ${
                showAnalyticalSurface
                  ? 'bg-hud-cyan text-slate-950 font-bold shadow-cyan-glow-sm'
                  : 'text-slate-400 hover:bg-slate-800/50'
              }`}
              title="Toggle 3D Analytical Topographic Surface"
            >
              <Scan className="w-3.5 h-3.5" />
              <span>3D SURFACE {showAnalyticalSurface ? 'ON' : 'OFF'}</span>
            </button>

            {/* Mode: ANOMALY 3D vs TERRAIN 3D */}
            <button
              onClick={() => onColorModeChange(colorMode === 'anomaly_3d' ? 'terrain_3d' : 'anomaly_3d')}
              className={`px-2 py-1 rounded-lg flex items-center gap-1 transition ${
                colorMode === 'anomaly_3d' || colorMode === 'terrain_3d'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
                  : 'text-slate-400 hover:bg-slate-800/50'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>{colorMode === 'anomaly_3d' ? 'ANOMALY 3D' : 'TERRAIN 3D'}</span>
            </button>

            <button
              onClick={() => setShowUrbanEnvironment(!showUrbanEnvironment)}
              className={`px-2 py-1 rounded-lg flex items-center gap-1 transition ${
                showUrbanEnvironment ? 'text-hud-emerald font-bold' : 'text-slate-400'
              }`}
            >
              <Car className="w-3.5 h-3.5" />
              <span>WORLD</span>
            </button>

            <button
              onClick={() => setShowPoints(!showPoints)}
              className={`px-2 py-1 rounded-lg flex items-center gap-1 transition ${
                showPoints ? 'text-purple-300 font-bold' : 'text-slate-400'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>POINTS</span>
            </button>
          </div>

          <button
            onClick={() => applyCameraPreset('isometric')}
            className="glass-panel p-2 rounded-xl text-slate-300 hover:text-hud-cyan transition"
            title="Reset Camera View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="glass-panel p-2 rounded-xl text-slate-300 hover:text-hud-cyan transition"
          >
            {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* DRDO DEFENCE R&D 3D SCIENTIFIC CELL & ANOMALY INSPECTOR PANEL */}
      {selectedAnomaly && (
        <div className="absolute top-16 right-4 z-30 w-80 animate-in slide-in-from-right-10 duration-200 pointer-events-auto font-mono text-xs select-none">
          <div className="glass-panel p-3.5 rounded-2xl bg-slate-950/95 border border-amber-500/60 shadow-2xl flex flex-col gap-2.5 backdrop-blur-xl">
            {/* Header */}
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40">
                  <Target className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-bold text-white text-[12px] font-display tracking-wide">
                    {selectedAnomaly.name}
                  </div>
                  <div className="text-[9.5px] text-amber-400 font-bold">
                    {selectedAnomaly.id} • {selectedAnomaly.type.toUpperCase()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedAnomaly(null);
                  if (anomalySelectionGroupRef.current) {
                    while (anomalySelectionGroupRef.current.children.length > 0) {
                      anomalySelectionGroupRef.current.remove(anomalySelectionGroupRef.current.children[0]);
                    }
                  }
                }}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scientific Parameters Data Grid */}
            <div className="grid grid-cols-2 gap-2 text-[10.5px]">
              <div className="p-2 rounded-lg bg-black/60 border border-slate-800">
                <div className="text-[9px] text-slate-400 font-medium">RADIAL DISTANCE</div>
                <div className="text-white font-bold text-xs">{selectedAnomaly.distance} m</div>
                <div className="text-[8.5px] text-hud-cyan">Foveation Range</div>
              </div>

              <div className="p-2 rounded-lg bg-black/60 border border-slate-800">
                <div className="text-[9px] text-slate-400 font-medium">LOCAL RESOLUTION</div>
                <div className="text-hud-emerald font-bold text-xs">{selectedAnomaly.resolution}</div>
                <div className="text-[8.5px] text-hud-emerald font-semibold">Refined Cell Mesh</div>
              </div>

              <div className="p-2 rounded-lg bg-black/60 border border-slate-800">
                <div className="text-[9px] text-slate-400 font-medium">MEASURED ELEVATION (Z)</div>
                <div className="text-amber-400 font-black text-xs">
                  {selectedAnomaly.elevation < 0 ? `${(selectedAnomaly.elevation * 100).toFixed(1)} cm` : `+${(selectedAnomaly.elevation * 100).toFixed(1)} cm`}
                </div>
                <div className="text-[8.5px] text-slate-400">Mean Surface Height</div>
              </div>

              <div className="p-2 rounded-lg bg-black/60 border border-slate-800">
                <div className="text-[9px] text-slate-400 font-medium">ELEVATION ENVELOPE</div>
                <div className="text-white font-bold text-xs">
                  {(selectedAnomaly.minZ * 100).toFixed(0)}cm &rarr; {(selectedAnomaly.maxZ * 100).toFixed(0)}cm
                </div>
                <div className="text-[8.5px] text-slate-400">&Delta;Z = {(selectedAnomaly.deltaZ * 100).toFixed(1)}cm</div>
              </div>

              <div className="p-2 rounded-lg bg-black/60 border border-slate-800">
                <div className="text-[9px] text-slate-400 font-medium">SURFACE ROUGHNESS</div>
                <div className="text-purple-300 font-bold text-xs">
                  &sigma;z = {(selectedAnomaly.roughness * 100).toFixed(1)} cm
                </div>
                <div className="text-[8.5px] text-slate-400">Height Variance</div>
              </div>

              <div className="p-2 rounded-lg bg-black/60 border border-slate-800">
                <div className="text-[9px] text-slate-400 font-medium">POINT RETURNS (N)</div>
                <div className="text-white font-bold text-xs">{selectedAnomaly.pointCount} pts</div>
                <div className="text-[8.5px] text-slate-400">Refined Density</div>
              </div>
            </div>

            {/* Traversability & Semantic Risk Tag */}
            <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col gap-1">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400 font-medium">TRAVERSABILITY ASSESSMENT:</span>
                <span className={`px-2 py-0.5 rounded font-bold text-[9px] ${
                  selectedAnomaly.isTraversable
                    ? 'bg-hud-emerald/20 text-hud-emerald border border-hud-emerald/40'
                    : 'bg-red-500/20 text-red-400 border border-red-500/40'
                }`}>
                  {selectedAnomaly.isTraversable ? 'TRAVERSABLE' : 'NON-TRAVERSABLE RISK'}
                </span>
              </div>
              <div className="text-[9.5px] text-slate-300">
                Class: <span className="font-bold text-white">{selectedAnomaly.semanticClass}</span> (Confidence: {(selectedAnomaly.confidence * 100).toFixed(1)}%)
              </div>
            </div>

            {/* Camera Actions & Data Provenance */}
            <div className="flex items-center gap-2 pt-1 border-t border-slate-800">
              <button
                onClick={() => focusCameraOnAnomaly(selectedAnomaly)}
                className="flex-1 py-1.5 rounded-lg bg-hud-cyan text-slate-950 font-bold text-[10.5px] hover:bg-hud-cyan/90 transition flex items-center justify-center gap-1 cursor-pointer"
              >
                <Crosshair className="w-3.5 h-3.5" />
                <span>INSPECT FOCUS</span>
              </button>

              <button
                onClick={() => {
                  if (onOpenResolution) onOpenResolution();
                }}
                className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white text-[10.5px] font-semibold cursor-pointer"
              >
                FOVEATION
              </button>
            </div>

            <div className="text-[8.5px] text-slate-500 text-center font-mono">
              PROVENANCE: {selectedAnomaly.provenance}
            </div>
          </div>
        </div>
      )}

      {/* BOTTOM-RIGHT POV ROTATION & ZOOM TOOLBAR */}
      <div className="absolute bottom-4 right-4 z-20 flex items-center gap-1.5 pointer-events-auto font-mono text-xs">
        <div className="glass-panel p-1.5 rounded-2xl flex items-center gap-1 bg-slate-950/80 border border-slate-700/60 shadow-xl">
          <button
            onClick={orbitLeft}
            className="p-1.5 rounded-lg text-slate-300 hover:text-hud-cyan hover:bg-slate-800 transition"
            title="Orbit Left"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={orbitRight}
            className="p-1.5 rounded-lg text-slate-300 hover:text-hud-cyan hover:bg-slate-800 transition"
            title="Orbit Right"
          >
            <RotateCw className="w-4 h-4" />
          </button>
          <div className="w-[1px] h-4 bg-slate-700 mx-0.5" />
          <button
            onClick={tiltUp}
            className="p-1.5 rounded-lg text-slate-300 hover:text-hud-cyan hover:bg-slate-800 transition"
            title="Tilt Up"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
          <button
            onClick={tiltDown}
            className="p-1.5 rounded-lg text-slate-300 hover:text-hud-cyan hover:bg-slate-800 transition"
            title="Tilt Down"
          >
            <ArrowDown className="w-4 h-4" />
          </button>
          <div className="w-[1px] h-4 bg-slate-700 mx-0.5" />
          <button
            onClick={zoomIn}
            className="p-1.5 rounded-lg text-slate-300 hover:text-hud-cyan hover:bg-slate-800 transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={zoomOut}
            className="p-1.5 rounded-lg text-slate-300 hover:text-hud-cyan hover:bg-slate-800 transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
