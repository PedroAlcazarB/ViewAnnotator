import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { fileURLToPath, URL } from 'node:url'


// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 8080
  }, 
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }, resolve: {
    alias: {
      'fabric': 'fabric/dist/fabric.js'
    }
  }
})