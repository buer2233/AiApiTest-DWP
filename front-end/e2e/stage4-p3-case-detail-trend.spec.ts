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
  failed_rerun: false,
  module_rerun: false,
  trend_7d: true,
  trend_30d: true,
  jenkins_tasks: false,
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

const passedCase = {
  ...failedCase,
  id: 502,
  node_id: 'test_case/test_gbif_case/test_species.py::test_get_species',
  case_name: 'test_get_species',
  case_summary: '物种查询通过用例',
  error_type: '',
  assertion_text: '',
  execution_status: 'passed',
  display_status: 'passed',
  error_message_summary: '',
  error_message_detail: '',
  confirmation_result: '',
}

const skippedCase = {
  ...failedCase,
  id: 503,
  node_id: 'test_case/test_gbif_case/test_species.py::test_legacy_species',
  case_name: 'test_legacy_species',
  case_summary: '历史接口跳过用例',
  error_type: '',
  assertion_text: '历史接口人工跳过',
  execution_status: 'failed',
  display_status: 'skipped',
  error_message_summary: '',
  error_message_detail: '',
  confirmation_result: '历史原因',
}

const failedCasePage2 = {
  ...failedCase,
  id: 504,
  node_id: 'test_case/test_gbif_case/test_species.py::test_page_two_species',
  case_name: 'test_page_two_species',
  case_summary: '第二页失败用例',
  error_type: 'TimeoutError',
  assertion_text: 'request finished within 5s',
  error_message_summary: 'TimeoutError: request exceeded 5s',
  error_message_detail: 'TimeoutError: request exceeded 5s; token=[REDACTED]',
  confirmation_result: '待确认',
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

type MockOptions = {
  role?: 'admin' | 'member'
  trendSeries?: typeof trendSeries
}

async function mockStage4P3Api(page: Page, options: MockOptions = {}) {
  const caseRequests: URL[] = []
  const trendRequests: URL[] = []
  const statusPayloads: unknown[] = []
  const forbiddenSideEffects: string[] = []
  const role = options.role ?? 'admin'

  page.on('request', (request) => {
    const url = request.url()
    const isSourceAsset = /\/src\//.test(url)
    if (/(jenkins|retry|rerun|report|reports|allure|tasks)/i.test(url) && !isSourceAsset) {
      forbiddenSideEffects.push(`${request.method()} ${url}`)
    }
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
    caseRequests.push(requestUrl)
    const status = requestUrl.searchParams.get('status') ?? 'failed'
    const page = Number(requestUrl.searchParams.get('page') ?? '1')
    const caseByStatus = {
      failed: [
        role === 'admin' ? (page === 2 ? failedCasePage2 : failedCase) : { ...failedCase, error_message_detail: null, actions: { can_update_status: false, can_retry: false } },
      ],
      passed: [passedCase],
      skipped: [skippedCase],
    }
    await route.fulfill({
      status: 200,
      json: {
        data: caseByStatus[status as keyof typeof caseByStatus] ?? [],
        meta: {
          total: status === 'failed' && role === 'admin' ? 2 : caseByStatus[status as keyof typeof caseByStatus]?.length ?? 0,
          page,
          per_page: Number(requestUrl.searchParams.get('per_page') ?? '20'),
          total_pages: status === 'failed' && role === 'admin' ? 2 : 1,
        },
      },
    })
  })

  await page.route(/\/api\/v1\/case-results\/\d+\/status$/, async (route) => {
    statusPayloads.push(route.request().postDataJSON())
    await route.fulfill({
      status: 200,
      json: {
        data: {
          case_result: { id: 501, display_status: 'skipped', confirmation_result: '误报，人工跳过' },
          module_summary: { snapshot_id: 101, total_count: 100, failed_count: 3, passed_count: 94, skipped_count: 3, pass_rate: '0.970000' },
          environment_summary: { environment_id: 1, total_count: 100, failed_count: 3, pass_rate: '0.970000' },
          audit_id: 9001,
        },
      },
    })
  })

  await page.route(/\/api\/v1\/module-snapshots\/\d+\/trend(?:\?.*)?$/, async (route) => {
    const requestUrl = new URL(route.request().url())
    trendRequests.push(requestUrl)
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
          days: Number(requestUrl.searchParams.get('days') ?? '7'),
          series: options.trendSeries ?? trendSeries,
        },
      },
    })
  })

  return { caseRequests, trendRequests, statusPayloads, forbiddenSideEffects }
}

