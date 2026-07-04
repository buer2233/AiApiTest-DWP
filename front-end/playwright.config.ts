import { defineConfig, devices } from '@playwright/test'
import { loadEnv } from 'vite'

import { repoRoot, resolvePlaywrightEnv } from './config/env'

const env = resolvePlaywrightEnv(loadEnv(process.env.NODE_ENV || 'test', repoRoot, ''))

export const playwrightPermissionOrigin = env.permissionOrigin

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  reporter: [['list'], ['html', { outputFolder: 'tests/evidence/playwright-report', open: 'never' }]],
  use: {
    baseURL: env.baseUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `node node_modules/vite/bin/vite.js --host ${env.webServerHost} --port ${env.webServerPort}`,
    url: env.webServerUrl,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
