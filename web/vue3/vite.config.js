import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import viteCompression from 'vite-plugin-compression'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    // Gzip 压缩
    viteCompression({
      algorithm: 'gzip',
      threshold: 1024,        // 仅压缩 >1KB 的文件
      ext: '.gz',
    }),
    // Brotli 压缩
    viteCompression({
      algorithm: 'brotliCompress',
      threshold: 1024,
      ext: '.br',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: '../../dist',
    emptyOutDir: true,
    // 生产环境关闭 source map，减小体积
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // echarts 按需导入后体积已大幅减少，独立 chunk
          'echarts': ['echarts/core'],
          // Vue 生态独立
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // axios 独立
          'axios': ['axios'],
        },
        // 带 hash 的 chunk 文件名，便于长期缓存
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      }
    },
    // 警告阈值不变
    chunkSizeWarningLimit: 600
  }
})
