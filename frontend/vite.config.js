import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Redirige les appels /api/* vers le backend FastAPI
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite:   (p) => p.replace(/^\/api/, ''),
        changeOrigin: true
      }
    }
  }
})
