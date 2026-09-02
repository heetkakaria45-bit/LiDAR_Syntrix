import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/video.mp4': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/assets/video.mp4': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../src/visualization/web',
    emptyOutDir: false,
    chunkSizeWarningLimit: 1500,
  },
});
