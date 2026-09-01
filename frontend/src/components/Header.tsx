import React from 'react';
import {
  Activity,
  Cpu,
  Zap,
  BarChart3,
  Video,
  Layers,
  ShieldCheck,
  Maximize,
  Minimize,
  Sliders,
  HardDrive,
  Radio,
  Grid,
  ArrowLeft,
  Home,
} from 'lucide-react';
import { TelemetryData, VideoBgMode } from '../types';

interface HeaderProps {
  telemetry: TelemetryData | null;
  videoMode: VideoBgMode;
  onVideoModeChange: (mode: VideoBgMode) => void;
  videoOpacity: number;
  onVideoOpacityChange: (opacity: number) => void;
  onOpenArchitecture: () => void;
  onOpenBenchmark: () => void;
  onOpenResolution?: () => void;
  onNavigateHome?: () => void;
  isConnected: boolean;
  isPlaying?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  telemetry,
  videoMode,
  onVideoModeChange,
  videoOpacity,
  onVideoOpacityChange,
  onOpenArchitecture,
  onOpenBenchmark,
  onOpenResolution,
  onNavigateHome,
  isConnected,
  isPlaying = true,
}) => {
  const [isFullscreen, setIsFullscreen] = React.useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true));
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false));
    }
  };

  return (
    <header className="w-full px-5 py-2 glass-panel border-b border-hud-border flex items-center justify-between z-30 relative select-none">
      {/* BRANDING & PROJECT TITLE */}
      <div className="flex items-center gap-3">
        {onNavigateHome && (
          <button
            onClick={onNavigateHome}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700/80 text-slate-300 hover:text-hud-cyan hover:border-hud-cyan/60 transition flex items-center gap-1.5 text-xs font-mono font-bold shadow-sm cursor-pointer"
            title="Return to Home Landing Page"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-hud-cyan" />
            <span className="hidden sm:inline">HOME</span>
          </button>
        )}

        <div className="relative flex items-center justify-center">
          <div className="w-8 h-8 rounded-lg bg-hud-cyan/15 border border-hud-cyan/40 flex items-center justify-center text-hud-cyan font-bold shadow-cyan-glow-sm">
            <Radio className="w-4 h-4 animate-pulse text-hud-cyan" />
          </div>
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-hud-emerald animate-ping" />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold font-display tracking-wide text-white leading-none">
              FOVEATED SEMANTIC LiDAR
            </h1>
            <span className="px-1.5 py-0.5 text-[9.5px] font-mono font-extrabold bg-hud-cyan/15 text-hud-cyan border border-hud-cyan/40 rounded tracking-wider">
              2.5D MAPPING
            </span>
          </div>
          <p className="text-[10.5px] font-mono text-slate-400 leading-none mt-1">
            Smart India Hackathon 2026 • Defence Autonomous Perception
          </p>
        </div>
      </div>

      {/* QUICK SYSTEM METRICS TICKER */}
      <div className="hidden md:flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-900/70 border border-slate-800">
          <Activity className="w-3.5 h-3.5 text-hud-cyan animate-pulse" />
          <span className="text-slate-400">FPS:</span>
          <span className="text-hud-cyan font-bold">{telemetry?.fps || 60.0}</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-900/70 border border-slate-800">
          <Zap className="w-3.5 h-3.5 text-hud-emerald" />
          <span className="text-slate-400">LATENCY:</span>
          <span className="text-hud-emerald font-bold">
            {telemetry?.latency_ms ? `${telemetry.latency_ms.toFixed(1)}ms` : '17.8ms'}
          </span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-900/70 border border-slate-800">
          <span className="text-slate-400">MEM SAVINGS:</span>
          <span className="text-hud-emerald font-bold">
            {telemetry?.memory_savings_pct ? `+${telemetry.memory_savings_pct}%` : '+95.4%'}
          </span>
        </div>
      </div>

      {/* RIGHT ACTION BUTTONS */}
      <div className="flex items-center gap-2 text-xs font-mono">
        {onOpenResolution && (
          <button
            onClick={onOpenResolution}
            className="px-3 py-1.5 rounded-lg glass-card border border-hud-emerald/40 text-hud-emerald hover:bg-hud-emerald/20 transition flex items-center gap-1.5 font-bold cursor-pointer"
          >
            <Grid className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">4 ZONES</span>
          </button>
        )}

        <button
          onClick={onOpenBenchmark}
          className="px-3 py-1.5 rounded-lg glass-card border border-purple-500/40 text-purple-300 hover:bg-purple-500/20 transition flex items-center gap-1.5 font-bold cursor-pointer"
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">BENCHMARK</span>
        </button>

        <button
          onClick={onOpenArchitecture}
          className="px-3 py-1.5 rounded-lg glass-card border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/20 transition flex items-center gap-1.5 font-bold cursor-pointer"
        >
          <Cpu className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">ARCHITECTURE</span>
        </button>

        <button
          onClick={toggleFullscreen}
          className="p-1.5 rounded-lg glass-card text-slate-300 hover:text-white transition cursor-pointer"
          title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen View'}
        >
          {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
};
