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
    trend_7d: true,
    trend_30d: true,
    jenkins_tasks: false,
  },
}

const failedCase = {
  id: 501,
  node_id: 'test_case/test_gbif_case/test_species.py::test_search_species',
  case_name: 'test_search_species',
  case_summary: '物种查询失败用例',
  error_type: 'AssertionError',
  assertion_text: 'expected status_code == 200',
  execution_status: 'failed',
  display_status: 'failed',
  error_message_summary: 'AssertionError: expected 200, got 500',
  error_message_detail: 'AssertionError: expected 200, got 500; Authorization: Bearer [REDACTED]',
  confirmation_result: '人工确认中',
  actions: { can_update_status: true, can_retry: false },
}

const trendSeries = [
  {
    run_date: '2026-07-02',
    run_type: 'daily_full',
    total_count: 100,
    failed_count: 6,
    skipped_count: 2,
    pass_rate: 0.94,
    duration_seconds: 552,
  },
  {
    run_date: '2026-07-03',
    run_type: 'daily_full',
    total_count: 100,
    failed_count: 3,
    skipped_count: 2,
    pass_rate: 0.97,
    duration_seconds: 548,
  },
]

async function mockStage4P3Api(page: Page) {
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

  await page.route(/\/api\/v1\/module-snapshots(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: [moduleSnapshot],
        meta: { total: 1, page: 1, per_page: 20, total_pages: 1 },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/cases(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: [failedCase],
        meta: { total: 1, page: 1, per_page: 20, total_pages: 1 },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/trend(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          module: {
            snapshot_id: 101,
            module_name: '物种查询模块',
            package_name: 'test_gbif_case',
            environment_name: '模拟测试环境',
          },
          days: 7,
          series: trendSeries,
        },
      },
    })
  })
}

async function waitForDialogSettled(page: Page) {
  await page.waitForFunction(() => {
    const dialogLayers = Array.from(document.querySelectorAll<HTMLElement>('.el-overlay-dialog, .el-dialog'))
    return (
      dialogLayers.length > 0 &&
      dialogLayers.every((layer) => getComputedStyle(layer).opacity === '1') &&
      !document.querySelector('.dialog-fade-enter-active, .dialog-fade-leave-active')
    )
  })
}

test.describe('Stage4 P3 截图证据', () => {
  test('保存用例详情、状态修改、趋势和移动端关键截图', async ({ page }) => {
    await mockStage4P3Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const caseDialog = page.getByRole('dialog', { name: /用例详情/ })
    await caseDialog.getByRole('cell', { name: 'test_search_species', exact: true }).waitFor()
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage4-p3-case-details-desktop-20260704.png',
    })

    await caseDialog.getByRole('button', { name: '修改状态' }).click()
    const statusDialog = page.getByRole('dialog', { name: /修改用例状态/ })
    await statusDialog.getByLabel('修改原因').fill('误报，人工跳过')
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage4-p3-status-update-dialog-20260704.png',
    })
    await statusDialog.getByRole('button', { name: '取消' }).click()
    await caseDialog.getByRole('button', { name: '关闭' }).click()

    await page.getByRole('button', { name: '7天趋势' }).click()
    const trendDialog = page.getByRole('dialog', { name: /近 7 天趋势/ })
    await trendDialog.locator('svg[aria-label="通过率趋势折线图"]').waitFor()
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage4-p3-trend-desktop-20260704.png',
    })
    await trendDialog.getByRole('button', { name: '关闭' }).click()

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    await page
      .getByRole('dialog', { name: /用例详情/ })
      .getByLabel('移动端用例详情列表')
      .getByText('test_search_species', { exact: true })
      .waitFor()
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage4-p3-case-details-mobile-20260704.png',
    })
  })
})
