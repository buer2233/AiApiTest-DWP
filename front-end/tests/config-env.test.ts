import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { parsePort, resolveFrontendEnv, resolveFrontendServiceUrl, resolvePlaywrightEnv } from '../config/env'

describe('frontend environment config', () => {
  it('falls back to safe numeric defaults for invalid ports', () => {
    expect(parsePort('5174', 5173)).toBe(5174)
    expect(parsePort('not-a-port', 5173)).toBe(5173)
    expect(parsePort('', 5173)).toBe(5173)
  })

  it('derives Vite dev server and API proxy from platform host and ports', () => {
    const env = resolveFrontendEnv({
      PLATFORM_BIND_HOST: '0.0.0.0',
      PLATFORM_PUBLIC_HOST: 'platform.example.test',
      PLATFORM_PUBLIC_SCHEME: 'https',
      BACKEND_HOST_PORT: '18000',
      FRONTEND_HOST_PORT: '15280',
    })

    expect(env.devHost).toBe('0.0.0.0')
    expect(env.devPort).toBe(15280)
    // 本地 Vite 直连的是明文 backend 端口，公开 HTTPS 仅用于外部入口链接。
    expect(env.apiProxyTarget).toBe('http://127.0.0.1:18000')
    expect(env.apiBaseUrl).toBe('/api/v1')
  })

  it('derives Playwright endpoints with the fixed acceptance port', () => {
    const env = resolvePlaywrightEnv({
      PLATFORM_BIND_HOST: '0.0.0.0',
      PLATFORM_PUBLIC_HOST: 'platform.example.test',
      PLATFORM_PUBLIC_SCHEME: 'https',
    })

    expect(env.baseUrl).toBe('http://127.0.0.1:4173')
    expect(env.webServerHost).toBe('0.0.0.0')
    expect(env.webServerPort).toBe(4173)
    expect(env.webServerUrl).toBe('http://127.0.0.1:4173/@vite/client')
    expect(env.permissionOrigin).toBe('http://127.0.0.1:4173')
  })

  it('uses the fixed Compose backend endpoint for Jenkins container tests', () => {
    const env = resolveFrontendEnv({
      CI: 'true',
      PLATFORM_PUBLIC_HOST: '127.0.0.1',
      BACKEND_HOST_PORT: '18000',
    })

    expect(env.apiProxyTarget).toBe('http://backend:8000')
  })

  it('derives the deployed frontend URL for real acceptance specs', () => {
    expect(resolveFrontendServiceUrl({
      PLATFORM_PUBLIC_HOST: 'platform.example.test',
      PLATFORM_PUBLIC_SCHEME: 'https',
      FRONTEND_HOST_PORT: '15173',
    })).toBe('https://platform.example.test:15173')
  })

  it('normalizes wildcard and IPv6 hosts for local and public URLs', () => {
    const local = resolvePlaywrightEnv({
      PLATFORM_BIND_HOST: '::',
      PLATFORM_PUBLIC_HOST: '2001:db8::8',
    })

    expect(local.baseUrl).toBe('http://[::1]:4173')
    expect(resolveFrontendServiceUrl({
      PLATFORM_PUBLIC_HOST: '[2001:db8::8]',
      PLATFORM_PUBLIC_SCHEME: 'https',
      FRONTEND_HOST_PORT: '15173',
    })).toBe('https://[2001:db8::8]:15173')
  })

  it('keeps Stage12 real acceptance URL on the centralized Playwright baseURL', () => {
    const source = readFileSync(
      resolve(__dirname, '..', 'e2e', 'stage12-snapshot-date-jenkins-sync-real-acceptance.spec.ts'),
      'utf-8',
    )

    expect(source).not.toContain('http://127.0.0.1:5173')
    expect(source).toContain('baseURL')
  })
})
