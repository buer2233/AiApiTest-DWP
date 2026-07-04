import { describe, expect, it } from 'vitest'

import { parsePort, resolveFrontendEnv, resolvePlaywrightEnv } from '../config/env'

describe('frontend environment config', () => {
  it('falls back to safe numeric defaults for invalid ports', () => {
    expect(parsePort('5174', 5173)).toBe(5174)
    expect(parsePort('not-a-port', 5173)).toBe(5173)
    expect(parsePort('', 5173)).toBe(5173)
  })

  it('resolves Vite dev server values from root environment variables', () => {
    const env = resolveFrontendEnv({
      FRONTEND_DEV_HOST: '0.0.0.0',
      FRONTEND_DEV_PORT: '5280',
      FRONTEND_DEV_API_PROXY_TARGET: 'http://backend:8000',
      VITE_API_BASE_URL: '/api/v1',
    })

    expect(env.devHost).toBe('0.0.0.0')
    expect(env.devPort).toBe(5280)
    expect(env.apiProxyTarget).toBe('http://backend:8000')
    expect(env.apiBaseUrl).toBe('/api/v1')
  })

  it('keeps Playwright baseURL, webServer URL and permission origin aligned', () => {
    const env = resolvePlaywrightEnv({
      PLAYWRIGHT_WEB_SERVER_HOST: '127.0.0.1',
      PLAYWRIGHT_WEB_SERVER_PORT: '4300',
    })

    expect(env.baseUrl).toBe('http://127.0.0.1:4300')
    expect(env.webServerUrl).toBe('http://127.0.0.1:4300/@vite/client')
    expect(env.permissionOrigin).toBe('http://127.0.0.1:4300')
  })
})
