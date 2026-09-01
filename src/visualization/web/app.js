/**
 * LiDAR_SYNTRIX — Autonomous Perception Control Center & 3D WebGL Engine
 * Module: src/visualization/web/app.js
 * Owner: Atharva (src/integration/ & src/visualization/)
 *
 * Capabilities:
 *  - Three.js WebGL 3D Spatial Environment (Physical 3D World vs 2.5D Computational Overlay)
 *  - Fictional Autonomous Research UGV with Roof-Mounted Rotating LiDAR & Laser Fan
 *  - Multi-Resolution Foveated Spatial Grid (5cm, 10cm, 25cm, 50cm visible geometry)
 *  - 6 Perception Modes: FOVEATED, SEMANTIC, ELEVATION, TRAVERSABILITY, RAW, BENCHMARK
 *  - Interactive 3D Raycasting Cell Inspector & "Why This Resolution?" Explainer
 *  - Hero Video Stream with Scroll-Controlled Perception Milestones (0%, 20%, 40%, 60%, 80%, 100%)
 *  - Live Measured Telemetry HUD (FPS, RAM RSS, per-stage latencies, cell count)
 *  - Multi-Camera Views (Follow UGV, Top-Down Tactical, Sensor POV, Free Orbit)
 *  - Zero-Fabrication Metric Principles & 2D Canvas Fallback
 */

// 8-Class Semantic Taxonomy & Standard Color Mapping (CONTRACTS.md)
const CLASS_COLORS_HEX = {
  0: 0x804080, // DRIVABLE_GROUND
  1: 0x006400, // NON_DRIVABLE_TERRAIN
  2: 0x00008e, // VEHICLE
  3: 0xdc143c, // PEDESTRIAN (VRU)
  4: 0xff0000, // CYCLIST (VRU)
  5: 0x999999, // POLE / TREE
  6: 0x464646, // WALL / BUILDING
  7: 0xfaaa1e, // OTHER_OBSTACLE
};

const CLASS_COLORS_CSS = {
  0: '#804080',
  1: '#006400',
  2: '#00008E',
  3: '#DC143C',
  4: '#FF0000',
  5: '#999999',
  6: '#464646',
  7: '#FAAA1E',
};

const CLASS_NAMES = {
  0: 'DRIVABLE_GROUND',
  1: 'NON_DRIVABLE_TERRAIN',
  2: 'VEHICLE',
  3: 'PEDESTRIAN',
  4: 'CYCLIST',
  5: 'POLE',
  6: 'WALL_BUILDING',
  7: 'OTHER_OBSTACLE',
};

const RESOLUTION_BY_RING = {
  near: 0.05,     // R0: 5 cm (0-10m)
  mid_near: 0.10, // R1: 10 cm (10-25m)
  mid: 0.25,      // R2: 25 cm (25-50m)
  far: 0.50,      // R3: 50 cm (50-100m)
};

// ============================================================================
// 1. PERSISTENT BACKGROUND VIDEO CONTROLLER (CONTINUOUS AMBIENT STREAM)
// ============================================================================
class HeroVideoController {
  constructor() {
    this.video = document.getElementById('hero-video');
    this.fallback = document.getElementById('video-fallback');
    this.archBtn = document.getElementById('btn-open-architecture');
    this.showArchBtn = document.getElementById('btn-show-arch');
    this.archModal = document.getElementById('arch-modal');
    this.closeArchBtn = document.getElementById('btn-close-arch');

    this.initVideo();
    this.bindEvents();
  }

  initVideo() {
    if (!this.video) return;

    // Handle video load error gracefully with radar fallback
    this.video.addEventListener('error', () => {
      console.warn('Hero video failed to load, activating technical simulation fallback.');
      if (this.fallback) this.fallback.style.display = 'flex';
      if (this.video) this.video.style.display = 'none';
    });

    // Muted autoplay with seamless loop running throughout background
    this.video.muted = true;
    this.video.loop = true;
    this.video.playsInline = true;

    const startPlay = () => {
      const playPromise = this.video.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.log('Background video autoplay waiting for user interaction:', err);
          const onFirstTouch = () => {
            this.video.play().catch(() => {});
            window.removeEventListener('click', onFirstTouch);
            window.removeEventListener('keydown', onFirstTouch);
          };
          window.addEventListener('click', onFirstTouch, { once: true });
          window.addEventListener('keydown', onFirstTouch, { once: true });
        });
      }
    };

    startPlay();
  }

  bindEvents() {
    // Architecture Modal Handlers
    const openArch = () => {
      if (this.archModal) {
        this.archModal.style.display = 'flex';
        this.fetchArchitectureData();
      }
    };
    if (this.archBtn) this.archBtn.addEventListener('click', openArch);
    if (this.showArchBtn) this.showArchBtn.addEventListener('click', openArch);
    if (this.closeArchBtn) {
      this.closeArchBtn.addEventListener('click', () => {
        if (this.archModal) this.archModal.style.display = 'none';
      });
    }
    if (this.archModal) {
      this.archModal.addEventListener('click', (e) => {
        if (e.target === this.archModal) {
          this.archModal.style.display = 'none';
        }
      });
    }
  }

  async fetchArchitectureData() {
    const list = document.getElementById('arch-stages-list');
    if (!list) return;
    try {
      const res = await fetch('/api/architecture');
      if (!res.ok) return;
      const data = await res.json();
      let html = '';
      data.pipeline_stages.forEach((s) => {
        html += `
          <div class="arch-stage-card">
            <div class="arch-stage-num">0${s.stage_id}</div>
            <div>
              <div class="arch-stage-name">${s.name}</div>
              <div class="arch-stage-owner">Owner: ${s.owner} (${s.module})</div>
            </div>
            <div>
              <div class="arch-stage-contracts">Input: ${s.input}</div>
              <div class="arch-stage-contracts">Output: ${s.output}</div>
            </div>
            <div class="arch-stage-contracts">
              <strong>${s.resolution}</strong>
            </div>
            <div class="arch-stage-status">● ${s.status}</div>
          </div>
        `;
      });
      list.innerHTML = html;
    } catch (err) {
      console.warn('Failed to fetch architecture data:', err);
    }
  }
}

