/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        hud: {
          bg: '#0a0e14',
          'bg-card': 'rgba(16, 22, 32, 0.85)',
          'bg-panel': 'rgba(12, 17, 26, 0.88)',
          'border': 'rgba(56, 189, 248, 0.25)',
          'border-bright': 'rgba(56, 189, 248, 0.5)',
          cyan: '#38bdf8', // Tactical Ice Sky Cyan (matching video sky & vehicle sensors)
          'cyan-dim': 'rgba(56, 189, 248, 0.15)',
          emerald: '#10b981', // Natural Terrain Emerald (matching video foliage)
          'emerald-dim': 'rgba(16, 185, 129, 0.15)',
          amber: '#f59e0b', // Curb & Terrain Hazard Gold
          'amber-dim': 'rgba(245, 158, 11, 0.15)',
          crimson: '#f43f5e',
          'crimson-dim': 'rgba(244, 63, 94, 0.15)',
          purple: '#a855f7',
          'purple-dim': 'rgba(168, 85, 247, 0.15)',
          slate: '#64748b',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        display: ['Outfit', '"Plus Jakarta Sans"', 'sans-serif'],
      },
      boxShadow: {
        'cyan-glow': '0 0 25px rgba(56, 189, 248, 0.3)',
        'cyan-glow-sm': '0 0 12px rgba(56, 189, 248, 0.2)',
        'emerald-glow': '0 0 25px rgba(16, 185, 129, 0.3)',
        'emerald-glow-sm': '0 0 12px rgba(16, 185, 129, 0.2)',
        'amber-glow': '0 0 20px rgba(245, 158, 11, 0.25)',
        'panel': '0 12px 36px 0 rgba(0, 0, 0, 0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'radar-sweep': 'radarSweep 4s linear infinite',
        'scanline': 'scanline 8s linear infinite',
      },
      keyframes: {
        radarSweep: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' },
        }
      }
    },
  },
  plugins: [],
}
