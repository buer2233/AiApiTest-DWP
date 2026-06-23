import type { ProxyOptions } from 'vite';

export const apiProxyTarget = 'http://127.0.0.1:8000';

export const devServerProxy: Record<string, string | ProxyOptions> = {
  '/api': {
    target: apiProxyTarget,
    changeOrigin: true,
  },
};
