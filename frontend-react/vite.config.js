import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const proxyTarget = process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000'
const envAllowedHosts = (process.env.VITE_ALLOWED_HOSTS || '')
  .split(',')
  .map((h) => h.trim())
  .filter(Boolean)
const defaultAllowedHosts = ['localhost', '127.0.0.1', '.ngrok-free.dev', '.ngrok.dev', '.ngrok.app']
const allowedHosts = [...new Set([...defaultAllowedHosts, ...envAllowedHosts])]

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/healthz': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/readyz': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/mcp': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
