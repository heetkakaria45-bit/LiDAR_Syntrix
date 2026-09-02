import React, { useRef, useState, useEffect } from 'react';
import { Video, VideoOff, Maximize2, Minimize2, Eye, EyeOff, Camera, Radio } from 'lucide-react';
import { VideoBgMode } from '../types';

interface BackgroundVideoProps {
  mode: VideoBgMode;
  onModeChange: (mode: VideoBgMode) => void;
  opacity: number;
  onOpacityChange: (opacity: number) => void;
}

export const BackgroundVideo: React.FC<BackgroundVideoProps> = ({
  mode,
  onModeChange,
  opacity,
  onOpacityChange,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [videoError, setVideoError] = useState(false);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
  }, []);

  if (mode === 'off') {
    return (
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[#0a0e14] cyber-grid opacity-50" />
      </div>
    );
  }

  return (
    <>
      {/* FULLSCREEN AMBIENT BACKGROUND MODE (BRIGHT & VIBRANT) */}
      {mode === 'ambient' && (
        <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
          <video
            ref={videoRef}
            src="/bg_video.mp4"
            autoPlay
            loop
            muted
            playsInline
            onLoadedData={() => setVideoLoaded(true)}
            onError={() => setVideoError(true)}
            className="absolute inset-0 w-full h-full object-cover transition-opacity duration-700 filter brightness-105 contrast-110 saturate-110"
            style={{ opacity: videoLoaded ? Math.max(0.65, opacity) : 0 }}
          />

          {/* Tactical Refined Scrim (Preserves Video Visibility while keeping text legible) */}
          <div className="absolute inset-0 bg-[#0a0e14]/40" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0e14] via-transparent to-[#0a0e14]/60" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0a0e14]/50 via-transparent to-[#0a0e14]/50" />
          <div className="absolute inset-0 cyber-grid opacity-25" />
          <div className="absolute inset-0 scanlines opacity-10" />
        </div>
      )}

      {/* PIP SENSOR CAMERA FEED MODE */}
      {mode === 'pip' && (
        <div className="fixed bottom-20 left-6 z-30 w-80 rounded-lg overflow-hidden glass-panel tech-box shadow-2xl border border-hud-cyan/40 transition-all duration-300">
          <div className="px-3 py-1.5 bg-slate-900/90 border-b border-hud-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
              <span className="text-[11px] font-mono font-bold tracking-wider text-hud-cyan">
                CAM_01 // ROVER_TERRAIN
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-hud-cyan-dim text-hud-cyan border border-hud-cyan/30">
                1080p 60FPS
              </span>
              <button
                onClick={() => onModeChange('ambient')}
                className="p-1 hover:text-hud-cyan text-slate-400 transition"
                title="Switch to Ambient Background"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onModeChange('off')}
                className="p-1 hover:text-red-400 text-slate-400 transition"
                title="Disable Video Feed"
              >
                <VideoOff className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="relative aspect-video w-full bg-black">
            <video
              src="/bg_video.mp4"
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-cover"
            />
            <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/60 text-[9px] font-mono text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <Radio className="w-2.5 h-2.5 animate-pulse" /> SENSOR STREAM LIVE
            </div>
          </div>
        </div>
      )}
    </>
  );
};
