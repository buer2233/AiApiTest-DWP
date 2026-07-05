import { test, type Page } from '@playwright/test'

const testEnvironment = {
  id: 1,
  env_key: 'mock-example',
  env_name: '模拟测试环境',
  base_url: 'https://example.test/api',
}

const moduleSnapshot = {
  id: 101,
  completed_at: '2026-07-05T10:30:00+08:00',
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
    failed_rerun: true,
    module_rerun: true,
    trend_7d: true,
    trend_30d: true,
    jenkins_tasks: true,
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
  actions: { can_update_status: true, can_retry: true },
}

const jenkinsTasks = [
  {
    id: 302,
    task_type: 'failed_rerun',
    job_name: '失败重试',
    environment_url: testEnvironment.base_url,
    status: 'running',
    triggered_by: '平台管理员',
    started_at: '2026-07-05T10:00:00+08:00',
    finished_at: null,
    jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Failed-Rerun/302/',
    allure_report_url: null,
    actions: { cancel: true, view_report: false, view_jenkins_task: true },
  },
  {
    id: 303,
    task_type: 'module_rerun',
    job_name: '模块重试',
    environment_url: testEnvironment.base_url,
    status: 'test_failed',
    triggered_by: '平台管理员',
    started_at: '2026-07-05T09:00:00+08:00',
    finished_at: '2026-07-05T09:10:00+08:00',
    jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Module-Rerun/303/',
    allure_report_url: 'https://allure.example.test/reports/303/index.html',
    actions: { cancel: false, view_report: true, view_jenkins_task: true },
  },
]

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

async function mockStage6P5Api(page: Page) {
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

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/jenkins-tasks(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: jenkinsTasks,
        meta: { total: 2, page: 1, per_page: 20, total_pages: 1 },
      },
    })
  })
}

test.describe('Stage6 P5 Jenkins 前端截图证据', () => {
  test('保存模块操作、用例重试和 Jenkins 任务弹窗截图', async ({ page }) => {
    await mockStage6P5Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('heading', { name: '模块通过率' }).waitFor()
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage6-p5-modules-actions-desktop-20260705.png',
      fullPage: true,
    })

    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const caseDialog = page.getByRole('dialog', { name: /用例详情/ })
    await caseDialog.getByRole('checkbox', { name: '选择 test_search_species' }).waitFor()
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage6-p5-case-retry-dialog-20260705.png',
    })
    await caseDialog.getByRole('button', { name: '关闭' }).click()

    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    const taskDialog = page.getByRole('dialog', { name: /Jenkins 任务/ })
    await taskDialog.getByRole('cell', { name: '运行中' }).waitFor()
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage6-p5-jenkins-tasks-desktop-20260705.png',
    })
    await taskDialog.getByRole('button', { name: '关闭' }).click()

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    await page.getByRole('dialog', { name: /Jenkins 任务/ }).getByLabel('移动端 Jenkins 任务列表').waitFor()
    await waitForDialogSettled(page)
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage6-p5-jenkins-tasks-mobile-20260705.png',
    })
  })
})
