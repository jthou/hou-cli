/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// 从项目根 .env 读取后端端口，与 Makefile 一致（WEB_PORT 优先，其次 BACKEND_PORT）
function getBackendPort() {
  const envPath = path.resolve(__dirname, '../../.env')
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8')
    const m = content.match(/^WEB_PORT=(\d+)/m) || content.match(/^BACKEND_PORT=(\d+)/m)
    if (m) return m[1]
  }
  return '8081'
}
const API_PORT = getBackendPort()
const API_TARGET = `http://127.0.0.1:${API_PORT}`

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: '../web/dist',
    emptyDir: true,
  },
  server: {
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        timeout: 0,  // 禁用超时，避免 SSE 流被提前关闭
      },
      '/ws': { target: API_TARGET.replace('http', 'ws'), ws: true },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.{js,ts,mjs}'],
  },
})
