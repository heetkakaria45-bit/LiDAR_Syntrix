import React, { useState, useEffect } from 'react';
import {
  Car,
  Compass,
  ShieldAlert,
  Gauge,
  Zap,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  RotateCcw,
  Octagon,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Navigation,
} from 'lucide-react';

export interface TrafficActorState {
  id: string;
  x: number;
  z: number;
  speed: number;
  type: 'leading' | 'oncoming';
  visible: boolean;
}

export interface TeleopState {
  speed: number;
  speedKmh: number;
  targetSpeedKmh: number;
  steerAngle: number;
  mode: 'manual' | 'autonomous';
  distanceTraveled: number;
  throttlePct: number;
  brakePct: number;
  isReverse?: boolean;
  laneX?: number;
  eStop: boolean;
  isCollided?: boolean;
  trafficActors?: TrafficActorState[];
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
  const [pressedKeys, setPressedKeys] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      const code = e.code;
      setPressedKeys((prev) => ({ ...prev, [code]: true }));

      if (code === 'KeyW' || code === 'ArrowUp') {
        onUpdateTeleop((prev) => {
          if (prev.isCollided) return prev; // Forward blocked during collision
          return {
            ...prev,
            mode: 'manual',
            targetSpeedKmh: 35,
            throttlePct: 85,
            brakePct: 0,
            isReverse: false,
            eStop: false,
          };
        });
      } else if (code === 'KeyS' || code === 'ArrowDown') {
        // Reverse mode: reverses vehicle backwards
        onUpdateTeleop((prev) => ({
          ...prev,
          mode: 'manual',
          targetSpeedKmh: -18,
          throttlePct: 0,
          brakePct: 0,
          isReverse: true,
          eStop: false,
          isCollided: false, // Reversing clears forward collision
        }));
      } else if (code === 'KeyA' || code === 'ArrowLeft') {
        onUpdateTeleop((prev) => ({
          ...prev,
          steerAngle: -22,
        }));
      } else if (code === 'KeyD' || code === 'ArrowRight') {
        onUpdateTeleop((prev) => ({
          ...prev,
          steerAngle: 22,
        }));
      } else if (code === 'Space') {
        e.preventDefault();
        onUpdateTeleop((prev) => ({
          ...prev,
          eStop: !prev.eStop,
          targetSpeedKmh: 0,
          brakePct: 100,
          throttlePct: 0,
          isReverse: false,
        }));
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const code = e.code;
      setPressedKeys((prev) => ({ ...prev, [code]: false }));

      if (code === 'KeyA' || code === 'ArrowLeft' || code === 'KeyD' || code === 'ArrowRight') {
        onUpdateTeleop((prev) => ({ ...prev, steerAngle: 0 }));
      }
      if (code === 'KeyW' || code === 'ArrowUp') {
        onUpdateTeleop((prev) => ({
          ...prev,
          throttlePct: 0,
          targetSpeedKmh: 0,
        }));
      }
      if (code === 'KeyS' || code === 'ArrowDown') {
        onUpdateTeleop((prev) => ({
          ...prev,
          isReverse: false,
          targetSpeedKmh: 0,
        }));
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
    onUpdateTeleop((prev) => {
      if (prev.isCollided) return prev;
      return {
        ...prev,
        mode: 'manual',
        targetSpeedKmh: 35,
        throttlePct: 85,
        brakePct: 0,
        isReverse: false,
        eStop: false,
      };
    });
  };

  const handleGasUp = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      throttlePct: 0,
      targetSpeedKmh: 0,
    }));
  };

  const handleReverseDown = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      mode: 'manual',
      targetSpeedKmh: -18,
      throttlePct: 0,
      brakePct: 0,
      isReverse: true,
      eStop: false,
      isCollided: false,
    }));
  };

  const handleReverseUp = () => {
    onUpdateTeleop((prev) => ({
      ...prev,
      isReverse: false,
      targetSpeedKmh: 0,
    }));
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
      isReverse: false,
      brakePct: prev.eStop ? 0 : 100,
    }));
  };

  const isWPressed = pressedKeys['KeyW'] || pressedKeys['ArrowUp'];
  const isAPressed = pressedKeys['KeyA'] || pressedKeys['ArrowLeft'];
  const isSPressed = pressedKeys['KeyS'] || pressedKeys['ArrowDown'];
  const isDPressed = pressedKeys['KeyD'] || pressedKeys['ArrowRight'];
  const isSpacePressed = pressedKeys['Space'];

  // Transmission Gear Estimation
  const activeGear = teleop.eStop
    ? 'E'
    : teleop.isReverse || teleop.speed < -0.1 || isSPressed
    ? 'R'
    : teleop.speed > 0.3 || isWPressed
    ? 'D'
    : teleop.brakePct > 50
    ? 'P'
    : 'N';

  const lanePositionM = teleop.laneX !== undefined ? teleop.laneX : 0.0;
  const laneName =
    lanePositionM < -1.2
      ? 'LEFT LANE'
      : lanePositionM > 1.2
      ? 'RIGHT LANE'
      : 'CENTER LANE';

  return (
    <div className="absolute top-16 left-4 z-20 flex flex-col gap-2 font-sans select-none pointer-events-auto">
      <div className="glass-panel p-3.5 rounded-2xl border border-hud-cyan/40 shadow-panel flex flex-col gap-3 w-[320px] bg-[#0c111a]/95 backdrop-blur-2xl tech-box">
        {/* TACTICAL CONSOLE HEADER */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/90">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-hud-cyan/15 border border-hud-cyan/40 flex items-center justify-center text-hud-cyan shadow-cyan-glow-sm">
              <Car className="w-4 h-4 text-hud-cyan" />
            </div>
            <div>
              <div className="font-bold text-white text-xs tracking-wider font-display uppercase leading-tight">
                VEHICLE TELEOP
              </div>
              <div className="text-[9.5px] text-hud-cyan/90 font-mono font-semibold uppercase tracking-wider mt-0.5">
                AUTONOMOUS CONTROL SYSTEM
              </div>
            </div>
          </div>

          {/* TRANSMISSION GEAR INDICATOR PILLS */}
          <div className="flex items-center gap-1 bg-black/60 p-1 rounded-xl border border-slate-800">
            {(['P', 'R', 'N', 'D'] as const).map((g) => {
              const isActive = activeGear === g;
              return (
                <span
                  key={g}
                  className={`px-2 py-0.5 rounded-lg text-[10px] font-mono font-black transition-all ${
                    isActive
                      ? g === 'D'
                        ? 'bg-hud-emerald text-slate-950 shadow-emerald-glow-sm'
                        : g === 'R'
                        ? 'bg-amber-400 text-slate-950 shadow-amber-glow'
                        : g === 'P'
                        ? 'bg-hud-cyan text-slate-950'
                        : 'bg-slate-300 text-slate-950'
                      : 'text-slate-500 hover:text-slate-400'
                  }`}
                >
                  {g}
                </span>
              );
            })}

            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="text-slate-400 hover:text-white p-1 ml-0.5 rounded-lg hover:bg-slate-800 transition cursor-pointer"
              title={isMinimized ? 'Expand Teleop Cockpit' : 'Minimize Teleop Cockpit'}
            >
              {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* COLLISION ALERT BANNER */}
        {teleop.isCollided && (
          <div className="p-2.5 rounded-xl bg-red-950/90 border border-red-500 text-red-200 flex items-center justify-between animate-pulse shadow-lg">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
              <div>
                <div className="text-xs font-black text-white font-mono tracking-wide">
                  OBSTACLE CONTACT STOP
                </div>
                <div className="text-[10px] text-red-300 font-sans">Press [S] to Reverse & Clear</div>
              </div>
            </div>
            <button
              onClick={() => {
                onUpdateTeleop((prev) => ({ ...prev, isCollided: false, speed: 0 }));
              }}
              className="px-2.5 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white font-mono text-[10px] font-bold transition cursor-pointer"
            >
              CLEAR
            </button>
          </div>
        )}

        {!isMinimized && (
          <div className="flex flex-col gap-3">
            {/* 1. PRIMARY VELOCITY & STEERING GAUGES */}
            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/90 flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                {/* VELOCITY READOUT */}
                <div className="flex flex-col">
                  <div className="text-[10px] text-slate-300 font-sans font-semibold tracking-wider uppercase flex items-center gap-1.5">
                    <Gauge className="w-3.5 h-3.5 text-hud-cyan" />
                    <span>VELOCITY</span>
                  </div>
                  <div className="flex items-baseline gap-1.5 mt-0.5">
                    {teleop.speed < -0.05 ? (
                      <ArrowDown className="w-4 h-4 text-amber-400 animate-bounce" />
                    ) : teleop.speed > 0.05 ? (
                      <ArrowUp className="w-4 h-4 text-hud-emerald animate-pulse" />
                    ) : null}
                    <span className="text-3xl font-black text-white font-mono tracking-tight font-tabular">
                      {Math.abs(teleop.speedKmh).toFixed(1)}
                    </span>
                    <span className="text-[10.5px] font-bold text-hud-cyan font-mono">KM/H</span>
                  </div>
                </div>

                {/* STEERING ANGLE READOUT */}
                <div className="flex flex-col items-end">
                  <div className="text-[10px] text-slate-300 font-sans font-semibold tracking-wider uppercase flex items-center gap-1.5">
                    <Compass className="w-3.5 h-3.5 text-purple-400" />
                    <span>STEERING</span>
                  </div>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span
                      className={`text-base font-bold font-mono font-tabular ${
                        teleop.steerAngle < 0
                          ? 'text-hud-cyan'
                          : teleop.steerAngle > 0
                          ? 'text-purple-400'
                          : 'text-slate-300'
                      }`}
                    >
                      {teleop.steerAngle > 0
                        ? `+${teleop.steerAngle.toFixed(0)}° R`
                        : teleop.steerAngle < 0
                        ? `${teleop.steerAngle.toFixed(0)}° L`
                        : `0.0° CTR`}
                    </span>
                  </div>
                </div>
              </div>

              {/* 2. DYNAMIC LANE TRACKER & OFFSET */}
              <div className="p-2 rounded-xl bg-black/60 border border-slate-800/90 flex items-center justify-between text-xs font-sans">
                <div className="flex items-center gap-2">
                  <Navigation className="w-3.5 h-3.5 text-hud-cyan" />
                  <span className="text-slate-300 font-medium">LANE:</span>
                  <span className="font-bold text-white font-mono tracking-wide">{laneName}</span>
                </div>
                <div className="text-slate-300 font-sans font-medium">
                  Offset:{' '}
                  <span className="text-hud-cyan font-bold font-mono font-tabular">
                    {lanePositionM >= 0 ? `+${lanePositionM.toFixed(2)}m` : `${lanePositionM.toFixed(2)}m`}
                  </span>
                </div>
              </div>

              {/* STATUS & ODOMETER FOOTNOTE */}
              <div className="flex items-center justify-between text-[10px] pt-1 border-t border-slate-900">
                <div className="flex items-center gap-1 text-slate-300 font-sans font-medium">
                  <span className="text-slate-400">ODOMETER:</span>
                  <span className="text-slate-100 font-mono font-bold font-tabular">
                    {teleop.distanceTraveled.toFixed(1)}m
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-md text-[9.5px] font-mono font-bold border ${
                      teleop.speed < -0.1
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : teleop.speed > 0.1
                        ? 'bg-hud-emerald/20 text-hud-emerald border-hud-emerald/40'
                        : 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}
                  >
                    {teleop.speed < -0.1
                      ? 'REVERSING'
                      : teleop.speed > 0.1
                      ? 'CRUISING'
                      : 'STANDSTILL'}
                  </span>

                  <button
                    onClick={handleEStop}
                    className={`px-2 py-0.5 rounded-md font-mono font-bold text-[9.5px] transition cursor-pointer ${
                      teleop.eStop
                        ? 'bg-red-500 text-white animate-pulse'
                        : 'bg-red-500/15 text-red-300 border border-red-500/40 hover:bg-red-500/30'
                    }`}
                    title="Toggle Emergency Stop (Spacebar)"
                  >
                    {teleop.eStop ? 'STOPPED' : 'E-STOP'}
                  </button>
                </div>
              </div>
            </div>

            {/* 3. TACTICAL DIRECT-DRIVE CONTROLS (WASD) */}
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/90 flex flex-col items-center gap-2.5">
              {/* FORWARD (W) */}
              <button
                onMouseDown={handleGasDown}
                onMouseUp={handleGasUp}
                onTouchStart={handleGasDown}
                onTouchEnd={handleGasUp}
                className={`w-40 py-2 rounded-xl border transition-all flex items-center justify-center gap-1.5 font-mono font-bold text-xs cursor-pointer ${
                  isWPressed || teleop.throttlePct > 0
                    ? 'bg-hud-emerald/30 border-hud-emerald text-white shadow-emerald-glow-sm scale-[0.98]'
                    : 'bg-slate-900/90 border-slate-700/90 text-slate-200 hover:text-hud-emerald hover:border-hud-emerald/50'
                }`}
              >
                <ChevronUp className="w-4 h-4 text-hud-emerald" />
                <span>FORWARD [W]</span>
              </button>

              {/* MIDDLE ROW (A, S, D) */}
              <div className="flex items-center gap-2 w-full justify-between">
                <button
                  onMouseDown={() => handleSteer('left')}
                  onMouseUp={() => handleSteer('center')}
                  onTouchStart={() => handleSteer('left')}
                  onTouchEnd={() => handleSteer('center')}
                  className={`flex-1 py-2 rounded-xl border transition-all flex items-center justify-center gap-1 font-mono font-bold text-[11px] cursor-pointer ${
                    isAPressed || teleop.steerAngle < 0
                      ? 'bg-hud-cyan/30 border-hud-cyan text-white shadow-cyan-glow-sm scale-[0.98]'
                      : 'bg-slate-900/90 border-slate-700/90 text-slate-200 hover:text-hud-cyan hover:border-hud-cyan/50'
                  }`}
                  title="Steer left to shift to left lane (Key A)"
                >
                  <ChevronLeft className="w-3.5 h-3.5 text-hud-cyan" />
                  <span>LEFT [A]</span>
                </button>

                <button
                  onMouseDown={handleReverseDown}
                  onMouseUp={handleReverseUp}
                  onTouchStart={handleReverseDown}
                  onTouchEnd={handleReverseUp}
                  className={`flex-1 py-2 rounded-xl border transition-all flex items-center justify-center gap-1 font-mono font-bold text-[11px] cursor-pointer ${
                    isSPressed || teleop.isReverse || teleop.speed < -0.1
                      ? 'bg-amber-500/30 border-amber-400 text-amber-200 shadow-amber-glow scale-[0.98]'
                      : 'bg-slate-900/90 border-slate-700/90 text-slate-200 hover:text-amber-400 hover:border-amber-500/50'
                  }`}
                  title="Reverse drive (Key S)"
                >
                  <ChevronDown className="w-3.5 h-3.5 text-amber-400" />
                  <span>REVERSE [S]</span>
                </button>

                <button
                  onMouseDown={() => handleSteer('right')}
                  onMouseUp={() => handleSteer('center')}
                  onTouchStart={() => handleSteer('right')}
                  onTouchEnd={() => handleSteer('center')}
                  className={`flex-1 py-2 rounded-xl border transition-all flex items-center justify-center gap-1 font-mono font-bold text-[11px] cursor-pointer ${
                    isDPressed || teleop.steerAngle > 0
                      ? 'bg-hud-cyan/30 border-hud-cyan text-white shadow-cyan-glow-sm scale-[0.98]'
                      : 'bg-slate-900/90 border-slate-700/90 text-slate-200 hover:text-hud-cyan hover:border-hud-cyan/50'
                  }`}
                  title="Steer right to shift to right lane (Key D)"
                >
                  <span>RIGHT [D]</span>
                  <ChevronRight className="w-3.5 h-3.5 text-hud-cyan" />
                </button>
              </div>

              {/* BOTTOM SPACEBAR E-STOP & RESET */}
              <div className="flex items-center gap-2 w-full">
                <button
                  onClick={handleEStop}
                  className={`flex-1 py-1.5 rounded-xl border transition-all flex items-center justify-center gap-1.5 font-mono font-bold text-[10px] cursor-pointer ${
                    teleop.eStop || isSpacePressed
                      ? 'bg-red-600 border-red-500 text-white'
                      : 'bg-slate-900/90 border-slate-800 text-slate-300 hover:text-red-400'
                  }`}
                >
                  <Octagon className="w-3.5 h-3.5 text-red-400" />
                  <span>SPACE: E-STOP</span>
                </button>

                <button
                  onClick={onResetVehicle}
                  className="px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition flex items-center gap-1 font-mono text-[10px] font-semibold cursor-pointer"
                  title="Reset vehicle telemetry & position to origin"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>RESET</span>
                </button>
              </div>
            </div>

            {/* 4. TACTICAL SHORTCUTS HINT */}
            <div className="text-[10px] text-slate-400 font-mono text-center flex items-center justify-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-hud-emerald font-bold">
                W
              </kbd>
              <span>DRIVE</span>
              <span>•</span>
              <kbd className="px-1.5 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-amber-400 font-bold">
                S
              </kbd>
              <span>REVERSE</span>
              <span>•</span>
              <kbd className="px-1.5 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-hud-cyan font-bold">
                A/D
              </kbd>
              <span>LANE CHANGE</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
