import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Port from environment - Docker will set these
  const port = Number(env.VITE_PORT || env.PORT || 3001);
  // Backend port from environment - allows dynamic configuration
  const backendPort = env.VITE_BACKEND_PORT || '8080';
  const backendTarget = env.VITE_API_PROXY_TARGET || `http://localhost:${backendPort}`;

  return {
    plugins: [react()],
    server: {
      port: Number.isFinite(port) ? port : 3001,
      strictPort: false,
      // Bind to all interfaces for Docker/host access
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true
        }
      }
    },
    preview: {
      port: Number(env.VITE_PREVIEW_PORT || port),
      host: '0.0.0.0'
    }
  };
});
