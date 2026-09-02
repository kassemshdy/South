import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// In Docker Compose the API is reachable as http://api:8000; locally it is on
// 127.0.0.1. The proxy target is therefore configurable.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    // The API and uploaded media are proxied so the browser stays on one
    // origin in development — no CORS juggling, and cookies/paths behave as
    // they do in the single-container production layout.
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/media': { target: apiTarget, changeOrigin: true },
      '/sitemap.xml': { target: apiTarget, changeOrigin: true },
      '/robots.txt': { target: apiTarget, changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
