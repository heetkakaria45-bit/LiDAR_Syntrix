import React, { useState, useEffect } from 'react';
import { X, BarChart3, TrendingDown, Zap, ShieldCheck, Database, Award } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { apiService } from '../../services/api';

interface BenchmarkModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BenchmarkModal: React.FC<BenchmarkModalProps> = ({ isOpen, onClose }) => {
  const [benchmarkData, setBenchmarkData] = useState<any>(null);

  useEffect(() => {
    if (isOpen) {
      apiService.fetchBenchmark().then(setBenchmarkData);
    }
  }, [isOpen]);

  if (!isOpen || !benchmarkData) return null;

  const { uniform_vs_foveated, distance_bins } = benchmarkData;

  const chartData = distance_bins.map((d: any) => ({
    name: d.bin.split(' ')[0],
    miou: d.miou,
    rmse: d.elevation_rmse_cm,
    density: d.cell_density_pct,
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="w-full max-w-4xl max-h-[90vh] glass-panel rounded-2xl border border-purple-500/40 shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* MODAL HEADER */}
        <div className="px-6 py-4 border-b border-hud-border flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-display text-white">
                SIH 2026 Scientific Benchmarks &amp; Comparative Study
              </h2>
              <p className="text-xs font-mono text-slate-400">
                Quantitative Evaluation: Standard Uniform 3D/2D Grid vs. Adaptive Foveated 2.5D Mapping
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

        {/* MODAL BODY */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs font-mono text-slate-300">
          {/* Top 3 Hero Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-4 rounded-xl glass-card border border-emerald-500/30">
              <div className="text-emerald-400 text-xs font-bold mb-1">MEMORY FOOTPRINT REDUCTION</div>
              <div className="text-3xl font-black text-white">{uniform_vs_foveated.memory_reduction_pct}%</div>
              <div className="text-[11px] text-slate-400 mt-1">
                {uniform_vs_foveated.memory_uniform_mb} MB &rarr; {uniform_vs_foveated.memory_foveated_mb} MB
              </div>
            </div>

            <div className="p-4 rounded-xl glass-card border border-hud-cyan/30">
              <div className="text-hud-cyan text-xs font-bold mb-1">PROCESSING SPEEDUP</div>
              <div className="text-3xl font-black text-white">{uniform_vs_foveated.speedup_factor}x</div>
              <div className="text-[11px] text-slate-400 mt-1">
                {uniform_vs_foveated.processing_time_uniform_ms}ms &rarr; {uniform_vs_foveated.processing_time_foveated_ms}ms
              </div>
            </div>

            <div className="p-4 rounded-xl glass-card border border-purple-500/30">
              <div className="text-purple-300 text-xs font-bold mb-1">CELL COMPRESSION RATIO</div>
              <div className="text-3xl font-black text-white">{uniform_vs_foveated.cell_reduction_ratio}:1</div>
              <div className="text-[11px] text-slate-400 mt-1">
                400,000 &rarr; 18,420 Active Cells
              </div>
            </div>
          </div>

          {/* Distance Binned Metrics Chart */}
          <div className="p-4 rounded-xl bg-black/40 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-hud-cyan font-bold text-xs flex items-center gap-1.5">
                <BarChart3 className="w-4 h-4" /> SEMANTIC ACCURACY (mIoU %) ACROSS FOVEATION RINGS
              </span>
              <span className="text-[11px] text-slate-400">Evaluated on SemanticKITTI Split</span>
            </div>

            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <YAxis domain={[50, 100]} stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(6, 11, 22, 0.95)',
                      borderColor: 'rgba(168, 85, 247, 0.4)',
                      borderRadius: '8px',
                      fontFamily: 'monospace',
                    }}
                  />
                  <Bar dataKey="miou" name="Semantic mIoU %" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry: any, index: number) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={index === 0 ? '#00ff9d' : index === 1 ? '#00f0ff' : index === 2 ? '#8b5cf6' : '#ec4899'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Distance Bins Table */}
          <div className="space-y-2">
            <div className="text-slate-200 font-bold text-xs">DISTANCE-BINNED GEOMETRIC &amp; SEMANTIC METRICS</div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 px-3">FOVEATION ZONE</th>
                    <th className="py-2 px-3">RESOLUTION</th>
                    <th className="py-2 px-3">SEMANTIC mIoU</th>
                    <th className="py-2 px-3">ELEVATION RMSE</th>
                    <th className="py-2 px-3">SPATIAL ALLOCATION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {distance_bins.map((bin: any, idx: number) => (
                    <tr key={idx} className="hover:bg-slate-900/40 transition">
                      <td className="py-2 px-3 font-semibold text-white flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{
                            backgroundColor: idx === 0 ? '#00ff9d' : idx === 1 ? '#00f0ff' : idx === 2 ? '#8b5cf6' : '#ec4899',
                          }}
                        />
                        {bin.bin}
                      </td>
                      <td className="py-2 px-3 text-slate-300 font-bold">{bin.resolution}</td>
                      <td className="py-2 px-3 text-hud-emerald font-bold">{bin.miou}%</td>
                      <td className="py-2 px-3 text-hud-cyan">{bin.elevation_rmse_cm} cm</td>
                      <td className="py-2 px-3 text-purple-300">{bin.cell_density_pct}% of total cells</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
