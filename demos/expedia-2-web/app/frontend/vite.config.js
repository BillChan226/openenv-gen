import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(() => {
  // In docker-compose the backend is published on host :3000 but listens on :8082 internally.
  // Use VITE_API_PROXY_TARGET when running in containers; fall back to a sensible local default.
  const apiTarget =
    process.env.VITE_API_PROXY_TARGET ||
    process.env.VITE_API_BASE_URL ||
    // Local dev default: memory backend runs on :8082
    'http://localhost:8082';

  return {
    plugins: [react()],
    server: {
      port: 3001,
      strictPort: true,
      proxy: {
        // Proxy ONLY API calls. This prevents SPA routes like /hotels from being
        // forwarded to the backend when users deep-link/refresh.
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    }
  };
});