test.describe('Stage4 P3 用例详情、状态审计与趋势数据 RED', () => {
  test('admin 点击通过率后打开详情弹窗，默认失败筛选并可切换通过用例', async ({ page }) => {
    const api = await mockStage4P3Api(page)

    await page.goto('/modules?environment_id=1')
    await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()

    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const dialog = page.getByRole('dialog', { name: /物种查询模块.*用例详情/ })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('cell', { name: 'test_search_species', exact: true })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: 'test_get_species', exact: true })).toHaveCount(0)
    await expect.poll(() => api.caseRequests.at(-1)?.searchParams.get('status')).toBe('failed')
    await expect(dialog.getByRole('cell', { name: 'AssertionError: expected 200, got 500' })).toBeVisible()
    await dialog.getByRole('button', { name: '查看详情' }).click()
    await expect(dialog.getByText('[REDACTED]')).toBeVisible()

    await dialog.getByRole('button', { name: '通过' }).click()
    await expect.poll(() => api.caseRequests.at(-1)?.searchParams.get('status')).toBe('passed')
    await expect(dialog.getByRole('cell', { name: 'test_get_species', exact: true })).toBeVisible()

    await dialog.getByRole('button', { name: '关闭' }).click()
    await expect(dialog).toHaveCount(0)
    await expect(page.getByText('test_get_species')).toHaveCount(0)
  })

  test('member 只能查看摘要且不渲染状态修改入口', async ({ page }) => {
    await mockStage4P3Api(page, { role: 'member' })

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()

    const dialog = page.getByRole('dialog', { name: /用例详情/ })
    await expect(dialog.getByRole('cell', { name: 'AssertionError: expected 200, got 500' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: '查看详情' })).toHaveCount(0)
    await expect(dialog.getByRole('button', { name: '修改状态' })).toHaveCount(0)
  })

  test('admin 修改失败用例状态会提交原因、关闭二级弹窗并刷新详情列表', async ({ page }) => {
    const api = await mockStage4P3Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const detailDialog = page.getByRole('dialog', { name: /用例详情/ })
    await detailDialog.getByRole('button', { name: '修改状态' }).click()

    const statusDialog = page.getByRole('dialog', { name: /修改用例状态/ })
    await expect(statusDialog).toBeVisible()
    await statusDialog.getByLabel('目标状态').selectOption('skipped')
    await statusDialog.getByLabel('修改原因').fill('误报，人工跳过')
    await statusDialog.getByRole('button', { name: '保存修改' }).click()

    await expect.poll(() => api.statusPayloads.length).toBe(1)
    expect(api.statusPayloads[0]).toEqual({ display_status: 'skipped', reason: '误报，人工跳过' })
    await expect(statusDialog).toHaveCount(0)
    await expect(detailDialog.getByText('状态已更新，审计记录已写入')).toBeVisible()
    await expect.poll(() => api.caseRequests.at(-1)?.searchParams.get('status')).toBe('failed')
  })

  test('用例详情分页可请求后续页，并区分原始执行状态和展示状态', async ({ page }) => {
    const api = await mockStage4P3Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const dialog = page.getByRole('dialog', { name: /用例详情/ })
    await expect(dialog.getByRole('cell', { name: 'test_search_species', exact: true })).toBeVisible()

    await dialog.getByRole('button', { name: '下一页' }).click()
    await expect.poll(() => api.caseRequests.at(-1)?.searchParams.get('page')).toBe('2')
    await expect(dialog.getByRole('cell', { name: 'test_page_two_species', exact: true })).toBeVisible()

    await dialog.getByRole('button', { name: '跳过' }).click()
    await expect.poll(() => api.caseRequests.at(-1)?.searchParams.get('status')).toBe('skipped')
    await expect(dialog.getByRole('cell', { name: '失败' }).first()).toBeVisible()
    await expect(dialog.getByRole('cell', { name: '跳过' }).first()).toBeVisible()
  })

  test('趋势按钮只请求当前模块趋势，展示 SVG、表格和空态', async ({ page }) => {
    const api = await mockStage4P3Api(page)

    await page.goto('/modules?environment_id=1')
    await page.getByRole('button', { name: '7天趋势' }).click()
    const dialog = page.getByRole('dialog', { name: /近 7 天趋势/ })
    await expect(dialog).toBeVisible()
    await expect.poll(() => api.trendRequests.at(-1)?.searchParams.get('days')).toBe('7')
    await expect(dialog.locator('svg[aria-label="通过率趋势折线图"]')).toBeVisible()
    await expect(dialog.getByRole('columnheader', { name: '日期' })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: '2026-07-02' })).toBeVisible()
    await expect(dialog.getByRole('cell', { name: '97.00%' })).toBeVisible()
    await dialog.getByRole('button', { name: '关闭' }).click()

    await page.route(/\/api\/v1\/module-snapshots\/\d+\/trend(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            module: { snapshot_id: 101, module_name: '物种查询模块', package_name: 'test_gbif_case', environment_name: '模拟测试环境' },
            days: 30,
            series: [],
          },
        },
      })
    })
    await page.getByRole('button', { name: '30天趋势' }).click()
    const emptyDialog = page.getByRole('dialog', { name: /近 30 天趋势/ })
    await expect(emptyDialog.getByText('暂无趋势数据')).toBeVisible()
    await expect(emptyDialog.getByText('无历史记录')).toBeVisible()
  })

  test('重试和 Jenkins 入口保持禁用无副作用，移动端弹窗不横向溢出', async ({ page }) => {
    const api = await mockStage4P3Api(page)

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/modules?environment_id=1')

    await expect(page.getByRole('button', { name: '一键失败重试' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '模块重试' })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Jenkins 任务' })).toBeDisabled()
    await page.getByRole('button', { name: /查看物种查询模块用例详情/ }).click()
    const dialog = page.getByRole('dialog', { name: /用例详情/ })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByLabel('移动端用例详情列表')).toBeVisible()
    await expect(dialog.getByRole('table')).toHaveCount(0)

    const horizontalOverflow = await page.evaluate(() => {
      const documentWidth = document.documentElement.clientWidth
      return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - documentWidth
    })
    expect(horizontalOverflow).toBeLessThanOrEqual(1)
    expect(api.forbiddenSideEffects).toEqual([])
  })
})
