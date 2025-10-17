import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
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
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/uploads': {
        target: 'http://localhost:8000',
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