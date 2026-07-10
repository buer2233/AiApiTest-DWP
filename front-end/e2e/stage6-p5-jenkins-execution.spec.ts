import { expect, test, type Page } from '@playwright/test'

const testEnvironment = {
  id: 1,
  env_key: 'mock-example',
  env_name: '模拟测试环境',
  base_url: 'https://example.test/api',
}

const adminUser = {
  id: 1,
  username: 'admin_user',
  display_name: '平台管理员',
  role: 'admin',
  permissions: ['profile:read'],
}

const memberUser = {
  ...adminUser,
  id: 2,
  username: 'member_user',
  display_name: '普通成员',
  role: 'member',
}

const enabledActions = {
  failed_rerun: true,
  module_rerun: true,
  trend_7d: true,
  trend_30d: true,
  jenkins_tasks: true,
}

const memberActions = {
  failed_rerun: false,
  module_rerun: false,
  trend_7d: true,
  trend_30d: true,
  jenkins_tasks: true,
}

const originalModuleSnapshot = {
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
  actions: enabledActions,
}

const moduleRerunSnapshot = {
  ...originalModuleSnapshot,
  completed_at: '2026-07-05T10:30:00+08:00',
  failed_count: 2,
  passed_count: 96,
  pass_rate: 0.98,
  duration_seconds: 41,
}

