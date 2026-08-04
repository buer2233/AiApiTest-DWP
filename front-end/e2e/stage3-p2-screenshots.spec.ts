import { test, type Page } from '@playwright/test'

const testEnvironment = {
  id: 1,
  env_key: 'mock-example',
  env_name: '模拟测试环境',
  base_url: 'https://example.test/api',
}

const moduleSnapshot = {
  id: 101,
  completed_at: '2026-07-04T09:12:00+08:00',
  package_name: 'test_gbif_case',
  module_name: '物种查询模块',
  module_dev: '张三',
  module_test: '李四',
  total_count: 100,
  failed_count: 4,
  passed_count: 94,
  skipped_count: 2,
  pass_rate: 0.96,
  duration_seconds: 33.5,
  actions: {
    failed_rerun: false,
    module_rerun: false,
    trend_7d: false,
    trend_30d: false,
    jenkins_tasks: false,
  },
}

async function mockStage3P2Api(page: Page) {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          id: 1,
          username: 'admin_user',
          display_name: '平台管理员',
          role: 'admin',
          permissions: ['profile:read'],
        },
      },
    })
  })

  await page.route(/\/api\/v1\/test-environments(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, json: { data: [testEnvironment] } })
  })

  await page.route(/\/api\/v1\/test-environments\/\d+\/summary(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          environment: testEnvironment,
          started_at: '2026-07-04T09:00:00+08:00',
          finished_at: '2026-07-04T09:12:00+08:00',
          duration_seconds: 720,
          total_count: 100,
          failed_count: 4,
          passed_count: 94,
          skipped_count: 2,
          pass_rate: 0.96,
          actions: { generate_report: true },
        },
      },
    })
  })

  await page.route('**/api/v1/module-snapshots**', async (route) => {
    const url = new URL(route.request().url())
    const pageNumber = Number(url.searchParams.get('page') ?? '1')
    await route.fulfill({
      status: 200,
      json: {
        data: [moduleSnapshot],
        meta: { total: 1, page: pageNumber, per_page: 20, total_pages: 1 },
      },
    })
  })
}

test.describe('Stage3 P2 截图证据', () => {
  test('保存环境页和模块页关键截图', async ({ page }) => {
    test.setTimeout(60_000)
    await mockStage3P2Api(page)

    await page.goto('/environments')
    await page.getByRole('heading', { name: '环境通过率' }).waitFor()
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage3-p2-environments-desktop-20260704.png',
      fullPage: true,
    })

    await page.goto('/modules?environment_id=1')
    await page.getByRole('heading', { name: '模块通过率' }).waitFor()
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage3-p2-modules-desktop-20260704.png',
      fullPage: true,
    })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/modules?environment_id=1')
    await page.getByRole('heading', { name: '模块通过率' }).waitFor()
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage3-p2-modules-mobile-20260704.png',
      fullPage: true,
    })
  })
})
