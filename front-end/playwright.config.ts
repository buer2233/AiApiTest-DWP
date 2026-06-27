import { defineConfig, devices } from "@playwright/test";

// Playwright E2E：构建并以 preview 起静态服务；用例内通过 page.route mock 后端 API，
// 不依赖真实 Django 服务，保证可重复与隔离。
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run preview",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 180000,
  },
});
