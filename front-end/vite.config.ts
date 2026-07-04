import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

import { resolveFrontendEnv, repoRoot } from './config/env'

export default defineConfig(({ mode }) => {
  const env = resolveFrontendEnv(loadEnv(mode, repoRoot, ''))

  return {
    envDir: repoRoot,
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: env.devHost,
      port: env.devPort,
      proxy: {
        // 本地开发代理到 DRF，容器化或网关部署仍可通过 VITE_API_BASE_URL 使用统一入口。
        '/api': {
          target: env.apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      include: ['tests/**/*.test.ts', 'src/**/*.{test,spec}.ts'],
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
  }
})
