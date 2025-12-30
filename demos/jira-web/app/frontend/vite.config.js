/* eslint-disable no-undef */
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // In Docker dev, the frontend runs inside a container and should proxy to the
  // backend service name on the docker network. In local dev, proxy to localhost.
  // Allow override via VITE_PROXY_TARGET for CI/agents.
  const apiTarget =
    (typeof process !== 'undefined' && process.env && process.env.VITE_PROXY_TARGET) ||
    (mode === 'docker' ? 'http://backend:8000' : 'http://localhost:8000');

  return {
    plugins: [react()],
    server: {
      // Vite defaults to 5173; keep this consistent across local dev + Docker dev.
      port: 5173,
      strictPort: true,
      // Required for Docker so the dev server is reachable from outside the container.
      host: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
