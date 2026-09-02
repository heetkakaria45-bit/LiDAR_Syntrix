import React from 'react';
import {
  X,
  Grid,
  Zap,
  TrendingDown,
  ArrowRight,
  TrendingUp,
  Layers,
  Database,
  CheckCircle2,
  Cpu,
  Radio,
  Gauge,
  Info,
} from 'lucide-react';
import { FOVEATION_RINGS } from '../../types';

interface ResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectRing?: (ringId: number) => void;
}

export const ResolutionModal: React.FC<ResolutionModalProps> = ({
  isOpen,
  onClose,
  onSelectRing,
}) => {
  if (!isOpen) return null;

  const zones = [
    {
      zoneNumber: 1,
      name: 'NEAR HAZARD ZONE',
      range: '0 – 10 meters',
      resolution: '5 cm (0.05m)',
      color: '#00ff9d',
      cellArea: '0.0025 m²',
      cellCountEst: '12,560 cells',
      purpose: 'Millimeter/centimeter safety envelope for detecting curbs (+16cm), potholes (-14cm), road surface roughness, and immediate collision avoidance.',
      priority: 'CRITICAL (Highest Precision)',
    },
    {
      zoneNumber: 2,
      name: 'TACTICAL MANEUVER ZONE',
      range: '10 – 25 meters',
      resolution: '10 cm (0.10m)',
      color: '#00f0ff',
      cellArea: '0.0100 m²',
      cellCountEst: '16,490 cells',
      purpose: 'Tactical planning corridor for vehicle trajectory tracking, pedestrian crosswalk detection, and cyclist velocity vector calculation.',
      priority: 'HIGH (Trajectory Planning)',
    },
    {
      zoneNumber: 3,
      name: 'MID-RANGE ROAD ZONE',
      range: '25 – 50 meters',
      resolution: '25 cm (0.25m)',
      color: '#8b5cf6',
      cellArea: '0.0625 m²',
      cellCountEst: '9,420 cells',
      purpose: 'Intermediate perception zone for lane geometry, traffic flow monitoring, and oncoming vehicle detection across road boundaries.',
      priority: 'MEDIUM (Situational Awareness)',
    },
    {
      zoneNumber: 4,
      name: 'FAR HORIZON ZONE',
      range: '50 – 100 meters',
      resolution: '50 cm (0.50m)',
      color: '#ec4899',
      cellArea: '0.2500 m²',
      cellCountEst: '4,710 cells',
      priority: 'COARSE (Macro Free Space)',
      purpose: 'Coarse long-range horizon zone for structural clearance, macro obstacles, terrain slope changes, and distant boundary tracking.',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200 select-none">
      <div className="w-full max-w-4xl max-h-[92vh] glass-panel rounded-2xl border border-hud-emerald/50 shadow-emerald-glow flex flex-col overflow-hidden">
        {/* HEADER */}
        <div className="px-6 py-4 border-b border-hud-border flex items-center justify-between bg-slate-950/90">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-hud-emerald/15 text-hud-emerald border border-hud-emerald/40 shadow-emerald-glow-sm">
              <Grid className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold font-display text-white">
                  Adaptive Foveated Spatial Resolution Architecture
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-hud-emerald/20 text-hud-emerald border border-hud-emerald/40">
                  DEFENCE
                </span>
              </div>
              <p className="text-xs font-mono text-slate-400">
                Variable-Resolution Multi-Ring 2.5D LiDAR Grid Mapping
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* BODY */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono text-slate-300">
          {/* Core Concept Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-hud-emerald/10 via-slate-900 to-hud-cyan/10 border border-hud-emerald/30 relative">
            <div className="text-hud-emerald font-bold text-xs mb-1.5 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-hud-emerald" /> CORE ARCHITECTURAL PRINCIPLE
            </div>
            <blockquote className="text-sm font-sans font-medium text-slate-100 italic leading-relaxed border-l-2 border-hud-emerald pl-3 my-1.5">
              &ldquo;The system allocates higher spatial resolution near the vehicle where precision is critical, while progressively reducing resolution at greater distances to reduce memory and computational requirements.&rdquo;
            </blockquote>
          </div>

          {/* Inverse Relationship Diagram Card */}
          <div className="p-4 rounded-xl bg-black/60 border border-slate-800 flex flex-col gap-3">
            <div className="text-hud-cyan font-bold text-xs flex items-center justify-between">
              <span>SPATIAL WORKLOAD RELATIONSHIP</span>
              <span className="text-[10px] text-slate-400">INVERSE FOVEATED DYNAMICS</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-center">
              <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 flex flex-col items-center justify-center gap-1">
                <span className="text-[10px] text-slate-400 font-semibold">RADIAL DISTANCE</span>
                <span className="text-lg font-bold text-white flex items-center gap-1">
                  0m <ArrowRight className="w-4 h-4 text-hud-cyan" /> 100m
                </span>
                <span className="text-[9px] text-hud-cyan font-bold">DISTANCE ↑</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 flex flex-col items-center justify-center gap-1">
                <span className="text-[10px] text-slate-400 font-semibold">GRID CELL SIZE</span>
                <span className="text-lg font-bold text-amber-400 flex items-center gap-1">
                  5cm <ArrowRight className="w-4 h-4 text-amber-400" /> 50cm
                </span>
                <span className="text-[9px] text-amber-400 font-bold">CELL SIZE ↑ (10x Coarser)</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 flex flex-col items-center justify-center gap-1">
                <span className="text-[10px] text-slate-400 font-semibold">COMPUTATIONAL WORKLOAD</span>
                <span className="text-lg font-bold text-hud-emerald flex items-center gap-1">
                  97.6 MB <ArrowRight className="w-4 h-4 text-hud-emerald" /> 3.8 MB
                </span>
                <span className="text-[9px] text-hud-emerald font-bold">WORKLOAD &amp; MEMORY ↓ (96% Saved)</span>
              </div>
            </div>
          </div>

          {/* 4 Spatial Zones Deep Dive Grid */}
          <div>
            <div className="text-xs font-bold text-slate-200 mb-2.5 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-hud-cyan" /> FOUR CONCENTRIC SPATIAL FOVEATION ZONES
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {zones.map((z) => (
                <div
                  key={z.zoneNumber}
                  className="p-4 rounded-xl glass-card border hover:border-hud-cyan/50 transition cursor-pointer group flex flex-col justify-between"
                  style={{ borderColor: `${z.color}40` }}
                  onClick={() => {
                    if (onSelectRing) onSelectRing(z.zoneNumber - 1);
                    onClose();
                  }}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-6 h-6 rounded-lg font-black text-slate-950 flex items-center justify-center text-xs"
                          style={{ backgroundColor: z.color }}
                        >
                          Z{z.zoneNumber}
                        </span>
                        <span className="font-bold text-white tracking-wide">
                          {z.name}
                        </span>
                      </div>
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold"
                        style={{ color: z.color, backgroundColor: `${z.color}15`, border: `1px solid ${z.color}40` }}
                      >
                        {z.range}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300 font-sans leading-relaxed mb-3">
                      {z.purpose}
                    </p>
                  </div>

                  <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10.5px]">
                    <div>
                      <span className="text-slate-400">Resolution: </span>
                      <span className="font-bold text-white">{z.resolution}</span>
                    </div>
                    <span className="font-semibold" style={{ color: z.color }}>
                      {z.priority}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
