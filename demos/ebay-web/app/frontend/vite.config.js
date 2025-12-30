import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Use a writable cache dir in CI/container environments.
  cacheDir: process.env.VITE_CACHE_DIR || 'node_modules/.vite',

  server: {
    host: true,
    // Allow access from other containers on the docker network (e.g. openenv health checks).
    allowedHosts: ['frontend', 'localhost', '127.0.0.1'],
    // Deterministic dev server port for QA. Override with VITE_PORT if needed.
    // Default is 5173 to match Vite conventions and docker-compose.dev.yml.
    port: Number(process.env.VITE_PORT) || 5173,
    strictPort: true,
    // When running Vite inside Docker, HMR needs to connect back to the host browser.
    // These env vars are set in docker-compose.dev.yml.
    hmr: {
      host: process.env.VITE_HMR_HOST || undefined,
      clientPort: process.env.VITE_HMR_CLIENT_PORT ? Number(process.env.VITE_HMR_CLIENT_PORT) : undefined,
    },
    proxy: {
      '/api': {
        // Backend base URL; override via VITE_PROXY_TARGET (e.g. http://localhost:8000)
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: Number(process.env.VITE_PORT) || 5173,
    strictPort: true,
  },
});
