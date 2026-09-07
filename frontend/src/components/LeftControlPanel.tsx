import React from 'react';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Sliders,
  Layers,
  MapPin,
  Cpu,
  Eye,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Grid,
  Zap,
  Car,
  Gauge,
} from 'lucide-react';
import {
  ColorMode,
  ScenarioType,
  TelemetryData,
  FOVEATION_RINGS,
} from '../types';

interface LeftControlPanelProps {
  isPlaying: boolean;
  onTogglePlay: () => void;
  onStepFrame: () => void;
  onReset: () => void;
  playbackSpeed: number;
  onSpeedChange: (speed: number) => void;
  scenario: ScenarioType;
  onScenarioChange: (sc: ScenarioType) => void;
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
  telemetry: TelemetryData | null;
  onOpenResolution?: () => void;
  trafficDensity?: number;
  onTrafficDensityChange?: (density: number) => void;
  trafficSpeed?: number;
  onTrafficSpeedChange?: (speed: number) => void;
}

export const LeftControlPanel: React.FC<LeftControlPanelProps> = ({
  isPlaying,
  onTogglePlay,
  onStepFrame,
  onReset,
  playbackSpeed,
  onSpeedChange,
  scenario,
  onScenarioChange,
  colorMode,
  onColorModeChange,
  telemetry,
  onOpenResolution,
  trafficDensity = 5,
  onTrafficDensityChange,
  trafficSpeed = 1.0,
  onTrafficSpeedChange,
}) => {
  const colorModes: { id: ColorMode; label: string; desc: string; icon: string }[] = [
    { id: 'foveated', label: 'FOVEATED GRID', desc: 'Multi-Ring (5/10/25/50cm)', icon: '◎' },
    { id: 'anomaly_3d', label: 'ANOMALY 3D', desc: 'Topographic Surface & Anomaly Deflection', icon: '◬' },
    { id: 'terrain_3d', label: 'TERRAIN 3D', desc: '3D Scientific Elevation Mesh', icon: '▲' },
    { id: 'semantic', label: 'SEMANTIC 3D', desc: '8-Class DL Classification', icon: '▤' },
    { id: 'elevation', label: 'ELEVATION Z', desc: 'Heightmap Elevation Gradient', icon: '▲' },
    { id: 'traversability', label: 'TRAVERSABILITY', desc: 'Safe vs Impassable Terrain', icon: '◈' },
    { id: 'intensity', label: 'INTENSITY', desc: 'LiDAR Beam Reflectance', icon: '✹' },
  ];

  const scenarios: { id: ScenarioType; name: string; tag: string }[] = [
    { id: 'urban', name: 'Urban Intersection', tag: 'Cars, Peds, Curbs' },
    { id: 'hazard_course', name: 'Hazard Test Course', tag: 'Potholes, Curbs & Overhangs' },
    { id: 'highway', name: 'Highway Cruise', tag: 'High-speed Long Range' },
    { id: 'offroad', name: 'Off-Road Rough', tag: 'Undulating Slopes' },
    { id: 'pedestrian_cross', name: 'Crosswalk Zone', tag: 'Vulnerable Road Users' },
  ];

  return (
    <aside className="w-80 h-full flex flex-col gap-2.5 p-2.5 overflow-y-auto z-10 select-none font-sans text-xs text-slate-200 custom-scrollbar">
      {/* 1. PLAYBACK & SENSOR STREAMING CONTROLS */}
      <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-3">
        <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
          <span className="font-bold tracking-wider text-hud-cyan flex items-center gap-2 text-xs font-display">
            <Clock className="w-4 h-4 text-hud-cyan" /> SENSOR PLAYBACK
          </span>
          {/* Visible System State: ● LIVE / ● PAUSED */}
          <span
            className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold font-mono border flex items-center gap-1.5 ${
              isPlaying
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-emerald-glow-sm'
                : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span>{isPlaying ? '● LIVE' : '● PAUSED'}</span>
          </span>
        </div>

        {/* Action Buttons: START, PAUSE, RESET */}
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={onTogglePlay}
            className={`py-2 rounded-xl font-bold font-sans flex items-center justify-center gap-1.5 transition text-xs cursor-pointer ${
              isPlaying
                ? 'bg-amber-500 text-slate-950 hover:bg-amber-400 shadow-sm'
                : 'bg-hud-emerald text-slate-950 hover:bg-hud-emerald/90 shadow-emerald-glow-sm'
            }`}
            title={isPlaying ? 'Pause live scanning stream' : 'Start live scanning stream'}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isPlaying ? 'PAUSE' : 'START'}</span>
          </button>

          <button
            onClick={onStepFrame}
            className="py-2 rounded-xl font-semibold font-sans bg-black/40 border border-slate-700/80 text-slate-200 hover:text-hud-cyan hover:border-hud-cyan flex items-center justify-center gap-1 transition text-xs cursor-pointer"
            title="Step forward one frame"
          >
            <SkipForward className="w-3.5 h-3.5" />
            <span>STEP</span>
          </button>

          <button
            onClick={onReset}
            className="py-2 rounded-xl font-semibold font-sans bg-black/40 border border-slate-700/80 text-slate-200 hover:text-red-400 hover:border-red-500 flex items-center justify-center gap-1 transition text-xs cursor-pointer"
            title="Reset frame counter to 0"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET</span>
          </button>
        </div>

        {/* Playback Speed Selector */}
        <div className="flex items-center justify-between pt-1 border-t border-slate-800/90 text-xs font-sans">
          <span className="text-slate-300 font-semibold uppercase tracking-wider text-[10.5px]">SPEED:</span>
          <div className="flex gap-1.5">
            {[0.5, 1.0, 2.0, 5.0].map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                className={`px-2 py-0.5 rounded-lg font-mono text-xs font-bold transition cursor-pointer ${
                  playbackSpeed === s
                    ? 'bg-hud-cyan text-slate-950 shadow-cyan-glow-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 2. STREET TRAFFIC DENSITY CONTROL */}
      <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2.5">
        <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
          <span className="font-bold tracking-wider text-slate-200 flex items-center gap-2 text-xs font-display">
            <Car className="w-4 h-4 text-amber-400" /> TRAFFIC DENSITY
          </span>
          <span className="px-2 py-0.5 rounded-md text-[10.5px] font-bold font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm">
            {trafficDensity === 0 ? 'NO TRAFFIC' : `${trafficDensity} VEHICLES`}
          </span>
        </div>

        {/* Traffic Density Bar / Interactive Slider */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-[11px] text-slate-300 font-mono">
            <span className="text-slate-400">Active Fleet Density</span>
            <span className="text-white font-bold">{trafficDensity} / 10 Cars</span>
          </div>

          {/* Interactive Visual Bar */}
          <div className="relative w-full h-3.5 bg-black/60 rounded-full border border-slate-800 overflow-hidden flex items-center cursor-pointer shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 transition-all duration-150 rounded-full shadow-sm"
              style={{ width: `${(trafficDensity / 10) * 100}%` }}
            />
            <input
              type="range"
              min={0}
              max={10}
              step={1}
              value={trafficDensity}
              onChange={(e) => onTrafficDensityChange?.(Number(e.target.value))}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              title={`Traffic Density: ${trafficDensity} cars`}
            />
          </div>

          {/* Quick Density Presets */}
          <div className="grid grid-cols-5 gap-1 pt-1">
            {[
              { val: 0, label: 'OFF' },
              { val: 2, label: 'LOW' },
              { val: 5, label: 'MED' },
              { val: 8, label: 'HIGH' },
              { val: 10, label: 'MAX' },
            ].map((p) => (
              <button
                key={p.val}
                onClick={() => onTrafficDensityChange?.(p.val)}
                className={`py-1 rounded-lg text-[10px] font-mono font-bold transition cursor-pointer ${
                  trafficDensity === p.val
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'bg-black/40 border border-slate-800/80 text-slate-400 hover:text-white hover:border-slate-700'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-800/60">
            <span>Density: <span className="text-amber-300 font-semibold">{trafficDensity}/10 Active</span></span>
            <span>Flow: <span className="text-hud-cyan font-semibold">2-Way Lanes</span></span>
          </div>
        </div>
      </div>

      {/* 3. STREET TRAFFIC SPEED CONTROLLER */}
      <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2.5">
        <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
          <span className="font-bold tracking-wider text-slate-200 flex items-center gap-2 text-xs font-display">
            <Gauge className="w-4 h-4 text-hud-cyan" /> TRAFFIC SPEED
          </span>
          <span className="px-2 py-0.5 rounded-md text-[10.5px] font-bold font-mono bg-hud-cyan/20 text-hud-cyan border border-hud-cyan/40 shadow-sm">
            {trafficSpeed.toFixed(1)}x SPEED
          </span>
        </div>

        {/* Traffic Speed Bar / Interactive Slider */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-[11px] text-slate-300 font-mono">
            <span className="text-slate-400">Cruising Speed Scale</span>
            <span className="text-white font-bold">
              {trafficSpeed.toFixed(1)}x <span className="text-slate-400 font-normal">({(trafficSpeed * 7.2).toFixed(1)} m/s)</span>
            </span>
          </div>

          {/* Interactive Visual Bar */}
          <div className="relative w-full h-3.5 bg-black/60 rounded-full border border-slate-800 overflow-hidden flex items-center cursor-pointer shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-hud-cyan via-emerald-400 to-amber-400 transition-all duration-150 rounded-full shadow-sm"
              style={{ width: `${Math.max(0, Math.min(100, ((trafficSpeed - 0.5) / 2.0) * 100))}%` }}
            />
            <input
              type="range"
              min={0.5}
              max={2.5}
              step={0.1}
              value={trafficSpeed}
              onChange={(e) => onTrafficSpeedChange?.(Number(e.target.value))}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              title={`Traffic Speed: ${trafficSpeed.toFixed(1)}x`}
            />
          </div>

          {/* Quick Speed Presets */}
          <div className="grid grid-cols-5 gap-1 pt-1">
            {[
              { val: 0.5, label: '0.5x' },
              { val: 1.0, label: '1.0x' },
              { val: 1.5, label: '1.5x' },
              { val: 2.0, label: '2.0x' },
              { val: 2.5, label: '2.5x' },
            ].map((p) => (
              <button
                key={p.val}
                onClick={() => onTrafficSpeedChange?.(p.val)}
                className={`py-1 rounded-lg text-[10px] font-mono font-bold transition cursor-pointer ${
                  Math.abs(trafficSpeed - p.val) < 0.05
                    ? 'bg-hud-cyan text-slate-950 shadow-sm'
                    : 'bg-black/40 border border-slate-800/80 text-slate-400 hover:text-white hover:border-slate-700'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-800/60">
            <span>Velocity: <span className="text-hud-emerald font-semibold">{(trafficSpeed * 7.2 * 3.6).toFixed(1)} km/h</span></span>
            <span>Flow: <span className="text-hud-cyan font-semibold">Autonomous Random</span></span>
          </div>
        </div>
      </div>

      {/* 4. ADAPTIVE RESOLUTION MODAL SHORTCUT */}
      {onOpenResolution && (
        <button
          onClick={onOpenResolution}
          className="w-full p-3 rounded-2xl bg-gradient-to-r from-hud-emerald/15 to-hud-cyan/10 border border-hud-emerald/40 hover:border-hud-emerald transition flex items-center justify-between text-left group cursor-pointer shadow-sm"
        >
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-hud-emerald/20 text-hud-emerald border border-hud-emerald/30">
              <Grid className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs group-hover:text-hud-emerald transition font-display">
                Adaptive Resolution Hierarchy
              </div>
              <div className="text-[11px] text-slate-300 font-sans mt-0.5">4 Spatial Zones (5cm &rarr; 50cm)</div>
            </div>
          </div>
          <span className="text-[10px] text-hud-emerald font-bold font-mono px-2 py-0.5 rounded-md bg-hud-emerald/20 border border-hud-emerald/40">
            VIEW
          </span>
        </button>
      )}

      {/* 3. OPERATING SCENARIOS */}
      <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2.5">
        <span className="font-bold tracking-wider text-slate-200 flex items-center gap-2 text-xs font-display pb-1.5 border-b border-slate-800/90">
          <MapPin className="w-4 h-4 text-hud-cyan" /> SCENARIO DATASET
        </span>

        <div className="flex flex-col gap-1.5">
          {scenarios.map((sc) => (
            <button
              key={sc.id}
              onClick={() => onScenarioChange(sc.id)}
              className={`px-3 py-2 rounded-xl text-left transition flex items-center justify-between text-xs cursor-pointer ${
                scenario === sc.id
                  ? 'bg-hud-cyan/20 border border-hud-cyan/60 text-white shadow-cyan-glow-sm'
                  : 'bg-black/40 border border-slate-800/90 text-slate-300 hover:border-slate-700 hover:text-white'
              }`}
            >
              <div>
                <div className="font-bold text-xs text-white">{sc.name}</div>
                <div className="text-[10.5px] text-slate-400 font-sans mt-0.5">{sc.tag}</div>
              </div>
              {scenario === sc.id && <span className="w-2 h-2 rounded-full bg-hud-cyan shadow-cyan-glow-sm" />}
            </button>
          ))}
        </div>
      </div>

      {/* 4. POINT CLOUD & ELEVATION COLOR MODES */}
      <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2.5">
        <span className="font-bold tracking-wider text-slate-200 flex items-center gap-2 text-xs font-display pb-1.5 border-b border-slate-800/90">
          <Layers className="w-4 h-4 text-purple-400" /> COLOR MAPPING MODES
        </span>

        <div className="grid grid-cols-1 gap-1.5">
          {colorModes.map((cm) => (
            <button
              key={cm.id}
              onClick={() => onColorModeChange(cm.id)}
              className={`px-3 py-2 rounded-xl text-left transition flex items-center justify-between text-xs cursor-pointer ${
                colorMode === cm.id
                  ? 'bg-purple-500/20 border border-purple-500/60 text-white shadow-sm'
                  : 'bg-black/40 border border-slate-800/90 text-slate-300 hover:border-slate-700 hover:text-white'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="text-hud-cyan font-bold text-sm">{cm.icon}</span>
                <div>
                  <div className="font-bold text-xs text-white">{cm.label}</div>
                  <div className="text-[10.5px] text-slate-400 font-sans mt-0.5">{cm.desc}</div>
                </div>
              </div>
              {colorMode === cm.id && <span className="w-2 h-2 rounded-full bg-purple-400 shadow-sm" />}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
};
