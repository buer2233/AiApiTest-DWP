import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const configDir = dirname(fileURLToPath(import.meta.url))
export const frontendRoot = resolve(configDir, '..')
export const repoRoot = resolve(frontendRoot, '..')

type EnvRecord = Record<string, string | undefined>

export const API_BASE_PATH = '/api/v1'
export const PLAYWRIGHT_PORT = 4173

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

function resolvePlatformHosts(env: EnvRecord): {
  bindHost: string
  publicHost: string
} {
  const bindHost = env.PLATFORM_BIND_HOST || '127.0.0.1'
  return {
    bindHost,
    publicHost: env.PLATFORM_PUBLIC_HOST || bindHost,
  }
}

function stripIpv6Brackets(host: string): string {
  return host.startsWith('[') && host.endsWith(']') ? host.slice(1, -1) : host
}

function formatUrlHost(host: string): string {
  const normalized = stripIpv6Brackets(host)
  return normalized.includes(':') ? `[${normalized}]` : normalized
}

function resolveLocalConnectHost(bindHost: string): string {
  const normalized = stripIpv6Brackets(bindHost)
  if (normalized === '0.0.0.0') return '127.0.0.1'
  if (normalized === '::') return '::1'
  return normalized
}

export function resolveFrontendEnv(env: EnvRecord): FrontendEnv {
  const { bindHost } = resolvePlatformHosts(env)
  const connectHost = formatUrlHost(resolveLocalConnectHost(bindHost))
  const backendPort = parsePort(env.BACKEND_HOST_PORT, 8000)
  const apiProxyTarget = env.CI?.toLowerCase() === 'true'
    ? 'http://backend:8000'
    : `http://${connectHost}:${backendPort}`
  return {
    devHost: bindHost,
    devPort: parsePort(env.FRONTEND_HOST_PORT, 5173),
    // Vite 直连宿主机暴露的 Gunicorn 端口，该端口本身不终止 TLS。
    apiProxyTarget,
    apiBaseUrl: API_BASE_PATH,
  }
}

export function resolveFrontendServiceUrl(env: EnvRecord): string {
  const { publicHost } = resolvePlatformHosts(env)
  const scheme = env.PLATFORM_PUBLIC_SCHEME?.toLowerCase() === 'https' ? 'https' : 'http'
  const port = parsePort(env.FRONTEND_HOST_PORT, 5173)
  return `${scheme}://${formatUrlHost(publicHost)}:${port}`
}

export function resolvePlaywrightEnv(env: EnvRecord): PlaywrightEnv {
  const { bindHost } = resolvePlatformHosts(env)
  const webServerHost = bindHost
  const webServerPort = PLAYWRIGHT_PORT
  // Playwright 启动的 Vite webServer 是明文 HTTP，不能复用外部 HTTPS 协议。
  const baseUrl = `http://${formatUrlHost(resolveLocalConnectHost(bindHost))}:${webServerPort}`
  return {
    baseUrl,
    webServerHost,
    webServerPort,
    webServerUrl: `${baseUrl}/@vite/client`,
    permissionOrigin: baseUrl,
  }
}