// ============================================================================
// 2. THREE.JS WEBGL 3D PERCEPTION ENGINE (PHASE 3, 4, 5, 8, 10, 20, 21)
// ============================================================================
class ThreePerceptionEngine {
  constructor() {
    this.container = document.getElementById('three-container');
    this.canvas2D = document.getElementById('perception-canvas');

    this.viewMode = 'foveated';
    this.cameraView = 'follow'; // 'follow' | 'topdown' | 'sensor' | 'free'
    this.showPhysicalWorld = true;
    this.showGridWireframe = true;

    this.currentFrame = null;
    this.isPlaying = true;
    this.pollInterval = null;
    this.targetFps = 10;

    // Raycasting & Interactive Inspection
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2(-999, -999);
    this.hoveredCell = null;
    this.selectedCell = null;

    // Three.js Core Objects
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.clock = new THREE.Clock();

    // Scene Graph Groups
    this.physicalGroup = new THREE.Group();
    this.computationalGroup = new THREE.Group();
    this.pointCloudObject = null;
    this.cellsMeshGroup = new THREE.Group();
    this.foveaRingsGroup = new THREE.Group();
    this.ugvMesh = null;
    this.lidarEmitter = null;
    this.laserFanMesh = null;
    this.highlightBox = null;

    // Cell spatial registry for fast lookup: key -> { cell, mesh, x, y, z, size }
    this.cellRegistry = new Map();

    this.init();
  }

  init() {
    if (typeof THREE === 'undefined') {
      console.warn('Three.js not loaded, switching to 2D canvas fallback.');
      this.init2DFallback();
      return;
    }

    try {
      this.initThree();
      this.buildPhysicalWorld();
      this.buildFoveationRings();
      this.buildHighlightBox();
      this.bindUIEvents();
      this.startPolling();
      this.fetchBenchmarkStats();
      this.animate();
    } catch (e) {
      console.error('WebGL 3D Engine Initialization failed:', e);
      this.init2DFallback();
    }
  }

  initThree() {
    const width = this.container.clientWidth || window.innerWidth * 0.5;
    const height = this.container.clientHeight || window.innerHeight * 0.6;

    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x080b10);
    this.scene.fog = new THREE.FogExp2(0x080b10, 0.008);

