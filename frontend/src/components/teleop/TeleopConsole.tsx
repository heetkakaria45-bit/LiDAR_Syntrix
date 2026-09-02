import React, { useState, useEffect } from 'react';
import {
  Car,
  Cpu,
  ShieldAlert,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Zap,
} from 'lucide-react';

export interface TeleopState {
  speed: number;
  speedKmh: number;
  targetSpeedKmh: number;
  steerAngle: number;
  mode: 'manual' | 'autonomous';
  distanceTraveled: number;
  throttlePct: number;
  brakePct: number;
  eStop: boolean;
  isCollided?: boolean;
}

interface TeleopConsoleProps {
  teleop: TeleopState;
  onUpdateTeleop: (updater: (prev: TeleopState) => TeleopState) => void;
  onResetVehicle: () => void;
}

export const TeleopConsole: React.FC<TeleopConsoleProps> = ({
  teleop,
  onUpdateTeleop,
  onResetVehicle,
}) => {
  const [isMinimized, setIsMinimized] = useState<boolean>(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.code === 'KeyW' || e.code === 'ArrowUp') {
        onUpdateTeleop((prev) => ({
          ...prev,
          mode: 'manual',
          targetSpeedKmh: 35,
          throttlePct: 85,
          brakePct: 0,
          eStop: false,
        }));
      } else if (e.code === 'KeyS' || e.code === 'ArrowDown') {
        onUpdateTeleop((prev) => ({
          ...prev,
          throttlePct: 0,
          brakePct: 100,
          targetSpeedKmh: 0,
        }));
      } else if (e.code === 'KeyA' || e.code === 'ArrowLeft') {
        onUpdateTeleop((prev) => ({
          ...prev,
          steerAngle: -22,
        }));
      } else if (e.code === 'KeyD' || e.code === 'ArrowRight') {
        onUpdateTeleop((prev) => ({
          ...prev,
          steerAngle: 22,
        }));
      } else if (e.code === 'Space') {
        e.preventDefault();
        onUpdateTeleop((prev) => ({
          ...prev,
          eStop: !prev.eStop,
          targetSpeedKmh: 0,
          brakePct: 100,
          throttlePct: 0,
        }));
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'KeyA' || e.code === 'ArrowLeft' || e.code === 'KeyD' || e.code === 'ArrowRight') {
        onUpdateTeleop((prev) => ({ ...prev, steerAngle: 0 }));
      }
      if (e.code === 'KeyW' || e.code === 'ArrowUp') {
        // Stop moving when W / Up arrow is released
        onUpdateTeleop((prev) => ({
          ...prev,
          throttlePct: 0,
          targetSpeedKmh: 0,
        }));
      }
      if (e.code === 'KeyS' || e.code === 'ArrowDown') {
        onUpdateTeleop((prev) => ({ ...prev, brakePct: 0 }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [onUpdateTeleop]);

  const handleGasDown = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      mode: 'manual',
      targetSpeedKmh: 35,
      throttlePct: 85,
      brakePct: 0,
      eStop: false,
    }));
  };

  const handleGasUp = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      throttlePct: 0,
      targetSpeedKmh: 0,
    }));
  };

  const handleBrakeDown = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      throttlePct: 0,
      brakePct: 100,
      targetSpeedKmh: 0,
    }));
  };

  const handleBrakeUp = () => {
    onUpdateTeleop((prev) => ({ ...prev, brakePct: 0 }));
  };

  const handleSteer = (dir: 'left' | 'right' | 'center') => {
    onUpdateTeleop((prev) => ({
      ...prev,
      steerAngle: dir === 'left' ? -22 : dir === 'right' ? 22 : 0,
    }));
  };

  const handleEStop = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      eStop: !prev.eStop,
      targetSpeedKmh: 0,
      throttlePct: 0,
      brakePct: prev.eStop ? 0 : 100,
    }));
  };

  return (
    <div className="absolute top-16 left-4 z-20 flex flex-col gap-2 font-mono text-xs select-none pointer-events-auto">
      <div className="glass-panel p-2.5 rounded-2xl border border-hud-cyan/30 shadow-2xl flex flex-col gap-2 w-[270px] bg-slate-950/85 backdrop-blur-xl">
        {/* CONSOLE HEADER */}
        <div className="flex items-center justify-between pb-1 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded-lg bg-hud-cyan/20 text-hud-cyan border border-hud-cyan/40">
              <Car className="w-3.5 h-3.5 text-hud-cyan" />
            </div>
            <div>
              <div className="font-bold text-white text-[11.5px] tracking-wide font-display">
                VEHICLE TELEOP
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10.5px] text-hud-cyan font-bold">
              {teleop.speedKmh.toFixed(1)} km/h
            </span>
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
              title={isMinimized ? 'Expand Teleop' : 'Minimize Teleop'}
            >
              {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {!isMinimized && (
          <div className="flex flex-col gap-2">
            {/* 1. SPEED DISPLAY & STATUS */}
            <div className="p-2 rounded-xl bg-black/50 border border-slate-800/80 flex items-center justify-between">
              <div>
                <div className="text-[9px] text-slate-400 font-medium">SPEED (WASD CONTROLLED)</div>
                <div className="flex items-baseline gap-1">
                  <span className="text-xl font-black text-white font-mono">
                    {teleop.speedKmh.toFixed(1)}
                  </span>
                  <span className="text-[10px] font-bold text-hud-cyan">km/h</span>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className={`px-2 py-0.5 rounded text-[9.5px] font-bold ${
                  teleop.speedKmh > 0.5 ? 'bg-hud-emerald/20 text-hud-emerald border border-hud-emerald/40' : 'bg-slate-800 text-slate-400'
                }`}>
                  {teleop.speedKmh > 0.5 ? 'DRIVING' : 'STANDSTILL'}
                </span>

                <button
                  onClick={handleEStop}
                  className={`px-2 py-0.5 rounded font-bold text-[9px] transition ${
                    teleop.eStop
                      ? 'bg-red-500 text-white animate-pulse'
                      : 'bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30'
                  }`}
                >
                  {teleop.eStop ? 'STOPPED' : 'E-STOP'}
                </button>
              </div>
            </div>

            {/* 2. DIRECT DRIVE CONTROLLER PAD */}
            <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 flex flex-col items-center gap-1.5">
              <button
                onMouseDown={handleGasDown}
                onMouseUp={handleGasUp}
                onTouchStart={handleGasDown}
                onTouchEnd={handleGasUp}
                className="w-20 py-1.5 rounded-lg bg-black/60 border border-hud-emerald/50 text-hud-emerald hover:bg-hud-emerald/20 active:bg-hud-emerald/40 transition flex items-center justify-center gap-1 font-bold text-[11px]"
              >
                <ChevronUp className="w-4 h-4" />
                <span>GAS (W)</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  onMouseDown={() => handleSteer('left')}
                  onMouseUp={() => handleSteer('center')}
                  onTouchStart={() => handleSteer('left')}
                  onTouchEnd={() => handleSteer('center')}
                  className="w-16 py-1.5 rounded-lg bg-black/60 border border-hud-cyan/50 text-hud-cyan hover:bg-hud-cyan/20 active:bg-hud-cyan/40 transition flex items-center justify-center gap-0.5 font-bold text-[10px]"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>LEFT (A)</span>
                </button>

                <button
                  onMouseDown={handleBrakeDown}
                  onMouseUp={handleBrakeUp}
                  onTouchStart={handleBrakeDown}
                  onTouchEnd={handleBrakeUp}
                  className="w-18 py-1.5 rounded-lg bg-black/60 border border-red-500/50 text-red-400 hover:bg-red-500/20 active:bg-red-500/40 transition flex items-center justify-center gap-0.5 font-bold text-[10px]"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                  <span>BRAKE (S)</span>
                </button>

                <button
                  onMouseDown={() => handleSteer('right')}
                  onMouseUp={() => handleSteer('center')}
                  onTouchStart={() => handleSteer('right')}
                  onTouchEnd={() => handleSteer('center')}
                  className="w-16 py-1.5 rounded-lg bg-black/60 border border-hud-cyan/50 text-hud-cyan hover:bg-hud-cyan/20 active:bg-hud-cyan/40 transition flex items-center justify-center gap-0.5 font-bold text-[10px]"
                >
                  <span>RIGHT (D)</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="text-[9.5px] text-slate-500 text-center">
              Hold <kbd className="text-hud-emerald">W</kbd> to drive, release to stop. <kbd className="text-hud-cyan">A</kbd>/<kbd className="text-hud-cyan">D</kbd> to steer.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
