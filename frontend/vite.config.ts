// 类型声明（Node.js 环境）
declare const process: {
  env: Record<string, string | undefined>
}

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// @ts-ignore - Node.js 内置模块，运行时可用
import { resolve } from 'path'
// @ts-ignore - Node.js 内置模块，运行时可用
import { readFileSync, existsSync } from 'fs'
// @ts-ignore - Node.js 内置模块，运行时可用
import { fileURLToPath } from 'url'

// 获取当前文件目录（兼容 ES 模块）
// @ts-ignore - import.meta.url 在 Vite 中可用
const __filename = fileURLToPath(import.meta.url)
const __dirname = resolve(__filename, '..')

// 加载统一服务配置
function loadServicesConfig() {
  try {
    const configPath = resolve(__dirname, '../config/services.json')
    if (existsSync(configPath)) {
      const raw = readFileSync(configPath, 'utf-8')
      return JSON.parse(raw)
    }
  } catch (error) {
    console.warn('⚠️  无法加载统一配置文件，使用默认配置:', error)
  }
  // 默认配置
  return {
    frontend: { port: 5173, host: 'localhost' },
    backend: { port: 8008, host: '0.0.0.0' }
  }
}

const servicesConfig = loadServicesConfig()

// 获取配置值（优先级：环境变量 > 配置文件 > 默认值）
const frontendPort = process.env.FRONTEND_PORT 
  ? parseInt(process.env.FRONTEND_PORT) 
  : servicesConfig.frontend.port

const backendPort = process.env.BACKEND_PORT 
  ? parseInt(process.env.BACKEND_PORT) 
  : servicesConfig.backend.port

const backendHost = process.env.BACKEND_HOST || servicesConfig.backend.host || 'localhost'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: frontendPort,
    host: true, // 保持这个设置，允许外部访问

    // --- 以下是为您添加的核心配置 ---

    // 1. 允许您的域名访问 Vite 开发服务器
    allowedHosts: ['www.digital-jiageng.xyz'],

    // 2. 确保在 HTTP 反向代理下热更新正常工作
    hmr: {
      protocol: 'ws', // 因为您是 HTTP，所以这里必须是 'ws'
      host: 'www.digital-jiageng.xyz',
    },

    // --- 核心配置结束 ---

    proxy: {
      '/api': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true,
        secure: false,
      },
      '/uploads': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    // ... 您的构建配置保持不变 ...
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'router': ['react-router-dom'],
          'antd': ['antd', '@ant-design/icons'],
          'utils': ['axios', 'dayjs', 'ahooks'],
        },
      },
    },
  },
})