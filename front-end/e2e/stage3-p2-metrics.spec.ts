import { expect, test, type Page } from '@playwright/test'

const TEST_ENV_BASE_URL = 'https://example.test/api'

const adminUser = {
  id: 1,
  username: 'admin_user',
  display_name: '平台管理员',
  role: 'admin',
  permissions: ['profile:read'],
}

const testEnvironment = {
  id: 1,
  env_key: 'mock-example',
  env_name: '模拟测试环境',
  base_url: TEST_ENV_BASE_URL,
}

const summaryWithSnapshot = {
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
}

const summaryWithoutSnapshot = {
  environment: testEnvironment,
  started_at: null,
  finished_at: null,
  duration_seconds: null,
  total_count: 0,
  failed_count: 0,
  passed_count: 0,
  skipped_count: 0,
  pass_rate: 0,
  actions: { generate_report: true },
}

const disabledActions = {
  failed_rerun: false,
  module_rerun: false,
  trend_7d: false,
  trend_30d: false,
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
  actions: disabledActions,
}

type Stage3P2ApiOptions = {
  summary?: typeof summaryWithSnapshot | typeof summaryWithoutSnapshot
  modules?: Array<typeof moduleSnapshot>
  totalModules?: number
}

async function mockStage3P2Api(page: Page, options: Stage3P2ApiOptions = {}) {
  const moduleSnapshotRequests: URL[] = []
  const sideEffectRequests: string[] = []
  const summary = options.summary ?? summaryWithSnapshot
  const modules = options.modules ?? [moduleSnapshot]
  const totalModules = options.totalModules ?? modules.length

  // P2 前端只允许通过 DRF 只读 API 获取数据；这里记录任何报告、重试、Jenkins 相关副作用请求。
  page.on('request', (request) => {
    const url = request.url()
    const method = request.method()
    const isApiWrite = /\/api\/v1\//.test(url) && method !== 'GET'
    const isSourceAsset = /\/src\//.test(url)
    const isForbiddenWorkflow = /(jenkins|retry|rerun|report|reports|allure|tasks)/i.test(url)
    if (isApiWrite || (isForbiddenWorkflow && !isSourceAsset)) {
      sideEffectRequests.push(`${method} ${url}`)
    }
  })

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { data: adminUser } })
  })

  await page.route(/\/api\/v1\/test-environments(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, json: { data: [testEnvironment] } })
  })

  await page.route(/\/api\/v1\/test-environments\/\d+\/summary(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, json: { data: summary } })
  })

  await page.route('**/api/v1/module-snapshots**', async (route) => {
    const requestUrl = new URL(route.request().url())
    moduleSnapshotRequests.push(requestUrl)
    const pageNumber = Number(requestUrl.searchParams.get('page') ?? '1')
    const perPage = Number(requestUrl.searchParams.get('per_page') ?? '20')

    await route.fulfill({
      status: 200,
      json: {
        data: modules,
        meta: {
          total: totalModules,
          page: pageNumber,
          per_page: perPage,
          total_pages: Math.max(1, Math.ceil(totalModules / perPage)),
        },
      },
    })
  })

  return { moduleSnapshotRequests, sideEffectRequests }
}

