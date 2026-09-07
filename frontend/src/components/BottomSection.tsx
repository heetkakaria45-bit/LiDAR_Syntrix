import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Filter,
  Eye,
  EyeOff,
  Sliders,
  ShieldAlert,
  Layers,
  ChevronDown,
  ChevronUp,
  Clock,
} from 'lucide-react';
import { SEMANTIC_CLASSES, FramePayload, SemanticClassInfo } from '../types';

interface BottomSectionProps {
  frame: FramePayload | null;
  currentFrameIndex: number;
  totalFrames: number;
  onScrubFrame: (frameIdx: number) => void;
  visibleClasses: Set<number>;
  onToggleClass: (classId: number) => void;
}

interface LogEntry {
  id: string;
  time: string;
  level: 'INFO' | 'HAZARD' | 'PERCEPTION' | 'GRID';
  message: string;
}

export const BottomSection: React.FC<BottomSectionProps> = ({
  frame,
  currentFrameIndex,
  totalFrames,
  onScrubFrame,
  visibleClasses,
  onToggleClass,
}) => {
  const [logFilter, setLogFilter] = useState<'ALL' | 'HAZARD' | 'PERCEPTION' | 'GRID'>('ALL');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Generate real-time dynamic logs as frames advance
  useEffect(() => {
    if (!frame) return;
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(
      now.getMinutes()
    ).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}.${String(
      now.getMilliseconds()
    ).padStart(3, '0')}`;

    const newLogs: LogEntry[] = [];

    if (frame.telemetry.frame_count % 3 === 0) {
      newLogs.push({
        id: `log-foveated-${Date.now()}`,
        time: timeStr,
        level: 'GRID',
        message: `Foveated multi-ring hash updated: ${frame.telemetry.cell_count} cells across 4 rings. (Bandwidth saved: +${frame.telemetry.memory_savings_pct}%)`,
      });
    }

    if (frame.hazards && frame.hazards.length > 0 && frame.telemetry.frame_count % 5 === 0) {
      const h = frame.hazards[0];
      newLogs.push({
        id: `log-hazard-${Date.now()}`,
        time: timeStr,
        level: 'HAZARD',
        message: `Hazard flagged: [${h.type.toUpperCase()}] at (X: ${h.x}m, Y: ${h.y}m) — ${h.details}`,
      });
    }

    if (frame.boundingBoxes && frame.boundingBoxes.length > 0 && frame.telemetry.frame_count % 7 === 0) {
      const b = frame.boundingBoxes[0];
      newLogs.push({
        id: `log-percep-${Date.now()}`,
        time: timeStr,
        level: 'PERCEPTION',
        message: `Dynamic tracking: [${b.className}] confidence ${(b.confidence * 100).toFixed(1)}% at distance ${Math.hypot(b.center[0], b.center[1]).toFixed(1)}m`,
      });
    }

    if (newLogs.length > 0) {
      setLogs((prev) => [...prev.slice(-40), ...newLogs]);
    }
  }, [frame]);

  const filteredLogs = logs.filter((l) => logFilter === 'ALL' || l.level === logFilter);

  return (
    <footer className="w-full glass-panel border-t border-hud-border flex flex-col z-20 relative select-none font-sans">
      {/* 1. INTERACTIVE TIMELINE / SCRUBBER BAR */}
      <div className="px-5 py-2.5 border-b border-slate-800/80 flex items-center gap-4 text-xs font-sans">
        <div className="flex items-center gap-2 text-hud-cyan font-bold min-w-[140px] font-display text-xs">
          <Clock className="w-4 h-4 text-hud-cyan" />
          <span>FRAME SCRUBBER</span>
        </div>

        <div className="flex-1 flex items-center gap-3">
          <span className="text-slate-400 font-mono text-xs font-tabular">00000</span>
          <input
            type="range"
            min={0}
            max={totalFrames || 100}
            value={currentFrameIndex}
            onChange={(e) => onScrubFrame(parseInt(e.target.value))}
            className="flex-1 accent-hud-cyan cursor-pointer h-2 bg-slate-800 rounded-lg"
          />
          <span className="text-slate-200 font-bold font-mono text-xs font-tabular">
            {String(currentFrameIndex).padStart(5, '0')} / {String(totalFrames || 100).padStart(5, '0')}
          </span>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 px-2.5 rounded-xl glass-card text-slate-300 hover:text-hud-cyan hover:border-hud-cyan/40 transition flex items-center gap-1.5 text-xs font-bold cursor-pointer"
          title="Toggle Expanded Event Logs"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>LOGS</span>
          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* 2. EXPANDABLE EVENT LOG CONSOLE */}
      {isExpanded && (
        <div className="px-5 py-3 bg-black/80 border-b border-slate-800/90 flex flex-col gap-2 max-h-40 overflow-y-auto font-mono text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-300 font-sans font-semibold text-xs">
              <Filter className="w-3.5 h-3.5 text-hud-cyan" />
              <span>FILTER LOGS:</span>
              {(['ALL', 'HAZARD', 'PERCEPTION', 'GRID'] as const).map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setLogFilter(lvl)}
                  className={`px-2.5 py-0.5 rounded-lg text-xs font-mono font-bold transition cursor-pointer ${
                    logFilter === lvl
                      ? 'bg-hud-cyan text-slate-950 shadow-cyan-glow-sm'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
            <span className="text-[11px] text-slate-400 font-mono font-semibold">{filteredLogs.length} EVENTS</span>
          </div>

          <div className="space-y-1.5">
            {filteredLogs.map((l) => (
              <div key={l.id} className="flex items-baseline gap-2.5 text-xs">
                <span className="text-slate-400 font-mono text-[11px]">{l.time}</span>
                <span
                  className={`px-2 py-0.5 rounded-md text-[10px] font-bold font-mono ${
                    l.level === 'HAZARD'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : l.level === 'PERCEPTION'
                      ? 'bg-hud-cyan-dim text-hud-cyan border border-hud-cyan/30'
                      : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  }`}
                >
                  {l.level}
                </span>
                <span className="text-slate-200 font-sans">{l.message}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {/* 3. 8-CLASS SEMANTIC FILTER LEGEND & TRAVERSABILITY SCALE */}
      <div className="px-5 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs font-sans">
        {/* Semantic Class Filters */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-300 font-bold uppercase tracking-wider text-[11px] mr-1 font-display">CLASSES:</span>
          {Object.values(SEMANTIC_CLASSES).map((cls) => {
            const isVisible = visibleClasses.has(cls.id);
            return (
              <button
                key={cls.id}
                onClick={() => onToggleClass(cls.id)}
                className={`px-2.5 py-1 rounded-xl border transition flex items-center gap-1.5 text-xs font-semibold cursor-pointer ${
                  isVisible
                    ? 'bg-slate-900 text-slate-100 border-slate-700 hover:border-slate-500 shadow-sm'
                    : 'bg-black/40 text-slate-500 border-slate-900 opacity-50'
                }`}
              >
                <span
                  className="w-2.5 h-2.5 rounded-sm"
                  style={{ backgroundColor: cls.color }}
                />
                <span>{cls.label}</span>
                {isVisible ? (
                  <Eye className="w-3 h-3 text-hud-cyan" />
                ) : (
                  <EyeOff className="w-3 h-3 text-slate-500" />
                )}
              </button>
            );
          })}
        </div>

        {/* Traversability & Height Gradient */}
        <div className="flex items-center gap-4 text-xs font-sans">
          <div className="flex items-center gap-2">
            <span className="text-slate-300 font-semibold text-[11px]">TRAVERSABILITY:</span>
            <div className="w-24 h-2.5 rounded-md bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 border border-slate-700" />
            <span className="text-[11px] text-slate-300 font-mono">SAFE &rarr; RISK</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-300 font-semibold text-[11px]">HEIGHT (Z):</span>
            <div className="w-20 h-2.5 rounded-md bg-gradient-to-r from-blue-600 via-cyan-400 to-amber-400 border border-slate-700" />
            <span className="text-[11px] text-slate-300 font-mono">-0.5m &rarr; +3.5m</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
