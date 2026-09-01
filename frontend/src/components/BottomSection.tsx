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
    <footer className="w-full glass-panel border-t border-hud-border flex flex-col z-20 relative select-none">
      {/* 1. INTERACTIVE TIMELINE / SCRUBBER BAR */}
      <div className="px-5 py-2 border-b border-slate-800/80 flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 text-hud-cyan font-bold min-w-[130px]">
          <Clock className="w-3.5 h-3.5" />
          <span>FRAME SCRUBBER</span>
        </div>

        <div className="flex-1 flex items-center gap-3">
          <span className="text-slate-500 text-[11px]">00000</span>
          <input
            type="range"
            min={0}
            max={totalFrames || 100}
            value={currentFrameIndex}
            onChange={(e) => onScrubFrame(parseInt(e.target.value))}
            className="flex-1 accent-hud-cyan cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
          <span className="text-slate-300 font-bold text-[11px]">
            {String(currentFrameIndex).padStart(5, '0')} / {String(totalFrames || 100).padStart(5, '0')}
          </span>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 rounded glass-card text-slate-400 hover:text-hud-cyan transition flex items-center gap-1 text-[11px]"
          title="Toggle Expanded Event Logs"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>LOGS</span>
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
        </button>
      </div>

      {/* 2. EXPANDABLE EVENT LOG CONSOLE */}
      {isExpanded && (
        <div className="px-5 py-2.5 bg-black/70 border-b border-slate-800/80 flex flex-col gap-2 max-h-36 overflow-y-auto font-mono text-[11px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-400">
              <Filter className="w-3 h-3" />
              <span>FILTER LOGS:</span>
              {(['ALL', 'HAZARD', 'PERCEPTION', 'GRID'] as const).map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setLogFilter(lvl)}
                  className={`px-2 py-0.5 rounded transition ${
                    logFilter === lvl
                      ? 'bg-hud-cyan text-slate-950 font-bold'
                      : 'text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
            <span className="text-[10px] text-slate-500">{filteredLogs.length} EVENTS</span>
          </div>

          <div className="space-y-1">
            {filteredLogs.map((l) => (
              <div key={l.id} className="flex items-baseline gap-2">
                <span className="text-slate-500 text-[10px]">{l.time}</span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                    l.level === 'HAZARD'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : l.level === 'PERCEPTION'
                      ? 'bg-hud-cyan-dim text-hud-cyan border border-hud-cyan/30'
                      : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  }`}
                >
                  {l.level}
                </span>
                <span className="text-slate-300">{l.message}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {/* 3. 8-CLASS SEMANTIC FILTER LEGEND & TRAVERSABILITY SCALE */}
      <div className="px-5 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        {/* Semantic Class Filters */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-400 mr-1 text-[11px]">CLASSES:</span>
          {Object.values(SEMANTIC_CLASSES).map((cls) => {
            const isVisible = visibleClasses.has(cls.id);
            return (
              <button
                key={cls.id}
                onClick={() => onToggleClass(cls.id)}
                className={`px-2.5 py-1 rounded-md border transition flex items-center gap-1.5 text-[11px] ${
                  isVisible
                    ? 'bg-slate-900 text-slate-100 border-slate-700 shadow-sm'
                    : 'bg-black/40 text-slate-500 border-slate-900 opacity-50'
                }`}
              >
                <span
                  className="w-2.5 h-2.5 rounded-sm"
                  style={{ backgroundColor: cls.color }}
                />
                <span>{cls.label}</span>
                {isVisible ? (
                  <Eye className="w-2.5 h-2.5 text-hud-cyan" />
                ) : (
                  <EyeOff className="w-2.5 h-2.5 text-slate-600" />
                )}
              </button>
            );
          })}
        </div>

        {/* Traversability & Height Gradient */}
        <div className="flex items-center gap-4 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">TRAVERSABILITY:</span>
            <div className="w-24 h-2 rounded bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500" />
            <span className="text-[10px] text-slate-400">0.0 (SAFE) → 1.0</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">HEIGHT Z:</span>
            <div className="w-20 h-2 rounded bg-gradient-to-r from-blue-600 via-cyan-400 to-amber-400" />
            <span className="text-[10px] text-slate-400">-0.5m → +3.5m</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
