import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Use 127.0.0.1 explicitly — Node 18 resolves "localhost" to IPv6 (::1)
        // which fails if the backend only listens on IPv4
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
