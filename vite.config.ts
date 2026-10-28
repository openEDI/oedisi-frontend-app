import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? '/oedisi-frontend-app/' : '/',
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/jupyter': {
        target: 'http://127.0.0.1:8888',
        ws: true,
        changeOrigin: true,
      },
      '/voila': {
        target: 'http://127.0.0.1:8866',
        ws: true,
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
        // Local dev only: simulate nginx's X-Remote-User injection so the
        // multi-user UI works in a plain browser. Override via OEDISI_DEV_USER.
        headers: {
          'X-Remote-User': process.env.OEDISI_DEV_USER || 'dev',
        },
      },
    },
    watch: {
      ignored: ['**/server/runs/**', '**/server/.venv/**'],
    },
  },
})
