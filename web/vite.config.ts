/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// GitHub Pages project site: https://dsjwong.github.io/hkia-delay-predictor/
export default defineConfig({
  base: '/hkia-delay-predictor/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  worker: { format: 'es' }, // maplibre's worker is an ES module (imports maplibre-gl-shared)
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (/node_modules\/(maplibre-gl|@deck\.gl|@luma\.gl|@math\.gl|@loaders\.gl|@probe\.gl)\//.test(id)) return "map"
          if (/node_modules\/(recharts|d3-|victory-vendor|@reduxjs|redux|immer|reselect)/.test(id)) return "charts"
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
