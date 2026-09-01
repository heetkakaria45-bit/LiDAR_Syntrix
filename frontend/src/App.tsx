import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { BackgroundVideo } from './components/BackgroundVideo';
import { HomePage } from './components/HomePage';
import { LidarViewport } from './components/viewport/LidarViewport';
import { LeftControlPanel } from './components/LeftControlPanel';
import { RightStatsPanel } from './components/RightStatsPanel';
import { BottomSection } from './components/BottomSection';
import { TeleopConsole, TeleopState } from './components/teleop/TeleopConsole';
import { ArchitectureModal } from './components/modals/ArchitectureModal';
import { BenchmarkModal } from './components/modals/BenchmarkModal';
import { ResolutionModal } from './components/modals/ResolutionModal';
import { apiService } from './services/api';
import {
  FramePayload,
  ColorMode,
  ScenarioType,
  VideoBgMode,
  GridCellData,
} from './types';
import {
  ArrowDown,
  ArrowUp,
  Zap,
  Sparkles,
  Car,
  Sliders,
  BarChart3,
  X,
  Play,
  Pause,
} from 'lucide-react';

export const App: React.FC = () => {
  // Vehicle Driving State — Initially Still (0 km/h)
  const initialTeleop: TeleopState = {
    speed: 0.0,
    speedKmh: 0.0,
    targetSpeedKmh: 0,
    steerAngle: 0,
    mode: 'manual',
    distanceTraveled: 0,
    throttlePct: 0,
    brakePct: 0,
    eStop: false,
  };

  const teleopRef = useRef<TeleopState>(initialTeleop);
  const [teleop, setTeleopState] = useState<TeleopState>(initialTeleop);

  const updateTeleop = useCallback((updater: (prev: TeleopState) => TeleopState) => {
    setTeleopState((prev) => {
      const next = updater(prev);
      teleopRef.current = next;
      return next;
    });
  }, []);

  // Simulation & Pipeline State
  const [frame, setFrame] = useState<FramePayload | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [scenario, setScenario] = useState<ScenarioType>('urban');
  const [colorMode, setColorMode] = useState<ColorMode>('foveated');
  const [selectedRingId, setSelectedRingId] = useState<number | null>(null);
  const [visibleClasses, setVisibleClasses] = useState<Set<number>>(
    new Set([0, 1, 2, 3, 4, 5, 6, 7])
  );
  const [videoMode, setVideoMode] = useState<VideoBgMode>('ambient');
  const [videoOpacity, setVideoOpacity] = useState<number>(0.85);
  const [isArchitectureOpen, setIsArchitectureOpen] = useState<boolean>(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState<boolean>(false);
  const [isResolutionOpen, setIsResolutionOpen] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(1);
  const [totalFrames, setTotalFrames] = useState<number>(500);

  // Drawer Toggles for Uncluttered Professional Viewport
  const [showLeftDrawer, setShowLeftDrawer] = useState<boolean>(false);
  const [showRightDrawer, setShowRightDrawer] = useState<boolean>(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const simulationSectionRef = useRef<HTMLDivElement>(null);

  // Check connection status periodically
  useEffect(() => {
    apiService.checkConnection().then(setIsConnected);
    const interval = setInterval(() => {
      apiService.checkConnection().then(setIsConnected);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch frame on tick with dynamic teleop state
  const fetchNextFrame = useCallback(async () => {
    const curTeleop = teleopRef.current;
    const nextFrame = await apiService.fetchFrame(curTeleop);
    setFrame(nextFrame);
    setCurrentFrameIndex(nextFrame.telemetry.frame_count);
  }, []);

  // Physics Simulation Step — Only moves when throttle is active
  useEffect(() => {
    const physicsInterval = setInterval(() => {
      const cur = teleopRef.current;
      const dt = 0.05 * playbackSpeed;
      let newSpeed = cur.speed;

      if (cur.eStop || cur.brakePct > 50) {
        newSpeed = Math.max(0, newSpeed - 12.0 * dt);
      } else if (cur.throttlePct > 0) {
        const target = (cur.targetSpeedKmh || 35) / 3.6;
        if (newSpeed < target) newSpeed = Math.min(target, newSpeed + 4.5 * dt);
        else if (newSpeed > target) newSpeed = Math.max(target, newSpeed - 3.0 * dt);
      } else {
        // When not operated by WASD/controls, quickly decelerate to complete standstill
        newSpeed = Math.max(0, newSpeed - 8.0 * dt);
      }

      const dist = cur.distanceTraveled + Math.abs(newSpeed * dt);
      const updated: TeleopState = {
        ...cur,
        speed: newSpeed,
        speedKmh: Math.abs(newSpeed * 3.6),
        distanceTraveled: dist,
      };

      teleopRef.current = updated;
      setTeleopState(updated);
    }, 50);

    return () => clearInterval(physicsInterval);
  }, [playbackSpeed]);

  // Frame Ingestion Playback Loop
  useEffect(() => {
    fetchNextFrame();

    let timer: NodeJS.Timeout | null = null;
    if (isPlaying) {
      const intervalMs = Math.max(30, 100 / playbackSpeed);
      timer = setInterval(() => {
        fetchNextFrame();
      }, intervalMs);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, playbackSpeed, fetchNextFrame]);

  // Launch & Smooth Scroll Handler
  const handleLaunchSimulator = () => {
    setIsPlaying(true);
    updateTeleop((prev) => ({
      ...prev,
      mode: 'manual',
      targetSpeedKmh: 35,
      throttlePct: 80,
      eStop: false,
    }));
    simulationSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToTop = () => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Controls Handlers
  const handleTogglePlay = () => {
    const nextPlay = !isPlaying;
    setIsPlaying(nextPlay);
    apiService.sendControl(nextPlay ? 'play' : 'pause');
  };

  const handleStepFrame = () => {
    setIsPlaying(false);
    fetchNextFrame();
    apiService.sendControl('step');
  };

  const handleReset = () => {
    apiService.sendControl('reset', scenario);
    updateTeleop((prev) => ({
      ...prev,
      speed: 0,
      speedKmh: 0,
      targetSpeedKmh: 0,
      distanceTraveled: 0,
      steerAngle: 0,
      throttlePct: 0,
      brakePct: 0,
      eStop: false,
    }));
    fetchNextFrame();
  };

  const handleScenarioChange = (sc: ScenarioType) => {
    setScenario(sc);
    apiService.sendControl('set_scene', sc);
    fetchNextFrame();
  };

  const handleToggleClass = (classId: number) => {
    setVisibleClasses((prev) => {
      const next = new Set(prev);
      if (next.has(classId)) {
        next.delete(classId);
      } else {
        next.add(classId);
      }
      return next;
    });
  };

  return (
    <div
      ref={scrollContainerRef}
      className="relative w-screen h-screen overflow-y-auto overflow-x-hidden bg-[#0a0e14] text-slate-100 select-none font-sans scroll-smooth custom-scrollbar"
    >
      {/* 1. PERSISTENT BRIGHT VIDEO BACKGROUND */}
      <BackgroundVideo
        mode={videoMode}
        onModeChange={setVideoMode}
        opacity={videoOpacity}
        onOpacityChange={setVideoOpacity}
      />

      {/* 2. TOP TACTICAL NAVIGATION HEADER */}
      <Header
        telemetry={frame?.telemetry || null}
        videoMode={videoMode}
        onVideoModeChange={setVideoMode}
        videoOpacity={videoOpacity}
        onVideoOpacityChange={setVideoOpacity}
        onOpenArchitecture={() => setIsArchitectureOpen(true)}
        onOpenBenchmark={() => setIsBenchmarkOpen(true)}
        onOpenResolution={() => setIsResolutionOpen(true)}
        onNavigateHome={scrollToTop}
        isConnected={isConnected}
        isPlaying={isPlaying}
      />

      {/* 3. HERO & PROJECT OVERVIEW SECTION */}
      <HomePage
        onScrollToSimulator={handleLaunchSimulator}
        onOpenArchitecture={() => setIsArchitectureOpen(true)}
        onOpenBenchmark={() => setIsBenchmarkOpen(true)}
        onOpenResolution={() => setIsResolutionOpen(true)}
        telemetry={frame?.telemetry || null}
        isConnected={isConnected}
      />

      {/* 4. SCROLL DIVIDER & SECTION ANCHOR */}
      <div
        ref={simulationSectionRef}
        className="relative z-10 w-full px-6 py-3 border-t border-b border-hud-border/70 bg-slate-950/85 backdrop-blur-md flex flex-wrap items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="w-2.5 h-2.5 rounded-full bg-hud-cyan animate-ping" />
          <span className="text-white font-bold tracking-wide font-display text-sm">
            2.5D LIDAR SIMULATION &amp; FOVEATED SPATIAL MAPPING
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-hud-emerald font-semibold">Continuous Dynamic World</span>
        </div>

        {/* Viewport Floating Drawer Toggles for Uncluttered Experience */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={() => setShowLeftDrawer(!showLeftDrawer)}
            className={`px-3 py-1.5 rounded-lg border transition flex items-center gap-1.5 ${
              showLeftDrawer
                ? 'bg-hud-cyan text-slate-950 border-hud-cyan font-bold shadow-cyan-glow-sm'
                : 'glass-card text-slate-300 hover:text-white'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>CONTROLS &amp; SCENES</span>
          </button>

          <button
            onClick={() => setShowRightDrawer(!showRightDrawer)}
            className={`px-3 py-1.5 rounded-lg border transition flex items-center gap-1.5 ${
              showRightDrawer
                ? 'bg-hud-emerald text-slate-950 border-hud-emerald font-bold shadow-emerald-glow-sm'
                : 'glass-card text-slate-300 hover:text-white'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>PERF CHARTS</span>
          </button>

          <button
            onClick={scrollToTop}
            className="px-3 py-1.5 rounded-lg glass-card text-slate-400 hover:text-hud-cyan transition flex items-center gap-1"
          >
            <ArrowUp className="w-3.5 h-3.5" />
            <span>TOP</span>
          </button>
        </div>
      </div>

      {/* 5. HERO 3D SIMULATION VIEWPORT (UNCLUTTERED, FULL-WIDTH) */}
      <section className="relative z-10 w-full h-[calc(100vh-65px)] min-h-[660px] p-3 flex flex-col gap-2">
        <div className="relative flex-1 w-full h-full rounded-2xl overflow-hidden shadow-2xl border border-hud-border/70">
          {/* Main 3D/2.5D LiDAR Viewport Centerpiece */}
          <LidarViewport
            frame={frame}
            colorMode={colorMode}
            onColorModeChange={setColorMode}
            selectedRingId={selectedRingId}
            onSelectRing={setSelectedRingId}
            visibleClasses={visibleClasses}
            onOpenResolution={() => setIsResolutionOpen(true)}
            teleop={teleop}
          />

          {/* Floating Compact Teleoperation Cockpit */}
          <TeleopConsole
            teleop={teleop}
            onUpdateTeleop={updateTeleop}
            onResetVehicle={handleReset}
          />

          {/* Collapsible Slide-Over Left Control Drawer */}
          {showLeftDrawer && (
            <div className="absolute top-16 right-4 bottom-16 z-30 w-72 animate-in slide-in-from-right-10 duration-200">
              <div className="relative w-full h-full glass-panel p-3 rounded-2xl border border-hud-cyan/40 shadow-2xl overflow-y-auto custom-scrollbar flex flex-col gap-2">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                    <Sliders className="w-4 h-4 text-hud-cyan" />
                    <span>SIMULATION CONTROLS</span>
                  </div>
                  <button
                    onClick={() => setShowLeftDrawer(false)}
                    className="p-1 rounded text-slate-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <LeftControlPanel
                  isPlaying={isPlaying}
                  onTogglePlay={handleTogglePlay}
                  onStepFrame={handleStepFrame}
                  onReset={handleReset}
                  playbackSpeed={playbackSpeed}
                  onSpeedChange={setPlaybackSpeed}
                  scenario={scenario}
                  onScenarioChange={handleScenarioChange}
                  colorMode={colorMode}
                  onColorModeChange={setColorMode}
                  telemetry={frame?.telemetry || null}
                  onOpenResolution={() => setIsResolutionOpen(true)}
                />
              </div>
            </div>
          )}

          {/* Collapsible Slide-Over Right Stats & Recharts Drawer */}
          {showRightDrawer && (
            <div className="absolute top-16 right-4 bottom-16 z-30 w-80 animate-in slide-in-from-right-10 duration-200">
              <div className="relative w-full h-full glass-panel p-3 rounded-2xl border border-hud-emerald/40 shadow-2xl overflow-y-auto custom-scrollbar flex flex-col gap-2">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                    <BarChart3 className="w-4 h-4 text-hud-emerald" />
                    <span>PERFORMANCE METRICS</span>
                  </div>
                  <button
                    onClick={() => setShowRightDrawer(false)}
                    className="p-1 rounded text-slate-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <RightStatsPanel
                  frame={frame}
                  telemetry={frame?.telemetry || null}
                  selectedRingId={selectedRingId}
                  onSelectRing={setSelectedRingId}
                  isConnected={isConnected}
                  onOpenResolution={() => setIsResolutionOpen(true)}
                />
              </div>
            </div>
          )}
        </div>

        {/* Bottom Scrubber Section */}
        <BottomSection
          frame={frame}
          currentFrameIndex={currentFrameIndex}
          totalFrames={totalFrames}
          onScrubFrame={(idx) => {
            setCurrentFrameIndex(idx);
            fetchNextFrame();
          }}
          visibleClasses={visibleClasses}
          onToggleClass={handleToggleClass}
        />
      </section>

      {/* 6. MODAL OVERLAYS */}
      <ArchitectureModal
        isOpen={isArchitectureOpen}
        onClose={() => setIsArchitectureOpen(false)}
      />

      <BenchmarkModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
      />

      <ResolutionModal
        isOpen={isResolutionOpen}
        onClose={() => setIsResolutionOpen(false)}
        onSelectRing={setSelectedRingId}
      />
    </div>
  );
};
