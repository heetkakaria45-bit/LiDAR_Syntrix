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
    <aside className="w-80 h-full flex flex-col gap-2.5 p-2.5 overflow-y-auto z-10 select-none font-mono text-xs text-slate-300 custom-scrollbar">
      {/* 1. PLAYBACK & SENSOR STREAMING CONTROLS */}
      <div className="glass-panel p-3 rounded-xl border border-slate-800 flex flex-col gap-2.5">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800">
          <span className="font-bold tracking-wider text-hud-cyan flex items-center gap-1.5 text-xs">
            <Clock className="w-3.5 h-3.5 text-hud-cyan" /> SENSOR PLAYBACK
          </span>
          {/* Visible System State: ● LIVE / ● PAUSED */}
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1.5 ${
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
        <div className="grid grid-cols-3 gap-1.5">
          <button
            onClick={onTogglePlay}
            className={`py-2 rounded-lg font-bold flex items-center justify-center gap-1.5 transition text-xs ${
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
            className="py-2 rounded-lg font-semibold bg-black/40 border border-slate-700/80 text-slate-200 hover:text-hud-cyan hover:border-hud-cyan flex items-center justify-center gap-1 transition text-xs"
            title="Step forward one frame"
          >
            <SkipForward className="w-3.5 h-3.5" />
            <span>STEP</span>
          </button>

          <button
            onClick={onReset}
            className="py-2 rounded-lg font-semibold bg-black/40 border border-slate-700/80 text-slate-200 hover:text-red-400 hover:border-red-500 flex items-center justify-center gap-1 transition text-xs"
            title="Reset frame counter to 0"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET</span>
          </button>
        </div>

        {/* Playback Speed Selector */}
        <div className="flex items-center justify-between pt-1 border-t border-slate-800 text-[11px]">
          <span className="text-slate-400">SPEED:</span>
          <div className="flex gap-1">
            {[0.5, 1.0, 2.0, 5.0].map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                className={`px-2 py-0.5 rounded transition ${
                  playbackSpeed === s
                    ? 'bg-hud-cyan text-slate-950 font-bold shadow-cyan-glow-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 2. ADAPTIVE RESOLUTION MODAL SHORTCUT */}
      {onOpenResolution && (
        <button
          onClick={onOpenResolution}
          className="w-full p-2.5 rounded-xl bg-gradient-to-r from-hud-emerald/15 to-hud-cyan/10 border border-hud-emerald/40 hover:border-hud-emerald transition flex items-center justify-between text-left group"
        >
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-hud-emerald/20 text-hud-emerald">
              <Grid className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs group-hover:text-hud-emerald transition">
                Adaptive Resolution Hierarchy
              </div>
              <div className="text-[10px] text-slate-400">4 Spatial Zones (5cm $\rightarrow$ 50cm)</div>
            </div>
          </div>
          <span className="text-[10px] text-hud-emerald font-bold px-1.5 py-0.5 rounded bg-hud-emerald/20 border border-hud-emerald/30">
            VIEW
          </span>
        </button>
      )}

      {/* 3. OPERATING SCENARIOS */}
      <div className="glass-panel p-3 rounded-xl border border-slate-800 flex flex-col gap-2">
        <span className="font-bold tracking-wider text-slate-200 flex items-center gap-1.5 text-xs pb-1 border-b border-slate-800">
          <MapPin className="w-3.5 h-3.5 text-hud-cyan" /> SCENARIO DATASET
        </span>

        <div className="flex flex-col gap-1.5">
          {scenarios.map((sc) => (
            <button
              key={sc.id}
              onClick={() => onScenarioChange(sc.id)}
              className={`px-2.5 py-1.5 rounded-lg text-left transition flex items-center justify-between text-xs ${
                scenario === sc.id
                  ? 'bg-hud-cyan/15 border border-hud-cyan/50 text-white shadow-cyan-glow-sm'
                  : 'bg-black/30 border border-slate-800/80 text-slate-300 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="font-semibold text-[11px]">{sc.name}</div>
                <div className="text-[9px] text-slate-500">{sc.tag}</div>
              </div>
              {scenario === sc.id && <span className="w-1.5 h-1.5 rounded-full bg-hud-cyan" />}
            </button>
          ))}
        </div>
      </div>

      {/* 4. POINT CLOUD & ELEVATION COLOR MODES */}
      <div className="glass-panel p-3 rounded-xl border border-slate-800 flex flex-col gap-2">
        <span className="font-bold tracking-wider text-slate-200 flex items-center gap-1.5 text-xs pb-1 border-b border-slate-800">
          <Layers className="w-3.5 h-3.5 text-purple-400" /> COLOR MAPPING MODES
        </span>

        <div className="grid grid-cols-1 gap-1.5">
          {colorModes.map((cm) => (
            <button
              key={cm.id}
              onClick={() => onColorModeChange(cm.id)}
              className={`px-2.5 py-1.5 rounded-lg text-left transition flex items-center justify-between text-xs ${
                colorMode === cm.id
                  ? 'bg-purple-500/20 border border-purple-500/50 text-white shadow-sm'
                  : 'bg-black/30 border border-slate-800/80 text-slate-300 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-hud-cyan font-bold">{cm.icon}</span>
                <div>
                  <div className="font-semibold text-[11px]">{cm.label}</div>
                  <div className="text-[9px] text-slate-500">{cm.desc}</div>
                </div>
              </div>
              {colorMode === cm.id && <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
};
