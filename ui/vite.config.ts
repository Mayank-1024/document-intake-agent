import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API runs on :8000 (uv run uvicorn api.main:create_app --factory --port 8000).
// /api/* is proxied there so the browser never needs CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
