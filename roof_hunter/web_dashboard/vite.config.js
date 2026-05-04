import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Production on GitHub Pages (project site): set VITE_BASE_PATH=/repo-name/
// e.g. https://workofarttattoo.github.io/roof_hunter/ → VITE_BASE_PATH=/roof_hunter/
const base = process.env.VITE_BASE_PATH || '/'

// https://vite.dev/config/
export default defineConfig({
  base,
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true
    }
  }
})
