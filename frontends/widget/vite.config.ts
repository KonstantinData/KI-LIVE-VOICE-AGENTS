import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Vite Config für das Chat-Widget.
 * Baut als IIFE-Bundle (ein JS + ein CSS File) — einbettbar auf jeder Website.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      react: 'preact/compat',
      'react-dom': 'preact/compat',
      'react-dom/client': 'preact/compat/client',
    },
  },
  build: {
    lib: {
      entry: 'src/main.tsx',
      name: 'KITeamWidget',
      fileName: 'loader',
      formats: ['iife'],
    },
    rollupOptions: {
      // UI runtime is bundled so customer websites do not need any dependency.
      external: [],
    },
    outDir: 'dist',
    cssCodeSplit: false,
  },
});
