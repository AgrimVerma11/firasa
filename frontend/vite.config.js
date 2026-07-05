import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During development the API runs separately on port 5001. We proxy /api to it
// so the browser talks to a single origin and we avoid CORS headaches locally.
// In production VITE_API_BASE_URL points the client straight at the deployed API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
});
