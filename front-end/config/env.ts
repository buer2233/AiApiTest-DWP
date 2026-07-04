import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const configDir = dirname(fileURLToPath(import.meta.url))
export const frontendRoot = resolve(configDir, '..')
export const repoRoot = resolve(frontendRoot, '..')

type EnvRecord = Record<string, string | undefined>

export interface FrontendEnv {
  devHost: string
  devPort: number
  apiProxyTarget: string
  apiBaseUrl: string
}

export interface PlaywrightEnv {
  baseUrl: string
  webServerHost: string
  webServerPort: number
  webServerUrl: string
  permissionOrigin: string
}

export function parsePort(value: string | undefined, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
    return fallback
  }
  return parsed
}

export function resolveFrontendEnv(env: EnvRecord): FrontendEnv {
  return {
    devHost: env.FRONTEND_DEV_HOST || '127.0.0.1',
    devPort: parsePort(env.FRONTEND_DEV_PORT, 5173),
    apiProxyTarget: env.FRONTEND_DEV_API_PROXY_TARGET || env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8000',
    apiBaseUrl: env.VITE_API_BASE_URL || '/api/v1',
  }
}

export function resolvePlaywrightEnv(env: EnvRecord): PlaywrightEnv {
  const webServerHost = env.PLAYWRIGHT_WEB_SERVER_HOST || env.FRONTEND_DEV_HOST || '127.0.0.1'
  const webServerPort = parsePort(env.PLAYWRIGHT_WEB_SERVER_PORT || env.FRONTEND_DEV_PORT, 4173)
  const defaultBaseUrl = `http://${webServerHost}:${webServerPort}`
  const baseUrl = env.PLAYWRIGHT_BASE_URL || defaultBaseUrl
  return {
    baseUrl,
    webServerHost,
    webServerPort,
    webServerUrl: `${baseUrl}/@vite/client`,
    permissionOrigin: baseUrl,
  }
}
