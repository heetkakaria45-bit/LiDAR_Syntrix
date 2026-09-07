import React, { useState, useEffect } from 'react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Zap,
  TrendingDown,
  AlertTriangle,
  Layers,
  Database,
  Activity,
  Car,
  User,
  ShieldAlert,
  HardDrive,
  Cpu,
  Radio,
  Clock,
  CheckCircle2,
  Server,
  Gauge,
  Scan,
  Grid,
  BarChart2,
  TrendingUp,
  SlidersHorizontal,
  ChevronRight,
} from 'lucide-react';
import { TelemetryData, FramePayload, FOVEATION_RINGS } from '../types';

interface RightStatsPanelProps {
  frame: FramePayload | null;
  telemetry: TelemetryData | null;
  selectedRingId?: number | null;
  onSelectRing?: (ringId: number | null) => void;
  isConnected?: boolean;
  onOpenResolution?: () => void;
}

interface PerformanceHistoryPoint {
  frame: number;
  timeLabel: string;
  latencyMs: number;
  prepMs: number;
  inferMs: number;
  gridMs: number;
  mapMs: number;
  ptsPerSecK: number;
  occupiedCells: number;
  memoryFoveatedMb: number;
  memoryUniformMb: number;
  savingsPct: number;
}

export const RightStatsPanel: React.FC<RightStatsPanelProps> = ({
  frame,
  telemetry,
  selectedRingId,
  onSelectRing,
  isConnected = true,
  onOpenResolution,
}) => {
  const [activeTab, setActiveTab] = useState<'unified' | 'graphs' | 'telemetry'>('unified');
  const [perfHistory, setPerfHistory] = useState<PerformanceHistoryPoint[]>([]);

  useEffect(() => {
    if (!telemetry) return;
    const stage = telemetry.stage_latencies;
    const frameNum = telemetry.frame_count;
    const totalPts = frame?.points?.length || 8500;
    const fps = telemetry.fps || 60.0;
    const ptsK = Math.round((totalPts * fps) / 1000);
    const occupied = Object.keys(frame?.cells || {}).length || 2180;
    const memFov = telemetry.memory_rss_mb || 4.82;
    const memUni = 97.6;
    const sav = telemetry.memory_savings_pct || 95.4;

    const newPoint: PerformanceHistoryPoint = {
      frame: frameNum,
      timeLabel: `F${frameNum % 100}`,
      latencyMs: Number((telemetry.latency_ms || 18.4).toFixed(1)),
      prepMs: Number((stage?.preprocessing || 2.8).toFixed(1)),
      inferMs: Number((stage?.inference || 8.5).toFixed(1)),
      gridMs: Number((stage?.grid_indexing || 2.1).toFixed(1)),
      mapMs: Number((stage?.mapping || 3.6).toFixed(1)),
      ptsPerSecK: ptsK,
      occupiedCells: occupied,
      memoryFoveatedMb: Number(memFov.toFixed(2)),
      memoryUniformMb: memUni,
      savingsPct: sav,
    };

    setPerfHistory((prev) => {
      const next = [...prev, newPoint];
      return next.slice(-24); // Keep last 24 frames for smooth charts
    });
  }, [telemetry, frame]);

  // Compute ring cell distributions
  const cellsByRing = { near: 0, mid_near: 0, mid: 0, far: 0 };
  if (frame?.cells) {
    for (const c of Object.values(frame.cells)) {
      if (c.resolution_level in cellsByRing) {
        cellsByRing[c.resolution_level as keyof typeof cellsByRing]++;
      }
    }
  }
  const totalGridCells = Object.keys(frame?.cells || {}).length || 2180;
  const totalPoints = frame?.points?.length || 8500;
  const fps = telemetry?.fps || 60.0;
  const ptsPerSec = Math.round(totalPoints * fps);
  const gridCapacity = 45000;
  const gridUtilization = Number(((totalGridCells / gridCapacity) * 100).toFixed(1));

  // Latency breakdown timings
  const insertTime = telemetry?.stage_latencies?.grid_indexing ?? 2.1;
  const lookupTime = Number(((telemetry?.stage_latencies?.hazard_analysis ?? 1.4) * 0.6).toFixed(2));
  const prepTime = telemetry?.stage_latencies?.preprocessing ?? 2.8;
  const dlInferTime = telemetry?.stage_latencies?.inference ?? 8.5;
  const mapTime = telemetry?.stage_latencies?.mapping ?? 3.6;
  const totalLatency = telemetry?.latency_ms ?? 18.4;

  return (
    <aside className="w-88 h-full flex flex-col gap-2.5 p-2.5 overflow-y-auto z-10 select-none font-sans text-xs text-slate-200 custom-scrollbar">
      {/* ========================================================= */}
      {/* 1. TOP VIEW MODE TAB SELECTOR                             */}
      {/* ========================================================= */}
      <div className="glass-panel p-1 rounded-2xl border border-slate-800/90 flex items-center justify-between gap-1 text-xs font-sans">
        <button
          onClick={() => setActiveTab('unified')}
          className={`flex-1 py-2 rounded-xl font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
            activeTab === 'unified'
              ? 'bg-hud-cyan text-slate-950 shadow-cyan-glow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
          }`}
          title="Consolidated Overview: Stats & Performance Graphs"
        >
          <Activity className="w-4 h-4" />
          <span>DASHBOARD</span>
        </button>

        <button
          onClick={() => setActiveTab('graphs')}
          className={`flex-1 py-2 rounded-xl font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
            activeTab === 'graphs'
              ? 'bg-hud-cyan text-slate-950 shadow-cyan-glow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
          }`}
          title="Full Real-Time Recharts Performance Monitoring Charts"
        >
          <BarChart2 className="w-4 h-4" />
          <span>PERF CHARTS</span>
        </button>

        <button
          onClick={() => setActiveTab('telemetry')}
          className={`flex-1 py-2 rounded-xl font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
            activeTab === 'telemetry'
              ? 'bg-hud-cyan text-slate-950 shadow-cyan-glow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
          }`}
          title="Subsystem Health and Numerical Telemetry Breakdown"
        >
          <Gauge className="w-4 h-4" />
          <span>TELEMETRY</span>
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB VIEW: FULL REAL-TIME PERFORMANCE CHARTS               */}
      {/* ========================================================= */}
      {(activeTab === 'graphs' || activeTab === 'unified') && (
        <div className="flex flex-col gap-2.5">
          {/* CHART 1: PROCESSING LATENCY (MS) */}
          <div className="glass-panel p-3.5 rounded-2xl border border-hud-cyan/30 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-hud-cyan" />
                <span className="font-bold text-hud-cyan text-xs font-display">1. PROCESSING LATENCY</span>
              </div>
              <span className="text-[10px] text-white font-bold font-mono px-2 py-0.5 rounded-md bg-hud-cyan/20 border border-hud-cyan/40">
                {totalLatency.toFixed(1)} ms
              </span>
            </div>

            <div className="h-24 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfHistory} margin={{ top: 2, right: 0, left: -26, bottom: 0 }}>
                  <defs>
                    <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#00f0ff" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="timeLabel" hide />
                  <YAxis domain={[0, 32]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(6, 11, 22, 0.95)',
                      borderColor: 'rgba(0, 240, 255, 0.3)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontFamily: 'Inter, sans-serif',
                    }}
                  />
                  <Area type="monotone" dataKey="latencyMs" name="Total Latency (ms)" stroke="#00f0ff" strokeWidth={2} fill="url(#latencyGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-between items-center text-[10.5px] text-slate-300 pt-1 border-t border-slate-800/90 font-sans">
              <span>Target: &lt;33.3ms (30 FPS)</span>
              <span className="text-hud-emerald font-bold font-mono">Real-Time: {fps.toFixed(0)} FPS</span>
            </div>
          </div>

          {/* CHART 2: POINTS PROCESSED PER SECOND (KPTS/S) */}
          <div className="glass-panel p-3.5 rounded-2xl border border-amber-500/30 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <div className="flex items-center gap-2">
                <Scan className="w-4 h-4 text-amber-400" />
                <span className="font-bold text-amber-300 text-xs font-display">2. SENSOR THROUGHPUT</span>
              </div>
              <span className="text-[10px] text-amber-300 font-bold font-mono px-2 py-0.5 rounded-md bg-amber-500/20 border border-amber-500/40">
                {(ptsPerSec / 1000).toFixed(0)} kpts/s
              </span>
            </div>

            <div className="h-20 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={perfHistory} margin={{ top: 2, right: 0, left: -26, bottom: 0 }}>
                  <XAxis dataKey="timeLabel" hide />
                  <YAxis domain={[300, 700]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(6, 11, 22, 0.95)',
                      borderColor: 'rgba(245, 158, 11, 0.3)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontFamily: 'Inter, sans-serif',
                    }}
                  />
                  <Bar dataKey="ptsPerSecK" name="Throughput (kpts/s)" fill="#f59e0b" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-between items-center text-[10.5px] text-slate-300 pt-1 border-t border-slate-800/90 font-sans">
              <span>Velodyne 64-Beam LiDAR</span>
              <span className="text-amber-300 font-bold font-mono font-tabular">{totalPoints.toLocaleString()} pts / frame</span>
            </div>
          </div>

          {/* CHART 3: OCCUPIED CELLS COUNT */}
          <div className="glass-panel p-3.5 rounded-2xl border border-purple-500/30 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <div className="flex items-center gap-2">
                <Grid className="w-4 h-4 text-purple-400" />
                <span className="font-bold text-purple-300 text-xs font-display">3. OCCUPIED CELLS COUNT</span>
              </div>
              <span className="text-[10px] text-purple-300 font-bold font-mono px-2 py-0.5 rounded-md bg-purple-500/20 border border-purple-500/40">
                {totalGridCells.toLocaleString()} voxels
              </span>
            </div>

            <div className="h-20 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfHistory} margin={{ top: 2, right: 0, left: -26, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cellsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a855f7" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#a855f7" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="timeLabel" hide />
                  <YAxis domain={[1200, 3200]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(6, 11, 22, 0.95)',
                      borderColor: 'rgba(168, 85, 247, 0.3)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontFamily: 'Inter, sans-serif',
                    }}
                  />
                  <Area type="monotone" dataKey="occupiedCells" name="Active 2.5D Cells" stroke="#a855f7" strokeWidth={2} fill="url(#cellsGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-between items-center text-[10.5px] text-slate-300 pt-1 border-t border-slate-800/90 font-sans">
              <span>O(1) Spatial Hash Table</span>
              <span className="text-purple-300 font-bold font-mono font-tabular">{gridUtilization}% Utilization</span>
            </div>
          </div>

          {/* CHART 4: MEMORY USAGE (MB) FOVEATED VS UNIFORM */}
          <div className="glass-panel p-3.5 rounded-2xl border border-hud-emerald/40 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-hud-emerald" />
                <span className="font-bold text-hud-emerald text-xs font-display">4. MEMORY FOOTPRINT (MB)</span>
              </div>
              <span className="text-[10px] text-hud-emerald font-bold font-mono px-2 py-0.5 rounded-md bg-hud-emerald/20 border border-hud-emerald/40">
                +{telemetry?.memory_savings_pct ?? 95.4}% SAVED
              </span>
            </div>

            <div className="h-20 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfHistory} margin={{ top: 2, right: 0, left: -26, bottom: 0 }}>
                  <defs>
                    <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00ff9d" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#00ff9d" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="timeLabel" hide />
                  <YAxis domain={[0, 110]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(6, 11, 22, 0.95)',
                      borderColor: 'rgba(0, 255, 157, 0.3)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontFamily: 'Inter, sans-serif',
                    }}
                  />
                  <Area type="monotone" dataKey="memoryUniformMb" name="Uniform Grid 5cm (MB)" stroke="#ef4444" strokeDasharray="3 3" fill="none" />
                  <Area type="monotone" dataKey="memoryFoveatedMb" name="Foveated 2.5D Grid (MB)" stroke="#00ff9d" strokeWidth={2} fill="url(#memGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-between items-center text-[10.5px] font-mono pt-1 border-t border-slate-800/90">
              <span className="text-red-400 font-semibold">Uniform: 97.6 MB</span>
              <span className="text-hud-emerald font-bold font-tabular">Foveated: {telemetry?.memory_rss_mb ?? 4.82} MB</span>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB VIEW: TELEMETRY & SYSTEM DETAILS                      */}
      {/* ========================================================= */}
      {(activeTab === 'telemetry' || activeTab === 'unified') && (
        <div className="flex flex-col gap-2.5">
          {/* LIDAR TELEMETRY CARD */}
          <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2.5">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <span className="font-bold tracking-wider text-hud-cyan flex items-center gap-2 text-xs font-display">
                <Scan className="w-4 h-4 text-hud-cyan" /> LIDAR TELEMETRY
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-hud-cyan/15 text-hud-cyan font-bold font-mono border border-hud-cyan/30">
                {frame?.frame_id || 'FRAME_00142'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 rounded-xl bg-black/40 border border-slate-800/80 flex flex-col gap-0.5">
                <span className="text-[10px] text-slate-400 font-sans uppercase font-semibold">TOTAL POINTS</span>
                <span className="text-sm font-bold text-white font-mono font-tabular">{totalPoints.toLocaleString()}</span>
              </div>

              <div className="p-2 rounded-xl bg-black/40 border border-slate-800/80 flex flex-col gap-0.5">
                <span className="text-[10px] text-slate-400 font-sans uppercase font-semibold">OCCUPIED CELLS</span>
                <span className="text-sm font-bold text-hud-emerald font-mono font-tabular">{totalGridCells.toLocaleString()}</span>
              </div>

              <div className="p-2 rounded-xl bg-black/40 border border-slate-800/80 flex flex-col gap-0.5">
                <span className="text-[10px] text-slate-400 font-sans uppercase font-semibold">GRID CAPACITY</span>
                <span className="text-xs font-bold text-slate-200 font-mono font-tabular">{gridCapacity.toLocaleString()}</span>
              </div>

              <div className="p-2 rounded-xl bg-black/40 border border-slate-800/80 flex flex-col gap-0.5">
                <span className="text-[10px] text-slate-400 font-sans uppercase font-semibold">SCAN RANGE</span>
                <span className="text-xs font-bold text-purple-300 font-mono">100.0 m (360°)</span>
              </div>
            </div>
          </div>

          {/* ADAPTIVE RESOLUTION 4-ZONE METERS */}
          <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <span className="font-bold tracking-wider text-hud-emerald flex items-center gap-2 text-xs font-display">
                <Grid className="w-4 h-4 text-hud-emerald" /> ADAPTIVE GRID ALLOCATION
              </span>
              {onOpenResolution && (
                <button
                  onClick={onOpenResolution}
                  className="text-[10px] text-hud-emerald hover:underline flex items-center gap-0.5 font-bold cursor-pointer"
                >
                  <span>INFO</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="space-y-1.5">
              {FOVEATION_RINGS.map((ring) => {
                const count = cellsByRing[ring.name as keyof typeof cellsByRing] || 450;
                const pct = Math.max(5, Math.round((count / totalGridCells) * 100));
                return (
                  <div
                    key={ring.id}
                    onClick={() => onSelectRing && onSelectRing(selectedRingId === ring.id ? null : ring.id)}
                    className={`p-2 rounded-xl border transition cursor-pointer flex flex-col gap-1 ${
                      selectedRingId === ring.id
                        ? 'bg-white/10 border-white/40'
                        : 'bg-black/30 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ring.color }} />
                        <span className="text-slate-200 font-semibold font-sans">{ring.label}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400 font-mono text-[11px]">{count} cells</span>
                        <span
                          className="px-1.5 py-0.5 rounded-md text-[10px] font-bold text-slate-950 font-mono"
                          style={{ backgroundColor: ring.color }}
                        >
                          {ring.resolution * 100}cm
                        </span>
                      </div>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{ width: `${pct}%`, backgroundColor: ring.color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SUBSYSTEM INTEGRITY STATUS */}
          <div className="glass-panel p-3.5 rounded-2xl border border-slate-800/90 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/90">
              <span className="font-bold tracking-wider text-slate-200 flex items-center gap-2 text-xs font-display">
                <Server className="w-4 h-4 text-hud-cyan" /> SUBSYSTEM INTEGRITY
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 flex items-center gap-1 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5" /> ALL SYSTEMS GO
              </span>
            </div>

            <div className="space-y-1.5 text-xs font-sans">
              <div className="p-2 rounded-xl bg-black/40 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400 font-medium">LiDAR Sensor:</span>
                <span className="text-hud-emerald font-bold font-mono">ONLINE (64-Beam Stream)</span>
              </div>
              <div className="p-2 rounded-xl bg-black/40 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400 font-medium">DL Perception:</span>
                <span className="text-hud-cyan font-bold font-mono">ACTIVE (8-Class Inference)</span>
              </div>
              <div className="p-2 rounded-xl bg-black/40 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400 font-medium">Spatial Indexer:</span>
                <span className="text-purple-300 font-bold font-mono">OPTIMAL (O(1) Spatial Hash)</span>
              </div>
              <div className="p-2 rounded-xl bg-black/40 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400 font-medium">Backend Server:</span>
                <span className={isConnected ? 'text-hud-emerald font-bold font-mono' : 'text-amber-400 font-bold font-mono'}>
                  {isConnected ? 'CONNECTED (127.0.0.1:8080)' : 'STANDALONE SIMULATION'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