const retryableFailedCase = {
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

const lockedFailedCase = {
  ...retryableFailedCase,
  id: 502,
  node_id: 'test_case/test_gbif_case/test_species.py::test_locked_species',
  case_name: 'test_locked_species',
  actions: { can_update_status: true, can_retry: false },
}

const skippedCase = {
  ...retryableFailedCase,
  id: 503,
  node_id: 'test_case/test_gbif_case/test_species.py::test_legacy_species',
  case_name: 'test_legacy_species',
  display_status: 'skipped',
  confirmation_result: '历史原因',
  actions: { can_update_status: true, can_retry: false },
}

const queuedTask = {
  id: 301,
  task_type: 'failed_rerun',
  job_name: '失败重试',
  environment_url: testEnvironment.base_url,
  status: 'queued',
  triggered_by: '平台管理员',
  started_at: null,
  finished_at: null,
  jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Failed-Rerun/301/',
  allure_report_url: null,
  actions: { cancel: true, view_report: false, view_jenkins_task: true },
}

const runningTask = {
  ...queuedTask,
  id: 302,
  status: 'running',
  started_at: '2026-07-05T10:00:00+08:00',
  jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Failed-Rerun/302/',
}

const reportTask = {
  ...queuedTask,
  id: 303,
  task_type: 'module_rerun',
  job_name: '模块重试',
  status: 'test_failed',
  started_at: '2026-07-05T09:00:00+08:00',
  finished_at: '2026-07-05T09:10:00+08:00',
  jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Module-Rerun/303/',
  allure_report_url: 'https://allure.example.test/reports/303/index.html',
  actions: { cancel: false, view_report: true, view_jenkins_task: true },
}

type MockOptions = {
  role?: 'admin' | 'member'
  lockedRetry?: boolean
  pollToSuccess?: boolean
}

async function mockStage6P5Api(page: Page, options: MockOptions = {}) {
  const failedRetryPayloads: unknown[] = []
  const moduleRerunPayloads: unknown[] = []
  const cancelRequests: number[] = []
  const syncRequests: number[] = []
  const taskListRequests: URL[] = []
  let moduleSnapshot = {
    ...originalModuleSnapshot,
    actions: options.role === 'member' ? memberActions : enabledActions,
  }
  let tasks = [runningTask, reportTask]
  const role = options.role ?? 'admin'

  await page.context().route('https://jenkins.example.test/**', async (route) => {
    await route.fulfill({ status: 200, body: '<html><title>Jenkins</title></html>' })
  })
  await page.context().route('https://allure.example.test/**', async (route) => {
    await route.fulfill({ status: 200, body: '<html><title>Allure</title></html>' })
  })

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { data: role === 'admin' ? adminUser : memberUser } })
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
    const requestUrl = new URL(route.request().url())
    const status = requestUrl.searchParams.get('status') ?? 'failed'
    await route.fulfill({
      status: 200,
      json: {
        data: status === 'skipped' ? [skippedCase] : [retryableFailedCase, lockedFailedCase],
        meta: { total: status === 'skipped' ? 1 : 2, page: 1, per_page: 20, total_pages: 1 },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/failed-case-retries$/, async (route) => {
    failedRetryPayloads.push(route.request().postDataJSON())
    if (options.lockedRetry) {
      await route.fulfill({
        status: 409,
        json: { error: { code: 'module_execution_locked', message: '本模块已经有真正执行的重试!' } },
      })
      return
    }
    await route.fulfill({ status: 202, json: { data: queuedTask } })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/module-reruns$/, async (route) => {
    moduleRerunPayloads.push(route.request().postDataJSON())
    moduleSnapshot = moduleRerunSnapshot
    await route.fulfill({ status: 202, json: { data: { ...queuedTask, id: 304, task_type: 'module_rerun', job_name: '模块重试' } } })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/jenkins-tasks(?:\?.*)?$/, async (route) => {
    taskListRequests.push(new URL(route.request().url()))
    if (options.pollToSuccess && taskListRequests.length > 1) {
      tasks = [{ ...runningTask, status: 'success', actions: { ...runningTask.actions, cancel: false } }, reportTask]
    }
    await route.fulfill({
      status: 200,
      json: { data: tasks, meta: { total: tasks.length, page: 1, per_page: 20, total_pages: 1 } },
    })
  })

  await page.route(/\/api\/v1\/jenkins-tasks\/\d+\/cancel$/, async (route) => {
    const taskId = Number(route.request().url().match(/jenkins-tasks\/(\d+)\/cancel/)?.[1])
    cancelRequests.push(taskId)
    tasks = tasks.map((task) =>
      task.id === taskId ? { ...task, status: 'canceling', actions: { ...task.actions, cancel: false } } : task,
    )
    await route.fulfill({ status: 202, json: { data: tasks.find((task) => task.id === taskId) } })
  })

  await page.route(/\/api\/v1\/jenkins-tasks\/\d+\/sync$/, async (route) => {
    const taskId = Number(route.request().url().match(/jenkins-tasks\/(\d+)\/sync/)?.[1])
    syncRequests.push(taskId)
    tasks = tasks.map((task) =>
      task.id === taskId ? { ...task, status: 'success', actions: { ...task.actions, cancel: false } } : task,
    )
    await route.fulfill({ status: 200, json: { data: tasks.find((task) => task.id === taskId) } })
  })

  return { failedRetryPayloads, moduleRerunPayloads, cancelRequests, syncRequests, taskListRequests }
}

test.describe('Stage6 P5 Jenkins 执行闭环前端 RED', () => {
  test('admin 在模块行触发失败重试时提交 all_failed，成功后刷新但保留执行时间', async ({ page }) => {
    const api = await mockStage6P5Api(page)

    await page.goto('/modules?environment_id=1')
    await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
    await expect(page.locator('tbody').getByText('33.5秒')).toBeVisible()

    await page.getByRole('button', { name: '一键失败重试' }).click()
    await expect(page.getByRole('dialog', { name: /确认失败重试/ })).toHaveCount(0)

    await expect.poll(() => api.failedRetryPayloads).toEqual([{ retry_scope: 'all_failed' }])
    await expect(page.getByText('开始执行失败重试')).toBeVisible()
    await expect(page.locator('tbody').getByText('33.5秒')).toBeVisible()
  })

  test('admin 在模块行触发模块重试后调用 module_reruns，并刷新完整执行时间', async ({ page }) => {
    const api = await mockStage6P5Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: '模块重试' }).click()
    const confirmDialog = page.getByRole('dialog', { name: /确认模块重试/ })
    await confirmDialog.getByRole('button', { name: '确认模块重试' }).click()

    await expect.poll(() => api.moduleRerunPayloads).toEqual([{}])
    await expect(page.getByText('Jenkins 任务已创建：模块重试')).toBeVisible()
    await expect(page.locator('tbody').getByText('41.0秒')).toBeVisible()
  })

  test('admin 在用例详情中勾选失败用例重试，且一键失败重试使用 all_failed 范围', async ({ page }) => {
    const api = await mockStage6P5Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const dialog = page.getByRole('dialog', { name: /用例详情/ })
    await expect(dialog).toBeVisible()

    await dialog.getByRole('checkbox', { name: '选择 test_search_species' }).check()
    await dialog.getByRole('button', { name: '重试选中用例' }).click()
    await expect.poll(() => api.failedRetryPayloads.at(0)).toEqual({
      retry_scope: 'selected_failed',
      case_result_ids: [501],
    })

    await dialog.getByRole('button', { name: '一键失败重试' }).click()
    await expect.poll(() => api.failedRetryPayloads.at(1)).toEqual({ retry_scope: 'all_failed' })

    await dialog.getByRole('button', { name: '跳过' }).click()
    await expect(dialog.getByRole('checkbox', { name: '选择 test_legacy_species' })).toBeDisabled()
  })

  test('Jenkins 任务弹窗展示任务、取消运行中任务，并通过新页打开报告和 Jenkins', async ({ page }) => {
    const api = await mockStage6P5Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    const dialog = page.getByRole('dialog', { name: /物种查询模块.*Jenkins 任务/ })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('cell', { name: '运行中' })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: '测试失败' })).toBeVisible()

    await dialog.getByRole('button', { name: '取消任务' }).first().click()
    await expect.poll(() => api.cancelRequests).toEqual([302])
    await expect(dialog.getByRole('cell', { name: '取消中' })).toBeVisible()

    const reportPopupPromise = page.waitForEvent('popup')
    await dialog.getByRole('link', { name: '查看报告' }).click()
    const reportPopup = await reportPopupPromise
    await expect(reportPopup).toHaveURL(/allure\.example\.test\/reports\/303/)
    await reportPopup.close()

    const jenkinsPopupPromise = page.waitForEvent('popup')
    await dialog.getByRole('link', { name: '查看 Jenkins 任务' }).last().click()
    const jenkinsPopup = await jenkinsPopupPromise
    await expect(jenkinsPopup).toHaveURL(/jenkins\.example\.test\/job\/AiApiTest-DWP-Module-Rerun\/303/)
    await jenkinsPopup.close()
  })

  test('Jenkins 任务弹窗打开时会轮询运行中任务，关闭后停止刷新', async ({ page }) => {
    const api = await mockStage6P5Api(page, { pollToSuccess: true })

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    const dialog = page.getByRole('dialog', { name: /Jenkins 任务/ })

    await expect.poll(() => api.syncRequests.length, { timeout: 6500 }).toBeGreaterThan(0)
    expect(api.syncRequests).toContain(302)
    await expect.poll(() => api.taskListRequests.length, { timeout: 6500 }).toBeGreaterThan(1)
    await expect(dialog.getByRole('cell', { name: '成功' })).toBeVisible()

    await dialog.getByRole('button', { name: '关闭' }).click()
    const requestCountAfterClose = api.taskListRequests.length
    await page.waitForTimeout(5200)
    expect(api.taskListRequests.length).toBe(requestCountAfterClose)
  })

  test('锁冲突使用固定文案提示，member 只读可看任务但不能触发重试且移动端无横向溢出', async ({ page }) => {
    await mockStage6P5Api(page, { lockedRetry: true })
    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: '一键失败重试' }).click()
    await expect(page.getByText('本模块已经有真正执行的重试!')).toBeVisible()

    await page.setViewportSize({ width: 390, height: 844 })
    await mockStage6P5Api(page, { role: 'member' })
    await page.goto('/modules?environment_id=1')
    await expect(page.getByRole('button', { name: '一键失败重试' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '模块重试' })).toBeDisabled()
    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    await expect(page.getByRole('dialog', { name: /Jenkins 任务/ })).toBeVisible()

    const horizontalOverflow = await page.evaluate(() => {
      const documentWidth = document.documentElement.clientWidth
      return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - documentWidth
    })
    expect(horizontalOverflow).toBeLessThanOrEqual(1)
  })
})
