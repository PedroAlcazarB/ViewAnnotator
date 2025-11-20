import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { fileURLToPath, URL } from 'node:url'


// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://backend:5000',
        changeOrigin: true,
        secure: false
      }
    }
  }, 
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'fabric': 'fabric/dist/fabric.js'
    }
  }
})