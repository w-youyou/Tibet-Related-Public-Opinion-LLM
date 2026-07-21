import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue()
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    port: 3000,   // 使用3000端口
    strictPort: false,
    host: true,   // 监听所有网络接口
    
    // ======== 🚀 添加代理配置以解决 CORS 问题 ========
    proxy: {
      // 匹配所有以 '/api' 开头的请求路径
      '/api': {
        // 将请求转发的目标地址设置为你的 Django 后端服务地址
        target: 'http://127.0.0.1:8000', 
        // 允许跨域
        changeOrigin: true,
        // (可选) 路径重写：
        // 如果你的 Django 后端路由就是以 /api 开头的 (例如: /api/auth/login/)，则不需要 pathRewrite。
        // 根据你的描述，你的 API 路径是 /api/auth/login/，所以我们不需要重写。
      }
    }
    // ===================================================
  },
})
