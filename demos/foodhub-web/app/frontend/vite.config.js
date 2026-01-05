import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // In dev, proxy to local backend. In Docker, nginx handles proxy.
  // Use Vite's loadEnv to avoid relying on Node globals like `process`.
  const env = loadEnv(mode, '.', 'VITE_');
  const apiTarget = env.VITE_DEV_API_PROXY_TARGET || 'http://localhost:8083';

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 8000,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true
        }
      }
    }
  };
});
