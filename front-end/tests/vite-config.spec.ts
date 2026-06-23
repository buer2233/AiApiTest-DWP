import { describe, expect, it } from 'vitest';

import { apiProxyTarget, devServerProxy } from '../src/config/devServer';

describe('vite dev server config', () => {
  it('proxies API requests to the local DRF backend', () => {
    expect(apiProxyTarget).toBe('http://127.0.0.1:8000');
    expect(devServerProxy['/api']).toMatchObject({
      target: apiProxyTarget,
      changeOrigin: true,
    });
  });
});
