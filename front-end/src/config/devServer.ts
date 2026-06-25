/**
 * Vite 开发服务代理配置模块。
 * 本模块把前端本地 `/api` 请求代理到 DRF 后端，避免开发环境出现跨域和 404 问题。
 */

import type { ProxyOptions } from 'vite';

/** 本地 DRF 后端默认地址。 */
export const apiProxyTarget = 'http://127.0.0.1:8000';

/** Vite server.proxy 配置，供 vite.config.ts 和测试复用。 */
export const devServerProxy: Record<string, string | ProxyOptions> = {
  '/api': {
    target: apiProxyTarget,
    changeOrigin: true,
  },
};
