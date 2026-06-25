/**
 * Vite 前端工程配置。
 * 本文件配置 Vue 插件、开发代理、路径别名和 Vitest 测试环境。
 */

import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

import { devServerProxy } from './src/config/devServer';

export default defineConfig({
  plugins: [vue()],
  server: {
    // 开发环境把 /api 代理到 DRF 后端，前端代码无需写死后端地址。
    proxy: devServerProxy,
  },
  resolve: {
    alias: {
      // 使用 @ 指向 src，保持业务代码 import 路径稳定。
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // Vue Test Utils 组件测试需要浏览器 DOM 能力，使用 jsdom 环境。
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
});