    // 2. Camera (Z is up in our coordinate system, so we orient accordingly)
    this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 500);
    this.setCameraView(this.cameraView);

    // 3. WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    // 4. OrbitControls for free camera mode
    if (typeof THREE.OrbitControls !== 'undefined') {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
      this.controls.maxPolarAngle = Math.PI / 2 - 0.02; // prevent going below ground
      this.controls.minDistance = 2.0;
      this.controls.maxDistance = 200.0;
      this.controls.target.set(0, 0, 0);
    }

    // 5. Lighting (Restrained Defence R&D Technical Atmosphere)
    const ambientLight = new THREE.AmbientLight(0xd0e0f0, 0.6);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(30, -40, 60);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 250;
    const d = 50;
    dirLight.shadow.camera.left = -d;
    dirLight.shadow.camera.right = d;
    dirLight.shadow.camera.top = d;
    dirLight.shadow.camera.bottom = -d;
    this.scene.add(dirLight);

    // Subtle Cyan Rim Light
    const rimLight = new THREE.DirectionalLight(0x00f0ff, 0.3);
    rimLight.position.set(-30, 40, 20);
    this.scene.add(rimLight);

    // Add Main Groups
    this.scene.add(this.physicalGroup);
    this.scene.add(this.computationalGroup);
    this.computationalGroup.add(this.cellsMeshGroup);
    this.computationalGroup.add(this.foveaRingsGroup);

    // Window Resize Handler
    window.addEventListener('resize', () => {
      if (!this.container || !this.renderer || !this.camera) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    });
  }

  // ==========================================================================
  // PHYSICAL 3D WORLD (PHASE 4, 5, 20)
  // ==========================================================================
  buildPhysicalWorld() {
    // 1. Terrain Ground Mesh with Asphalt Test Track
    const terrainGeo = new THREE.PlaneGeometry(240, 240, 64, 64);
    // Orient plane with +Z as Up: Three.js Plane is XY, rotate X -90deg so +Y becomes +Z or build custom
    terrainGeo.rotateX(-Math.PI / 2); // Now Y is up in standard Three.js (we map our X->Z, Y->X or maintain standard)
    
    // Shader or canvas texture for asphalt track & terrain
    const groundCanvas = document.createElement('canvas');
    groundCanvas.width = 512;
    groundCanvas.height = 512;
    const gctx = groundCanvas.getContext('2d');
    gctx.fillStyle = '#141820';
    gctx.fillRect(0, 0, 512, 512);

    // Asphalt Road Center
    gctx.fillStyle = '#222834';
    gctx.fillRect(200, 0, 112, 512);
    // Road Dash Lines
    gctx.strokeStyle = '#475569';
    gctx.lineWidth = 4;
    gctx.setLineDash([16, 16]);
    gctx.beginPath();
    gctx.moveTo(256, 0);
    gctx.lineTo(256, 512);
    gctx.stroke();

    const groundTex = new THREE.CanvasTexture(groundCanvas);
    groundTex.wrapS = THREE.RepeatWrapping;
    groundTex.wrapT = THREE.RepeatWrapping;
    groundTex.repeat.set(12, 12);

    const groundMat = new THREE.MeshStandardMaterial({
      map: groundTex,
      roughness: 0.85,
      metalness: 0.15,
    });
    const groundMesh = new THREE.Mesh(terrainGeo, groundMat);
    groundMesh.receiveShadow = true;
    groundMesh.position.y = -0.05; // slightly below computational cells
    this.physicalGroup.add(groundMesh);

    // 2. Fictional Rugged Autonomous Research UGV (Canonical SIH Defence Model)
    this.ugvMesh = this.createUGVModel();
    this.physicalGroup.add(this.ugvMesh);

    // 3. Roadside Obstacles, Barrier Walls, Trees, and Hazard Landmarks
    this.populatePhysicalEnvironment();
  }

  createUGVModel() {
    const ugv = new THREE.Group();

    // Chassis / Body (Graphite Metallic)
    const bodyGeo = new THREE.BoxGeometry(2.0, 0.9, 4.4); // width (X), height (Y), length (Z)
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x1e242b,
      roughness: 0.5,
      metalness: 0.6,
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 0.85;
    body.castShadow = true;
    body.receiveShadow = true;
    ugv.add(body);

    // Muted Olive Armor Plating Accents
    const armorGeo = new THREE.BoxGeometry(2.1, 0.4, 3.2);
    const armorMat = new THREE.MeshStandardMaterial({
      color: 0x4a5842,
      roughness: 0.7,
      metalness: 0.3,
    });
    const armor = new THREE.Mesh(armorGeo, armorMat);
    armor.position.y = 0.9;
    armor.castShadow = true;
    ugv.add(armor);

    // Rugged Tread Wheels (4x)
    const wheelGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.45, 24);
    wheelGeo.rotateZ(Math.PI / 2);
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111317, roughness: 0.9 });
    const hubMat = new THREE.MeshStandardMaterial({ color: 0x6b7c63, metalness: 0.8 });

    const wheelPositions = [
      [-1.15, 0.5, 1.4],
      [1.15, 0.5, 1.4],
      [-1.15, 0.5, -1.4],
      [1.15, 0.5, -1.4],
    ];

    wheelPositions.forEach((pos) => {
      const wheel = new THREE.Mesh(wheelGeo, wheelMat);
      wheel.position.set(...pos);
      wheel.castShadow = true;
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.48, 16), hubMat);
      hub.rotateZ(Math.PI / 2);
      wheel.add(hub);
      ugv.add(wheel);
    });

    // Sensor Mast (Roof Mount)
    const mastGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.6, 12);
    const mastMat = new THREE.MeshStandardMaterial({ color: 0x2d3748, metalness: 0.8 });
    const mast = new THREE.Mesh(mastGeo, mastMat);
    mast.position.set(0, 1.55, 0.4);
    ugv.add(mast);

    // Rotating LiDAR Sensor Unit
    this.lidarEmitter = new THREE.Group();
    const lidarGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.3, 24);
    const lidarMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.3,
      metalness: 0.9,
    });
    const lidarCylinder = new THREE.Mesh(lidarGeo, lidarMat);
    this.lidarEmitter.add(lidarCylinder);

    // Glowing Optical Ring on LiDAR
    const ringGeo = new THREE.TorusGeometry(0.255, 0.02, 12, 32);
    ringGeo.rotateX(Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const glowRing = new THREE.Mesh(ringGeo, ringMat);
    this.lidarEmitter.add(glowRing);

    // Laser Fan Beam (Forward Scanning Visual Arc)
    const fanGeo = new THREE.ConeGeometry(8.0, 14.0, 16, 1, true, 0, Math.PI / 3);
    fanGeo.rotateX(Math.PI / 2);
    fanGeo.rotateY(Math.PI / 3 / 2);
    const fanMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this.laserFanMesh = new THREE.Mesh(fanGeo, fanMat);
    this.laserFanMesh.position.set(0, 0, 7.0);
    this.lidarEmitter.add(this.laserFanMesh);

    this.lidarEmitter.position.set(0, 1.9, 0.4);
    ugv.add(this.lidarEmitter);

    return ugv;
  }

  populatePhysicalEnvironment() {
    // 1. Concrete Barrier Walls (WALL_BUILDING - Class 6)
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x3f4a56, roughness: 0.8 });
    const wallGeo = new THREE.BoxGeometry(0.6, 1.4, 18.0);
    
    const leftWall = new THREE.Mesh(wallGeo, wallMat);
    leftWall.position.set(-9.0, 0.7, 18.0);
    leftWall.castShadow = true;
    leftWall.receiveShadow = true;
    this.physicalGroup.add(leftWall);

    const rightWall = new THREE.Mesh(wallGeo, wallMat);
    rightWall.position.set(9.0, 0.7, 32.0);
    rightWall.castShadow = true;
    rightWall.receiveShadow = true;
    this.physicalGroup.add(rightWall);

    // 2. Roadside Poles / Trees (POLE - Class 5)
    const poleGeo = new THREE.CylinderGeometry(0.12, 0.12, 5.0, 12);
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x808b96, metalness: 0.6 });
    const lampMat = new THREE.MeshBasicMaterial({ color: 0xffeedd });

    [-12.0, 12.0].forEach((sideX) => {
      for (let z = 5.0; z <= 65.0; z += 18.0) {
        const pole = new THREE.Mesh(poleGeo, poleMat);
        pole.position.set(sideX, 2.5, z);
        pole.castShadow = true;

        const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.2, 0.3), lampMat);
        lamp.position.set(sideX > 0 ? -0.4 : 0.4, 2.4, 0);
        pole.add(lamp);

        this.physicalGroup.add(pole);
      }
    });

    // 3. Parked Hazard Vehicle (VEHICLE - Class 2)
    const vehGeo = new THREE.BoxGeometry(2.1, 1.4, 4.6);
    const vehMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, metalness: 0.5, roughness: 0.5 });
    const obstacleVeh = new THREE.Mesh(vehGeo, vehMat);
    obstacleVeh.position.set(4.5, 0.7, 24.0);
    obstacleVeh.castShadow = true;
    this.physicalGroup.add(obstacleVeh);

    // 4. VRU Pedestrian Hazard (PEDESTRIAN - Class 3)
    const pedGroup = new THREE.Group();
    const pedBody = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 1.4, 12), new THREE.MeshStandardMaterial({ color: 0xdc143c }));
    pedBody.position.y = 0.7;
    const pedHead = new THREE.Mesh(new THREE.SphereGeometry(0.2, 16, 16), new THREE.MeshStandardMaterial({ color: 0xfbbf24 }));
    pedHead.position.y = 1.55;
    pedGroup.add(pedBody);
    pedGroup.add(pedHead);
    pedGroup.position.set(-3.5, 0, 14.0);
    pedGroup.castShadow = true;
    this.physicalGroup.add(pedGroup);

    // 5. Road Debris / Rock Hazard (OTHER_OBSTACLE - Class 7)
    const rockGeo = new THREE.DodecahedronGeometry(0.65);
    const rockMat = new THREE.MeshStandardMaterial({ color: 0x9a3412, roughness: 0.9 });
    const rock = new THREE.Mesh(rockGeo, rockMat);
    rock.position.set(1.2, 0.35, 16.0);
    rock.castShadow = true;
    this.physicalGroup.add(rock);
  }

  // ==========================================================================
  // COMPUTATIONAL 2.5D MULTI-RESOLUTION WORLD (PHASE 5, 8, 9, 10)
  // ==========================================================================
  buildFoveationRings() {
    const ringConfigs = [
      { r: 10, color: 0x00f0ff, label: 'R0 (5cm)' },
      { r: 25, color: 0x10b981, label: 'R1 (10cm)' },
      { r: 50, color: 0xf59e0b, label: 'R2 (25cm)' },
      { r: 100, color: 0xa855f7, label: 'R3 (50cm)' },
    ];

    ringConfigs.forEach(({ r, color }) => {
      const ringGeo = new THREE.RingGeometry(r - 0.08, r + 0.08, 64);
      ringGeo.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.5,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.y = 0.02;
      this.foveaRingsGroup.add(ringMesh);
    });
  }

  buildHighlightBox() {
    const boxGeo = new THREE.BoxGeometry(1, 1, 1);
    const edges = new THREE.EdgesGeometry(boxGeo);
    this.highlightBox = new THREE.LineSegments(
      edges,
      new THREE.LineBasicMaterial({ color: 0x00f0ff, linewidth: 2 })
    );
    this.highlightBox.visible = false;
    this.scene.add(this.highlightBox);
  }

  updateComputationalCells(cellsData) {
    if (!cellsData) return;

    // Clear previous cell meshes
    while (this.cellsMeshGroup.children.length > 0) {
      const obj = this.cellsMeshGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
      this.cellsMeshGroup.remove(obj);
    }
    this.cellRegistry.clear();

    const keys = Object.keys(cellsData);
    if (keys.length === 0) return;

    // Build geometry for multi-resolution cells
    // In our coordinate mapping: Map X (Forward) -> Three.js +Z, Map Y (Left) -> Three.js -X, Map Z (Up) -> Three.js +Y
    keys.forEach((key) => {
      const cell = cellsData[key];
      const resM = RESOLUTION_BY_RING[cell.resolution_level] || 0.25;

      const posX = -cell.cell_y; // lateral offset
      const posZ = cell.cell_x;  // forward distance
      const posY = Math.max(0.01, cell.elevation + 0.04);
      const height = Math.max(0.04, (cell.max_z - cell.min_z) || 0.05);

      const cellColor = this.computeCellColor(cell);

      const boxGeo = new THREE.BoxGeometry(resM * 0.96, height, resM * 0.96);
      const boxMat = new THREE.MeshStandardMaterial({
        color: cellColor,
        roughness: 0.6,
        metalness: 0.2,
        transparent: true,
        opacity: this.viewMode === 'raw' ? 0.3 : 0.88,
      });

      const cellMesh = new THREE.Mesh(boxGeo, boxMat);
      cellMesh.position.set(posX, posY + height / 2, posZ);
      cellMesh.receiveShadow = true;
      cellMesh.userData = { cellKey: key, cellData: cell };

      // Optional crisp wireframe overlay for foveation visibility
      if (this.showGridWireframe && (resM >= 0.1 || this.cameraView === 'follow')) {
        const wireEdges = new THREE.EdgesGeometry(boxGeo);
        const wireLine = new THREE.LineSegments(
          wireEdges,
          new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.15 })
        );
        cellMesh.add(wireLine);
      }

      this.cellsMeshGroup.add(cellMesh);
      this.cellRegistry.set(key, {
        cell,
        mesh: cellMesh,
        posX,
        posY,
        posZ,
        size: resM,
      });
    });
  }

  computeCellColor(cell) {
    if (this.viewMode === 'semantic') {
      return CLASS_COLORS_HEX[cell.semantic_class] || 0x475569;
    } else if (this.viewMode === 'elevation') {
      // Height gradient colormap [-0.2m, 2.0m]
      const normZ = Math.max(0, Math.min(1, (cell.elevation + 0.2) / 2.0));
      const color = new THREE.Color();
      color.setHSL((1.0 - normZ) * 0.66, 0.9, 0.45); // Blue (low) -> Green -> Red (high)
      return color.getHex();
    } else if (this.viewMode === 'traversability') {
      if (cell.semantic_class === 0) return 0x10b981; // Drivable (Green)
      if (cell.semantic_class === 1) return 0xf59e0b; // Terrain/Curb (Amber)
      return 0xef4444; // Lethal Obstacle (Red)
    } else if (this.viewMode === 'benchmark') {
      // Highlight foveated allocation: 5cm cyan, 10cm emerald, 25cm amber, 50cm purple
      if (cell.resolution_level === 'near') return 0x00f0ff;
      if (cell.resolution_level === 'mid_near') return 0x10b981;
      if (cell.resolution_level === 'mid') return 0xf59e0b;
      return 0xa855f7;
    } else {
      // Default: FOVEATED Mode (Semantic with ring luminance)
      return CLASS_COLORS_HEX[cell.semantic_class] || 0x334155;
    }
  }

  updatePointCloud(points, classes, intensities) {
    if (!points || points.length === 0) return;

    if (this.pointCloudObject) {
      this.scene.remove(this.pointCloudObject);
      if (this.pointCloudObject.geometry) this.pointCloudObject.geometry.dispose();
      if (this.pointCloudObject.material) this.pointCloudObject.material.dispose();
      this.pointCloudObject = null;
    }

    const count = points.length;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const p = points[i];
      positions[i * 3] = -p[1];     // Lateral X
      positions[i * 3 + 1] = p[2];  // Height Y (Up)
      positions[i * 3 + 2] = p[0];  // Forward Z

      let col = new THREE.Color(0x00f0ff);
      if (this.viewMode === 'raw') {
        const val = intensities && intensities[i] !== undefined ? intensities[i] : 0.8;
        col.setRGB(val * 0.4, val * 0.9, 1.0);
      } else if (classes && classes[i] !== undefined) {
        col.setHex(CLASS_COLORS_HEX[classes[i]] || 0xffffff);
      }
      colors[i * 3] = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;
    }

    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const pMat = new THREE.PointsMaterial({
      size: this.viewMode === 'raw' ? 0.22 : 0.14,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
    });

    this.pointCloudObject = new THREE.Points(pGeo, pMat);
    this.scene.add(this.pointCloudObject);
  }

  // ==========================================================================
  // CAMERA VIEW SYSTEM (PHASE 21)
  // ==========================================================================
  setCameraView(mode) {
    this.cameraView = mode;
    if (!this.camera) return;

    if (mode === 'follow') {
      // Elevated 3/4 Tactical Chase View behind UGV
      this.camera.position.set(0, 7.5, -9.0);
      this.camera.lookAt(0, 1.2, 12.0);
      if (this.controls) {
        this.controls.enabled = false;
        this.controls.target.set(0, 1.2, 12.0);
      }
    } else if (mode === 'topdown') {
      // Tactical Top-Down Ortho-like Perspective
      this.camera.position.set(0, 48.0, 24.0);
      this.camera.lookAt(0, 0, 24.0);
      if (this.controls) {
        this.controls.enabled = false;
        this.controls.target.set(0, 0, 24.0);
      }
    } else if (mode === 'sensor') {
      // LiDAR Mast POV looking forward
      this.camera.position.set(0, 2.05, 0.45);
      this.camera.lookAt(0, 1.8, 30.0);
      if (this.controls) {
        this.controls.enabled = false;
      }
    } else if (mode === 'free') {
      // Free Orbit Controls
      if (this.controls) {
        this.controls.enabled = true;
      }
    }

    // Update camera buttons state
    document.querySelectorAll('.cam-btn').forEach((b) => {
      if (b.dataset.cam === mode) b.classList.add('active');
      else b.classList.remove('active');
    });
  }

  // ==========================================================================
  // RAYCASTING & CELL INSPECTOR (PHASE 11, 12)
  // ==========================================================================
  handlePointerMove(event) {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.cellsMeshGroup.children);

    if (intersects.length > 0) {
      const hit = intersects[0];
      const cellData = hit.object.userData.cellData;
      if (cellData) {
        this.hoveredCell = cellData;
        this.positionHighlightBox(hit.object);
        this.updateCellInspector(cellData);
      }
    }
  }

  positionHighlightBox(mesh) {
    if (!this.highlightBox || !mesh) return;
    this.highlightBox.visible = true;
    this.highlightBox.position.copy(mesh.position);
    this.highlightBox.scale.copy(mesh.scale);
  }

  updateCellInspector(cell) {
    const container = document.getElementById('cell-inspector-content');
    const badge = document.getElementById('inspector-status');
    const expDist = document.getElementById('exp-distance');
    const expBaseRes = document.getElementById('exp-base-res');
    const expSem = document.getElementById('exp-semantic');
    const expAction = document.getElementById('exp-action');

    const dist = Math.hypot(cell.cell_x, cell.cell_y);
    let ringName = 'Far (50–100m)';
    let baseRes = '0.50 m (50 cm)';
    if (dist < 10.0) { ringName = 'Near (0–10m)'; baseRes = '0.05 m (5 cm)'; }
    else if (dist < 25.0) { ringName = 'Mid-Near (10–25m)'; baseRes = '0.10 m (10 cm)'; }
    else if (dist < 50.0) { ringName = 'Mid (25–50m)'; baseRes = '0.25 m (25 cm)'; }

    if (expDist) expDist.textContent = ringName;
    if (expBaseRes) expBaseRes.textContent = baseRes;

    const className = CLASS_NAMES[cell.semantic_class] || 'UNKNOWN';
    if (expSem) expSem.textContent = `${className} (${(cell.confidence * 100).toFixed(0)}%)`;

    if (expAction) {
      if (cell.semantic_class === 3 || cell.semantic_class === 4) {
        expAction.textContent = 'VRU Priority Target -> Refine to 5cm';
        expAction.className = 'f-val highlight-rose';
      } else if (cell.semantic_class === 2) {
        expAction.textContent = 'Vehicle Obstacle -> Refine to 10cm';
        expAction.className = 'f-val highlight-amber';
      } else {
        expAction.textContent = 'Nominal Ring Density';
        expAction.className = 'f-val highlight-emerald';
      }
    }

    if (badge) badge.textContent = `RING: ${cell.resolution_level.toUpperCase()}`;

    if (container) {
      container.innerHTML = `
        <table class="inspector-table">
          <tr><td class="prop-name">World (X, Y):</td><td class="prop-val">${cell.cell_x.toFixed(2)}m, ${cell.cell_y.toFixed(2)}m</td></tr>
          <tr><td class="prop-name">Ego Distance:</td><td class="prop-val">${dist.toFixed(2)} m</td></tr>
          <tr><td class="prop-name">Resolution Ring:</td><td class="prop-val highlight-cyan">${cell.resolution_level} (${(RESOLUTION_BY_RING[cell.resolution_level]*100).toFixed(0)}cm)</td></tr>
          <tr><td class="prop-name">Surface Elevation Z:</td><td class="prop-val">${cell.elevation.toFixed(3)} m</td></tr>
          <tr><td class="prop-name">Z Range [Min, Max]:</td><td class="prop-val">[${cell.min_z.toFixed(2)}, ${cell.max_z.toFixed(2)}] m</td></tr>
          <tr><td class="prop-name">Height Step (Δz):</td><td class="prop-val">${(cell.max_z - cell.min_z).toFixed(2)} m</td></tr>
          <tr><td class="prop-name">Terrain Roughness:</td><td class="prop-val">${cell.roughness.toFixed(4)}</td></tr>
          <tr><td class="prop-name">Semantic Class:</td><td class="prop-val" style="color:${CLASS_COLORS_CSS[cell.semantic_class]}">${className}</td></tr>
          <tr><td class="prop-name">Confidence:</td><td class="prop-val">${(cell.confidence * 100).toFixed(1)}%</td></tr>
          <tr><td class="prop-name">Point Count:</td><td class="prop-val">${cell.point_count} pts</td></tr>
          <tr><td class="prop-name">Data Source:</td><td class="prop-val highlight-emerald">SYNTHETIC</td></tr>
        </table>
      `;
    }

    const readout = document.getElementById('hover-coord-readout');
    if (readout) {
      readout.textContent = `X: ${cell.cell_x.toFixed(2)}m | Y: ${cell.cell_y.toFixed(2)}m | Z: ${cell.elevation.toFixed(2)}m | Dist: ${dist.toFixed(2)}m`;
    }
  }

  // ==========================================================================
  // REAL-TIME FRAME LOOP & REST API (PHASE 13, 14, 15)
  // ==========================================================================
  bindUIEvents() {
    // Mode Switch Buttons
    document.querySelectorAll('.mode-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.mode-btn').forEach((b) => b.classList.remove('active'));
        const target = e.currentTarget;
        target.classList.add('active');
        this.viewMode = target.dataset.mode;
        if (this.currentFrame && this.currentFrame.cells) {
          this.updateComputationalCells(this.currentFrame.cells);
        }
      });
    });

    // Camera Switcher Buttons
    document.querySelectorAll('.cam-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        this.setCameraView(e.currentTarget.dataset.cam);
      });
    });

    // Physical World & Grid Toggles
    const togglePhysicalBtn = document.getElementById('btn-toggle-physical');
    if (togglePhysicalBtn) {
      togglePhysicalBtn.addEventListener('click', () => {
        this.showPhysicalWorld = !this.showPhysicalWorld;
        this.physicalGroup.visible = this.showPhysicalWorld;
        togglePhysicalBtn.textContent = `3D WORLD: ${this.showPhysicalWorld ? 'ON' : 'OFF'}`;
      });
    }

    const toggleGridBtn = document.getElementById('btn-toggle-grid');
    if (toggleGridBtn) {
      toggleGridBtn.addEventListener('click', () => {
        this.showGridWireframe = !this.showGridWireframe;
        this.computationalGroup.visible = this.showGridWireframe;
        toggleGridBtn.textContent = `GRID: ${this.showGridWireframe ? 'ON' : 'OFF'}`;
      });
    }

    const resetCamBtn = document.getElementById('btn-reset-view');
    if (resetCamBtn) {
      resetCamBtn.addEventListener('click', () => {
        this.setCameraView(this.cameraView);
      });
    }

    // Pointer Raycasting Events
    this.container.addEventListener('mousemove', (e) => this.handlePointerMove(e));

    // Playback Controls
    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');
    const btnStep = document.getElementById('btn-step');
    const btnReset = document.getElementById('btn-reset');

    if (btnPlay) btnPlay.addEventListener('click', () => this.sendControl('play'));
    if (btnPause) btnPause.addEventListener('click', () => this.sendControl('pause'));
    if (btnStep) btnStep.addEventListener('click', () => this.sendControl('step'));
    if (btnReset) btnReset.addEventListener('click', () => this.sendControl('reset'));

    // Scene Selector
    const sceneSelect = document.getElementById('scene-select');
    if (sceneSelect) {
      sceneSelect.addEventListener('change', (e) => {
        this.sendControl('set_scene', { scene_type: e.target.value });
      });
    }

    // Speed Slider
    const fpsSlider = document.getElementById('fps-slider');
    const fpsVal = document.getElementById('fps-slider-val');
    if (fpsSlider) {
      fpsSlider.addEventListener('input', (e) => {
        this.targetFps = parseInt(e.target.value, 10);
        if (fpsVal) fpsVal.textContent = this.targetFps;
        this.startPolling();
      });
    }
  }

  async sendControl(action, params = {}) {
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...params }),
      });
      if (action === 'step' || action === 'set_scene') {
        this.fetchFrame();
      }
    } catch (err) {
      console.warn('Control API request failed:', err);
    }
  }

  startPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    const intervalMs = Math.floor(1000 / this.targetFps);
    this.pollInterval = setInterval(() => this.fetchFrame(), intervalMs);
  }

  async fetchFrame() {
    try {
      const res = await fetch('/api/frame');
      if (!res.ok) return;
      const data = await res.json();
      this.currentFrame = data;

      this.updateTelemetryHUD(data.telemetry);
      this.updateHazardCounters(data.map_metadata?.hazards_summary);
      this.updateComputationalCells(data.cells);
      this.updatePointCloud(data.points, data.semantic_classes, data.intensity);
    } catch (err) {
      // Backend temporarily offline
    }
  }

  async fetchBenchmarkStats() {
    try {
      const res = await fetch('/api/benchmark');
      if (!res.ok) return;
      const data = await res.json();
      const compCells = document.getElementById('comp-fov-cells');
      const compMem = document.getElementById('comp-fov-mem');
      const savings = document.getElementById('savings-pct');
      if (compCells) compCells.textContent = `${(data.foveated_grid.total_cells / 1000).toFixed(0)}k`;
      if (compMem) compMem.textContent = `${data.foveated_grid.memory_mb.toFixed(1)}`;
      if (savings) savings.textContent = `${data.comparison.memory_savings_pct.toFixed(1)}% MEMORY REDUCTION (${data.comparison.cell_count_reduction_factor}x)`;
    } catch (err) {
      console.warn('Benchmark API call failed:', err);
    }
  }

  updateTelemetryHUD(t) {
    if (!t) return;
    const fps = document.getElementById('header-fps');
    const frame = document.getElementById('header-frame');
    const cells = document.getElementById('header-cells');
    const mem = document.getElementById('header-memory');
    const latency = document.getElementById('header-latency');
    const modeBadge = document.getElementById('pipeline-mode-badge');

    if (fps) fps.textContent = t.fps ? t.fps.toFixed(1) : '--';
    if (frame) frame.textContent = String(t.frame_count || 0).padStart(4, '0');
    if (cells) cells.textContent = t.counts ? t.counts.cells : 0;
    if (mem) mem.textContent = t.memory ? `${t.memory.ram_rss_mb} MB` : '-- MB';

    if (modeBadge && t.pipeline_mode) {
      modeBadge.textContent = t.pipeline_mode;
    }

    if (t.stage_latencies_ms) {
      const s = t.stage_latencies_ms;
      const prep = s.preprocessing?.last_ms || 0;
      const infer = s.inference?.last_ms || 0;
      const grid = s.grid_indexing?.last_ms || 0;
      const map = s.mapping?.last_ms || 0;
      const total = s.total?.last_ms || (prep + infer + grid + map);

      if (latency) latency.textContent = `${total.toFixed(1)} ms`;

      const setVal = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = `${v.toFixed(1)}ms`;
      };
      setVal('val-prep', prep);
      setVal('val-infer', infer);
      setVal('val-grid', grid);
      setVal('val-map', map);
      setVal('val-total', total);

      const maxScale = Math.max(10.0, total);
      const setBar = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.style.width = `${Math.min(100, (v / maxScale) * 100)}%`;
      };
      setBar('bar-prep', prep);
      setBar('bar-infer', infer);
      setBar('bar-grid', grid);
      setBar('bar-map', map);
    }
  }

  updateHazardCounters(hazards) {
    if (!hazards) return;
    const curbs = document.getElementById('count-curbs');
    const potholes = document.getElementById('count-potholes');
    const overhangs = document.getElementById('count-overhangs');
    const obstacles = document.getElementById('count-obstacles');
    if (curbs) curbs.textContent = hazards.curb || 0;
    if (potholes) potholes.textContent = hazards.pothole || 0;
    if (overhangs) overhangs.textContent = hazards.overhang || 0;
    if (obstacles) obstacles.textContent = hazards.obstacle || 0;
  }

  // ==========================================================================
  // ANIMATION & RENDER LOOP
  // ==========================================================================
  animate() {
    requestAnimationFrame(() => this.animate());

    const delta = this.clock.getDelta();

    // Rotate LiDAR Emitter unit
    if (this.lidarEmitter) {
      this.lidarEmitter.rotation.y += delta * 6.0; // ~60 RPM realistic spin
    }

    // Subtle UGV idling vibration
    if (this.ugvMesh) {
      this.ugvMesh.position.y = Math.sin(this.clock.getElapsedTime() * 8.0) * 0.008;
    }

    if (this.controls && this.cameraView === 'free') {
      this.controls.update();
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  // Fallback for environments where WebGL is unsupported
  init2DFallback() {
    if (this.canvas2D) {
      this.canvas2D.style.display = 'block';
      const ctx = this.canvas2D.getContext('2d');
      ctx.fillStyle = '#0a0d12';
      ctx.fillRect(0, 0, this.canvas2D.width, this.canvas2D.height);
      ctx.fillStyle = '#00f0ff';
      ctx.font = '14px monospace';
      ctx.fillText('2D FALLBACK PERCEPTION MODE ACTIVE', 20, 30);
    }
  }
}

// Initialize Application Engines on DOM Ready
window.addEventListener('DOMContentLoaded', () => {
  window.heroController = new HeroVideoController();
  window.perceptionEngine = new ThreePerceptionEngine();
});
