import { expect, test, type Page } from '@playwright/test'

const testEnvironment = {
  id: 1,
  env_key: 'mock-example',
  env_name: '模拟测试环境',
  base_url: 'https://example.test/api',
}

const secondEnvironment = {
  id: 2,
  env_key: 'mock-inventory',
  env_name: '库存测试环境',
  base_url: 'https://inventory.example.test/api',
}

const adminUser = {
  id: 1,
  username: 'admin_user',
  display_name: '平台管理员',
  role: 'admin',
  permissions: ['profile:read'],
}

const enabledActions = {
  failed_rerun: true,
  module_rerun: true,
  trend_7d: true,
  trend_30d: true,
  jenkins_tasks: true,
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
  actions: enabledActions,
}

const secondModuleSnapshot = {
  ...moduleSnapshot,
  id: 102,
  completed_at: '2026-07-05T11:20:00+08:00',
  package_name: 'test_inventory_case',
  module_name: '库存模块',
  module_dev: '赵六',
  module_test: '钱七',
  failed_count: 1,
  passed_count: 98,
  pass_rate: 0.99,
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

const failedRetryTask = {
  id: 301,
  task_type: 'failed_rerun',
  job_name: 'AiApiTest-DWP-Failed-Rerun',
  environment_url: testEnvironment.base_url,
  status: 'queued',
  triggered_by: '平台管理员',
  started_at: null,
  finished_at: null,
  jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Failed-Rerun/301/',
  allure_report_url: null,
  actions: { cancel: true, view_report: false, view_jenkins_task: true },
}

const moduleRerunTask = {
  ...failedRetryTask,
  id: 302,
  task_type: 'module_rerun',
  job_name: 'AiApiTest-DWP-Module-Rerun',
  status: 'running',
  started_at: '2026-07-06T10:00:00+08:00',
  jenkins_build_url: 'https://jenkins.example.test/job/AiApiTest-DWP-Module-Rerun/302/',
}

const taskTypeLabels: Record<string, string> = {
  daily_full: '每日全量',
  failed_rerun: '失败重试',
  module_rerun: '模块重试',
}

type Stage8MockApi = {
  filterOptionRequests: URL[]
  moduleSnapshotRequests: URL[]
  failedRetryPayloads: unknown[]
  moduleRerunPayloads: unknown[]
  taskListRequests: URL[]
}

type Stage8MockOptions = {
  filterOptionsFailure?: boolean
}

async function mockStage8Api(page: Page, options: Stage8MockOptions = {}): Promise<Stage8MockApi> {
  const filterOptionRequests: URL[] = []
  const moduleSnapshotRequests: URL[] = []
  const failedRetryPayloads: unknown[] = []
  const moduleRerunPayloads: unknown[] = []
  const taskListRequests: URL[] = []

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { data: adminUser } })
  })

  await page.route(/\/api\/v1\/test-environments(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, json: { data: [testEnvironment, secondEnvironment] } })
  })

  await page.route(/\/api\/v1\/module-snapshots\/filter-options(?:\?.*)?$/, async (route) => {
    const requestUrl = new URL(route.request().url())
    filterOptionRequests.push(requestUrl)
    if (options.filterOptionsFailure) {
      await route.fulfill({
        status: 500,
        json: { error: { code: 'server_error', message: '筛选选项加载失败' } },
      })
      return
    }
    const optionSnapshots = requestUrl.searchParams.get('environment_id') === '2'
      ? [secondModuleSnapshot]
      : [moduleSnapshot, secondModuleSnapshot]
    await route.fulfill({
      status: 200,
      json: {
        data: {
          module_names: optionSnapshots.map((snapshot) => ({ label: snapshot.module_name, value: snapshot.module_name, count: 1 })),
          package_names: optionSnapshots.map((snapshot) => ({ label: snapshot.package_name, value: snapshot.package_name, count: 1 })),
          module_devs: optionSnapshots.map((snapshot) => ({ label: snapshot.module_dev, value: snapshot.module_dev, count: 1 })),
          module_tests: optionSnapshots.map((snapshot) => ({ label: snapshot.module_test, value: snapshot.module_test, count: 1 })),
        },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots(?:\?.*)?$/, async (route) => {
    const requestUrl = new URL(route.request().url())
    moduleSnapshotRequests.push(requestUrl)
    const data = requestUrl.searchParams.get('environment_id') === '2' ? [secondModuleSnapshot] : [moduleSnapshot]
    await route.fulfill({
      status: 200,
      json: {
        data,
        meta: {
          total: 40,
          page: Number(requestUrl.searchParams.get('page') ?? '1'),
          per_page: Number(requestUrl.searchParams.get('per_page') ?? '20'),
          total_pages: 2,
        },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/cases(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: [retryableFailedCase],
        meta: { total: 1, page: 1, per_page: 20, total_pages: 1 },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/failed-case-retries$/, async (route) => {
    failedRetryPayloads.push(route.request().postDataJSON())
    await route.fulfill({ status: 202, json: { data: failedRetryTask } })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/module-reruns$/, async (route) => {
    moduleRerunPayloads.push(route.request().postDataJSON())
    await route.fulfill({ status: 202, json: { data: moduleRerunTask } })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/jenkins-tasks(?:\?.*)?$/, async (route) => {
    const requestUrl = new URL(route.request().url())
    taskListRequests.push(requestUrl)
    const taskType = requestUrl.searchParams.get('task_type')
    const tasks = [failedRetryTask, moduleRerunTask].filter((task) => !taskType || task.task_type === taskType)
    await route.fulfill({
      status: 200,
      json: {
        data: tasks,
        meta: { total: tasks.length, page: 1, per_page: 20, total_pages: 1 },
      },
    })
  })

  return {
    filterOptionRequests,
    moduleSnapshotRequests,
    failedRetryPayloads,
    moduleRerunPayloads,
    taskListRequests,
  }
}

async function selectMultiOption(page: Page, testId: string, optionName: string) {
  await page.getByTestId(testId).click()
  await page.getByRole('option', { name: optionName }).click()
}

function normalizeTexts(values: string[]) {
  return values.map((value) => value.replace(/\s+/g, '').trim()).filter(Boolean)
}

test.describe('Stage8 模块通过率筛选与 Jenkins 趋势接入前端 RED', () => {
  test('模块筛选区使用后端多选选项，点选后自动同步 URL query', async ({ page }) => {
    const api = await mockStage8Api(page)

    await page.goto('/modules?environment_id=1&page=2')
    await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
    await expect(page.getByText('筛选与分页状态会同步到地址栏')).toHaveCount(0)
    await expect(page.getByLabel('通过率上限')).toHaveCount(0)
    await expect(page.getByText('上限筛选')).toHaveCount(0)
    await expect(page.locator('.filter-bar').getByText('模块开发', { exact: true })).toBeVisible()
    await expect.poll(() => api.filterOptionRequests.length).toBe(1)
    await expect.poll(() => api.filterOptionRequests[0]?.searchParams.get('environment_id')).toBe('1')

    const filterButtons = page.locator('.filter-bar button')
    await expect(filterButtons.nth(0)).toHaveText('重置')
    await expect(page.getByRole('button', { name: '查询', exact: true })).toHaveCount(0)

    await selectMultiOption(page, 'module-name-filter', '物种查询模块')
    await selectMultiOption(page, 'module-name-filter', '库存模块')
    await selectMultiOption(page, 'module-dev-filter', '张三')
    await selectMultiOption(page, 'module-dev-filter', '赵六')

    await expect.poll(() => new URL(page.url()).searchParams.get('module_name')).toBe('物种查询模块,库存模块')
    await expect.poll(() => new URL(page.url()).searchParams.get('module_dev')).toBe('张三,赵六')
    await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBeNull()
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('module_name')).toBe('物种查询模块,库存模块')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('module_dev')).toBe('张三,赵六')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('pass_rate_lte')).toBeNull()

    await page.reload()
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('module_name')).toBe('物种查询模块,库存模块')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('module_dev')).toBe('张三,赵六')

    await page.getByRole('button', { name: '重置', exact: true }).click()
    await expect.poll(() => new URL(page.url()).searchParams.get('module_name')).toBeNull()
    await expect.poll(() => new URL(page.url()).searchParams.get('module_dev')).toBeNull()
    await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBeNull()
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('page')).toBe('1')

    const requestCountBeforeSameReset = api.moduleSnapshotRequests.length
    await page.getByRole('button', { name: '重置', exact: true }).click()
    await expect.poll(() => api.moduleSnapshotRequests.length).toBe(requestCountBeforeSameReset + 1)
  })

  test('切换测试环境会同步 URL、刷新筛选选项和模块列表', async ({ page }) => {
    const api = await mockStage8Api(page)

    await page.goto('/modules?environment_id=1')
    await expect(page.locator('tbody').getByText('物种查询模块')).toBeVisible()

    await page.locator('#module-environment-filter').selectOption('2')
    await expect.poll(() => new URL(page.url()).searchParams.get('environment_id')).toBe('2')
    await expect.poll(() => api.filterOptionRequests.at(-1)?.searchParams.get('environment_id')).toBe('2')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('environment_id')).toBe('2')
    await expect(page.locator('tbody').getByText('库存模块')).toBeVisible()
    await expect(page.locator('tbody').getByText('物种查询模块')).toHaveCount(0)

    await page.getByTestId('module-dev-filter').click()
    await expect(page.getByRole('option', { name: '赵六' })).toBeVisible()
  })

  test('重复点击侧边栏模块通过率入口不会清空或重置当前环境数据', async ({ page }) => {
    const api = await mockStage8Api(page)

    await page.goto('/modules?environment_id=2')
    await expect(page.locator('tbody').getByText('库存模块')).toBeVisible()

    await page.getByRole('navigation', { name: '平台导航' }).getByRole('link', { name: '模块通过率' }).click()
    await page.getByRole('navigation', { name: '平台导航' }).getByRole('link', { name: '模块通过率' }).click()

    await expect.poll(() => new URL(page.url()).searchParams.get('environment_id')).toBe('2')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('environment_id')).toBe('2')
    await expect(page.locator('tbody').getByText('库存模块')).toBeVisible()
    await expect(page.locator('tbody').getByText('物种查询模块')).toHaveCount(0)
    await expect(page.getByText('暂无模块快照')).toHaveCount(0)
  })

  test('筛选选项接口失败时模块列表仍可基础查询', async ({ page }) => {
    await mockStage8Api(page, { filterOptionsFailure: true })

    await page.goto('/modules?environment_id=1')
    await expect(page.getByText('筛选选项加载失败，可稍后重试。')).toBeVisible()
    await expect(page.locator('tbody').getByText('物种查询模块')).toBeVisible()
    await expect(page.getByText(/TypeError|ReferenceError|Cannot read/i)).toHaveCount(0)
  })

  test('桌面表格和移动端卡片都把通过率放在跳过之后', async ({ page }) => {
    await mockStage8Api(page)

    await page.goto('/modules?environment_id=1')
    await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
    const headers = normalizeTexts(await page.locator('.table-frame thead th').allTextContents())
    expect(headers).toEqual(['日期', '用例包名', '模块名称', '执行时间', '模块开发', '模块测试', '总数', '失败', '跳过', '通过率', '后置能力'])

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/modules?environment_id=1')
    await expect(page.locator('.module-card').first()).toBeVisible()
    const mobileLabels = normalizeTexts(await page.locator('.module-card').first().locator('dt').allTextContents())
    expect(mobileLabels).toEqual(['日期', '执行时间', '模块开发', '模块测试', '总数', '失败', '跳过', '通过率'])
    await expect(page.getByLabel('模块移动端列表').getByText('96.00%')).toBeVisible()
    const horizontalOverflow = await page.evaluate(() => {
      const documentWidth = document.documentElement.clientWidth
      return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - documentWidth
    })
    expect(horizontalOverflow).toBeLessThanOrEqual(1)
  })

  test('失败重试直接触发并提示，模块重试必须使用固定文案确认', async ({ page }) => {
    const api = await mockStage8Api(page)

    await page.goto('/modules?environment_id=1')
    await expect(page.locator('.table-frame').getByRole('button', { name: '失败重试', exact: true })).toHaveCount(0)
    await page.getByRole('button', { name: '一键失败重试', exact: true }).click()
    await expect(page.getByRole('dialog', { name: /确认失败重试/ })).toHaveCount(0)
    await expect.poll(() => api.failedRetryPayloads).toEqual([{ retry_scope: 'all_failed' }])
    await expect(page.getByText('开始执行失败重试')).toBeVisible()

    await page.getByRole('button', { name: '模块重试' }).click()
    const confirmDialog = page.getByRole('dialog', { name: /确认模块重试/ })
    await expect(confirmDialog).toBeVisible()
    await expect(confirmDialog.getByText('模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？')).toBeVisible()
    await confirmDialog.getByRole('button', { name: '取消' }).click()
    await expect.poll(() => api.moduleRerunPayloads).toEqual([])

    await page.getByRole('button', { name: '模块重试' }).click()
    await page.getByRole('dialog', { name: /确认模块重试/ }).getByRole('button', { name: /确认模块重试|确认重试/ }).click()
    await expect.poll(() => api.moduleRerunPayloads).toEqual([{}])
  })

  test('用例详情弹窗中的选中重试和一键失败重试直接触发并显示固定提示', async ({ page }) => {
    const api = await mockStage8Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const dialog = page.getByRole('dialog', { name: /用例详情/ })
    await expect(dialog).toBeVisible()
    const dialogBox = await dialog.boundingBox()
    const viewport = page.viewportSize()
    expect(dialogBox?.width).toBeGreaterThanOrEqual((viewport?.width ?? 1440) * 0.68)
    expect(dialogBox?.x).toBeGreaterThan((viewport?.width ?? 1440) * 0.25)

    await dialog.getByRole('checkbox', { name: '选择 test_search_species' }).check()
    await dialog.getByRole('button', { name: '重试选中用例' }).click()
    await expect(page.getByRole('dialog', { name: /确认失败重试/ })).toHaveCount(0)
    await expect.poll(() => api.failedRetryPayloads.at(0)).toEqual({
      retry_scope: 'selected_failed',
      case_result_ids: [501],
    })
    await expect(dialog.getByText('开始执行失败重试')).toBeVisible()

    await dialog.getByRole('button', { name: '一键失败重试' }).click()
    await expect.poll(() => api.failedRetryPayloads.at(1)).toEqual({ retry_scope: 'all_failed' })
    await expect(dialog.getByText('开始执行失败重试')).toBeVisible()
  })

  test('Jenkins 任务弹窗展示任务类型和任务名，并支持状态日期任务类型筛选', async ({ page }) => {
    const api = await mockStage8Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    const dialog = page.getByRole('dialog', { name: /Jenkins 任务/ })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByLabel('任务状态')).toBeVisible()
    await expect(dialog.getByLabel('任务日期')).toBeVisible()
    await expect(dialog.getByLabel('任务类型')).toBeVisible()
    await expect(dialog.getByRole('columnheader', { name: '任务类型' })).toBeVisible()
    await expect(dialog.getByRole('columnheader', { name: '任务名' })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: taskTypeLabels.failed_rerun })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: failedRetryTask.job_name })).toBeVisible()

    await dialog.getByLabel('任务状态').selectOption('running')
    await dialog.getByLabel('任务日期').fill('2026-07-06')
    await dialog.getByLabel('任务类型').selectOption('module_rerun')
    await dialog.getByRole('button', { name: '查询', exact: true }).click()

    await expect.poll(() => api.taskListRequests.at(-1)?.searchParams.get('status')).toBe('running')
    await expect.poll(() => api.taskListRequests.at(-1)?.searchParams.get('date')).toBe('2026-07-06')
    await expect.poll(() => api.taskListRequests.at(-1)?.searchParams.get('task_type')).toBe('module_rerun')
    await expect(dialog.getByRole('cell', { name: taskTypeLabels.module_rerun })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: moduleRerunTask.job_name })).toBeVisible()
  })

  test('保存 Stage8 模块筛选与 Jenkins 弹窗关键截图', async ({ page }) => {
    await mockStage8Api(page)

    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/modules?environment_id=1')
    await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage8-modules-filters-desktop-20260707.png',
      fullPage: true,
    })

    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const caseDialog = page.getByRole('dialog', { name: /用例详情/ })
    await expect(caseDialog).toBeVisible()
    await caseDialog.screenshot({
      path: 'tests/evidence/screenshots/stage8-case-details-retry-20260707.png',
    })
    await caseDialog.getByRole('button', { name: '关闭' }).click()

    await page.getByRole('button', { name: 'Jenkins 任务' }).click()
    const jenkinsDialog = page.getByRole('dialog', { name: /Jenkins 任务/ })
    await expect(jenkinsDialog).toBeVisible()
    await jenkinsDialog.screenshot({
      path: 'tests/evidence/screenshots/stage8-jenkins-tasks-filters-20260707.png',
    })
    await jenkinsDialog.getByRole('button', { name: '关闭' }).click()

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/modules?environment_id=1')
    await expect(page.getByLabel('模块移动端列表')).toBeVisible()
    await page.screenshot({
      path: 'tests/evidence/screenshots/stage8-modules-mobile-20260707.png',
      fullPage: true,
    })
  })
})
