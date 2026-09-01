import React, { useState, useEffect } from 'react';
import { X, Zap, Cpu, CheckCircle2, ArrowRight, ShieldCheck, Database, Layers } from 'lucide-react';
import { apiService } from '../../services/api';
import { PipelineStageInfo } from '../../types';

interface ArchitectureModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ArchitectureModal: React.FC<ArchitectureModalProps> = ({ isOpen, onClose }) => {
  const [stages, setStages] = useState<PipelineStageInfo[]>([]);

  useEffect(() => {
    if (isOpen) {
      apiService.fetchArchitecture().then(setStages);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="w-full max-w-4xl max-h-[90vh] glass-panel rounded-2xl border border-hud-cyan/40 shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* MODAL HEADER */}
        <div className="px-6 py-4 border-b border-hud-border flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-hud-cyan-dim text-hud-cyan border border-hud-cyan/30">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-display text-white">
                End-to-End System Pipeline Architecture
              </h2>
              <p className="text-xs font-mono text-slate-400">
                Foveated Semantic 2.5D LiDAR Mapping — Module Ownership &amp; Shared Data Contracts
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
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono text-slate-300">
          {/* Architecture Flow Diagram */}
          <div className="p-4 rounded-xl bg-black/50 border border-slate-800">
            <div className="text-hud-cyan font-bold text-xs mb-3 flex items-center gap-1.5">
              <Layers className="w-4 h-4" /> DATA EXCHANGE &amp; CONTRACT FLOW
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-center text-[11px]">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-hud-emerald font-bold">1. PREPROCESSING</div>
                <div className="text-slate-400 text-[10px]">Lead: Amulya</div>
                <div className="mt-1 text-[9px] text-slate-500 font-mono">PointCloudFrame</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-hud-cyan font-bold">2. PERCEPTION</div>
                <div className="text-slate-400 text-[10px]">Lead: Vedant</div>
                <div className="mt-1 text-[9px] text-slate-500 font-mono">SemanticPointCloud</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-purple-400 font-bold">3. FOVEATED GRID</div>
                <div className="text-slate-400 text-[10px]">Lead: Manashri</div>
                <div className="mt-1 text-[9px] text-slate-500 font-mono">Multi-Ring Index</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-amber-400 font-bold">4. 2.5D MAPPING</div>
                <div className="text-slate-400 text-[10px]">Lead: Heet</div>
                <div className="mt-1 text-[9px] text-slate-500 font-mono">SemanticMap</div>
              </div>
            </div>
          </div>

          {/* Module Ownership Table */}
          <div className="space-y-2">
            <div className="text-slate-200 font-bold text-xs flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-hud-emerald" /> TEAM MODULE BREAKDOWN &amp; RESPONSIBILITIES
            </div>
            <div className="space-y-2">
              {stages.map((stage) => (
                <div
                  key={stage.stage_id}
                  className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-hud-cyan/40 transition flex flex-col md:flex-row md:items-center justify-between gap-3"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-bold text-hud-cyan">
                        STAGE {stage.stage_id}
                      </span>
                      <span className="font-bold text-white text-sm">{stage.name}</span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Module Path: <code className="text-hud-cyan">{stage.module}</code> &bull; Owner: <span className="text-slate-200 font-semibold">{stage.owner}</span>
                    </div>
                  </div>

                  <div className="text-left md:text-right space-y-0.5 text-[11px]">
                    <div className="text-slate-400">
                      Input: <span className="text-slate-200">{stage.input}</span> &rarr; Output: <span className="text-emerald-400">{stage.output}</span>
                    </div>
                    <div className="text-[10px] text-slate-500">{stage.resolution}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MODAL FOOTER */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-[11px] font-mono">
          <span className="text-slate-500">
            Strict Module Ownership &bull; ISO-Compliant Autonomous Perception Stack
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-hud-cyan text-slate-950 font-bold hover:bg-hud-cyan/90 transition shadow-cyan-glow-sm"
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