test.describe('Stage3 P2 环境与模块通过率只读页面 RED', () => {
  test('环境页展示环境下拉、汇总、后端返回地址和模块通过率入口', async ({ page }) => {
    await mockStage3P2Api(page)

    await page.goto('/environments')

    await expect(page.getByRole('heading', { name: '环境通过率' })).toBeVisible()
    const environmentSelect = page.locator('#environment-select')
    await expect(environmentSelect).toBeVisible()
    await expect(environmentSelect).toHaveValue('1')
    await expect(environmentSelect.locator('option:checked')).toHaveText('模拟测试环境')
    await expect(page.getByLabel('通过率汇总').getByText('模拟测试环境')).toBeVisible()
    await expect(page.getByText(TEST_ENV_BASE_URL)).toBeVisible()
    await expect(page.getByText('https://api.gbif.org')).toHaveCount(0)
    await expect(page.getByText('开始时间')).toBeVisible()
    await expect(page.getByText('结束时间')).toBeVisible()
    await expect(page.getByText('运行时间')).toBeVisible()
    await expect(page.getByText('96.00%')).toBeVisible()

    await page.getByRole('main').getByRole('link', { name: /模块通过率/ }).click()
    await expect(page).toHaveURL(/\/modules\?environment_id=1/)
  })

  test('环境页在无快照时展示暂无执行结果空态且不出现前端异常', async ({ page }) => {
    await mockStage3P2Api(page, { summary: summaryWithoutSnapshot })

    await page.goto('/environments')

    await expect(page.getByRole('heading', { name: '环境通过率' })).toBeVisible()
    await expect(page.getByText('暂无执行结果')).toBeVisible()
    await expect(page.getByText(/TypeError|ReferenceError|Cannot read/i)).toHaveCount(0)
  })

  test('生成环境报告按钮只提示后续实现且不触发 Jenkins、重试或报告创建请求', async ({ page }) => {
    const api = await mockStage3P2Api(page)

    await page.goto('/environments')
    await page.getByRole('button', { name: '生成环境报告' }).click()

    await expect(page.getByText('AI 分析报告功能后续实现')).toBeVisible()
    await page.waitForTimeout(100)
    expect(api.sideEffectRequests).toEqual([])
  })

  test('模块页展示核心字段并把 total=100 failed=4 渲染为 96.00%', async ({ page }) => {
    await mockStage3P2Api(page)

    await page.goto('/modules?environment_id=1')

    const tableHeader = page.locator('thead')
    await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '模块通过率' })).toHaveText('模块通过率')
    await expect(tableHeader.getByText('日期', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('用例包名', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('模块名称', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('模块开发', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('模块测试', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('跳过', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('通过率', { exact: true })).toBeVisible()
    await expect(tableHeader.getByText('执行时间', { exact: true })).toBeVisible()
    const tableBody = page.locator('tbody')
    await expect(tableBody.getByText('test_gbif_case')).toBeVisible()
    await expect(tableBody.getByText('物种查询模块')).toBeVisible()
    await expect(tableBody.getByText('张三')).toBeVisible()
    await expect(tableBody.getByText('李四')).toBeVisible()
    await expect(tableBody.getByText('96.00%')).toBeVisible()
    await expect(tableBody).toContainText('2')
  })

  test('模块页筛选、重置和分页会同步到 URL query 并请求后端分页接口', async ({ page }) => {
    const api = await mockStage3P2Api(page, { totalModules: 21 })

    await page.goto('/modules?environment_id=1')
    await page.getByLabel('模块名称').fill('物种')
    await page.getByLabel('用例包名').fill('test_gbif_case')
    await page.getByLabel('模块测试').fill('李四')
    await page.getByLabel('通过率上限').fill('90')
    await page.getByRole('button', { name: '查询', exact: true }).click()

    await expect.poll(() => new URL(page.url()).searchParams.get('module_name')).toBe('物种')
    await expect.poll(() => new URL(page.url()).searchParams.get('package_name')).toBe('test_gbif_case')
    await expect.poll(() => new URL(page.url()).searchParams.get('module_test')).toBe('李四')
    await expect.poll(() => new URL(page.url()).searchParams.get('pass_rate_lte')).toBe('90')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('module_name')).toBe('物种')

    await page.getByRole('button', { name: '下一页' }).click()
    await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBe('2')
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('page')).toBe('2')

    await page.getByLabel('每页条数').selectOption('50')
    await expect.poll(() => new URL(page.url()).searchParams.get('per_page')).toBe('50')
    await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBeNull()
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('per_page')).toBe('50')

    await page.getByRole('button', { name: '重置' }).click()
    await expect.poll(() => new URL(page.url()).searchParams.get('environment_id')).toBe('1')
    await expect.poll(() => new URL(page.url()).searchParams.get('module_name')).toBeNull()
    await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBeNull()
    await expect.poll(() => api.moduleSnapshotRequests.at(-1)?.searchParams.get('page')).toBe('1')
  })

  test('模块页 actions 全为 false 时后置能力按钮保持禁用且点击不会产生副作用', async ({ page }) => {
    const api = await mockStage3P2Api(page)

    await page.goto('/modules?environment_id=1')

    const actionNames = [/失败重试/, /模块重试/, /7天趋势/, /30天趋势/, /Jenkins任务|Jenkins 任务/]
    for (const actionName of actionNames) {
      const button = page.getByRole('button', { name: actionName })
      await expect(button).toBeVisible()
      await expect(button).toBeDisabled()
    }

    await page.waitForTimeout(100)
    expect(api.sideEffectRequests).toEqual([])
  })

  test('移动端环境页和模块页不会让 body 出现横向滚动', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await mockStage3P2Api(page)

    for (const routePath of ['/environments', '/modules?environment_id=1']) {
      await page.goto(routePath)
      await expect(page.getByRole('heading', { name: /环境通过率|模块通过率/ })).toBeVisible()
      if (routePath.startsWith('/modules')) {
        const mobileCards = page.getByLabel('模块移动端列表')
        await expect(mobileCards.getByText('物种查询模块')).toBeVisible()
        await expect(mobileCards.getByText('96.00%')).toBeVisible()
        await expect(mobileCards.getByText('跳过 2')).toBeVisible()
      }

      const horizontalOverflow = await page.evaluate(() => {
        const documentWidth = document.documentElement.clientWidth
        return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - documentWidth
      })
      expect(horizontalOverflow).toBeLessThanOrEqual(1)
    }
  })
})
