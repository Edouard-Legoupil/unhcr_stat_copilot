import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/report': 'http://127.0.0.1:8000',
      '/history': 'http://127.0.0.1:8000',
      '/quarto': 'http://127.0.0.1:8000',
      '/mcp': 'http://127.0.0.1:8000',
      '/analysis-config': 'http://127.0.0.1:8000'
    },
    // Use polling to avoid file watcher limits
    watch: {
      usePolling: true,
      interval: 1000
    }
  }
})
