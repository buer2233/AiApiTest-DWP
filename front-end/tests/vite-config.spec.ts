/**
 * Vite 开发代理配置测试。
 * 验证前端 `/api` 请求会代理到本地 DRF 后端，防止登录请求落到 Vite 自身返回 404。
 */

import { describe, expect, it } from 'vitest';

import { apiProxyTarget, devServerProxy } from '../src/config/devServer';

describe('vite dev server config', () => {
  it('proxies API requests to the local DRF backend', () => {
    /** 代理目标必须和本地后端开发服务端口保持一致。 */
    expect(apiProxyTarget).toBe('http://127.0.0.1:8000');
    expect(devServerProxy['/api']).toMatchObject({
      target: apiProxyTarget,
      changeOrigin: true,
    });
  });
});
