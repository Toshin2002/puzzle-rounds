import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, Vite runs on :5173 and forwards API + WebSocket traffic to FastAPI on :8000,
// so the browser only ever talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
