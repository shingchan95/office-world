import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/design/',
  plugins: [react()],
  build: {
    // Don't preload lazy chunks - lets the spinner show before three.js downloads
    modulePreload: false,
    rollupOptions: {
      output: {
        manualChunks: (id: string) => {
          if (id.includes('node_modules/three')) return 'three';
          if (id.includes('react-three/fiber')) return 'fiber';
          if (id.includes('react-three/drei')) return 'drei';
          if (id.includes('zustand') || id.includes('immer')) return 'state';
        },
      } as any,
    },
    chunkSizeWarningLimit: 800,
  },
  server: {
    host: true,
    port: 5173,
  },
});
