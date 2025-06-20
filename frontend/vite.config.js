import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,               // required for Docker
    port: 5173,
    watch: {
      usePolling: true        // FIXES HMR in Docker on Windows/macOS
    }
  }
})
