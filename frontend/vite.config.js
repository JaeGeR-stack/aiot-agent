
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    // 允许当前 Cloudflare 临时公网域名访问
    allowedHosts: [
      'americans-congratulations-opened-triangle.trycloudflare.com',
    ],

    proxy: {
      // ESP32-S3 真实传感器接口：保留 /api/sensor
      '/api/sensor': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      // 原有设备接口：去掉 /api 前缀
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
