import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [
    react(),
    tsconfigPaths(), // reads "@/*" alias from tsconfig.json automatically
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/jupyter': {
        target: 'http://127.0.0.1:8888',
        changeOrigin: true,
        ws: true,
        // No path rewrite — JupyterLab uses base_url=/jupyter/
        // so all its requests already have the /jupyter prefix
      },
    },
  },
})
