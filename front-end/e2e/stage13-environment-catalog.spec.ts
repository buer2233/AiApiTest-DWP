import { expect, test, type Page } from '@playwright/test'

const adminUser = {
  id: 1,
  username: 'stage13_admin',
  display_name: '平台管理员',
  role: 'admin',
  permissions: [],
}

const memberUser = {
  id: 2,
  username: 'stage13_member',
  display_name: '普通成员',
  role: 'member',
  permissions: [],
}

const catalogState = {
  status: 'synced',
  yaml_blob_sha: 'a'.repeat(40),
  last_commit_sha: 'b'.repeat(40),
  last_synced_at: '2026-07-20T10:00:00+08:00',
  last_error_code: null,
  last_error_summary: null,
}

const catalogEnvironment = {
  id: 7,
  env_key: 'stage13-qa',
  env_name: 'Stage13 QA',
  url_name: 'Stage13 QA',
  base_url: 'https://stage13-qa.example.invalid/api',
  url_desc: '自动化回归测试环境',
  is_active: true,
}

const environmentSummary = {
  environment: catalogEnvironment,
  started_at: '2026-07-20T09:00:00+08:00',
  finished_at: '2026-07-20T09:08:00+08:00',
  duration_seconds: 480,
  total_count: 120,
  failed_count: 6,
  passed_count: 112,
  skipped_count: 2,
  pass_rate: 0.9333,
  actions: { generate_report: false },
}

async function mockStage13Api(page: Page, user: typeof adminUser | typeof memberUser) {
  const requestedManagementEndpoints: string[] = []

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { data: user } })
  })

  await page.route(/\/api\/v1\/test-environments\/7\/summary(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, json: { data: environmentSummary } })
  })

  await page.route(/\/api\/v1\/environment-catalog-sync-attempts\/\d+(?:\/retry)?$/, async (route) => {
    requestedManagementEndpoints.push(route.request().url())
    await route.fulfill({ status: 403, json: { error: { code: 'admin_required', message: '需要管理人员权限。', details: [] } } })
  })

  await page.route(/\/api\/v1\/test-environments\/sync-from-yaml$/, async (route) => {
    requestedManagementEndpoints.push(route.request().url())
    await route.fulfill({ status: 403, json: { error: { code: 'admin_required', message: '需要管理人员权限。', details: [] } } })
  })

  await page.route(/\/api\/v1\/test-environments(?:\/\d+)?(?:\?.*)?$/, async (route) => {
    const request = route.request()
    const requestUrl = new URL(request.url())
    const isReadOnlyEnvironmentLookup = request.method() === 'GET' && requestUrl.searchParams.get('is_active') === 'true'

    if (isReadOnlyEnvironmentLookup) {
      await route.fulfill({ status: 200, json: { data: [catalogEnvironment], catalog_state: catalogState } })
      return
    }

    requestedManagementEndpoints.push(request.url())
    if (user.role !== 'admin') {
      await route.fulfill({ status: 403, json: { error: { code: 'admin_required', message: '需要管理人员权限。', details: [] } } })
      return
    }

    if (request.method() === 'GET') {
      await route.fulfill({ status: 200, json: { data: [catalogEnvironment], catalog_state: catalogState } })
      return
    }

    await route.fulfill({
      status: 202,
      json: {
        data: {
          environment: catalogEnvironment,
          sync_attempt: {
            id: 13,
            request_id: 'stage13-sync-13',
            direction: 'mysql_to_yaml',
            status: 'queued',
            expected_yaml_blob_sha: catalogState.yaml_blob_sha,
            observed_yaml_blob_sha: null,
            queue_id: '42',
            build_number: null,
            jenkins_build_url: null,
            job_full_name: 'AiApiTest-DWP-Environment-Catalog-Sync',
            commit_sha: null,
            requested_by: adminUser.display_name,
            error_code: null,
            error_summary: null,
            created_at: '2026-07-20T10:01:00+08:00',
            finished_at: null,
          },
        },
      },
    })
  })

  return { requestedManagementEndpoints }
}

test('TC-S13-F3-014：admin 按 C01 全宽台账维护环境并查看异步同步状态', async ({ page }) => {
  await mockStage13Api(page, adminUser)

  await page.goto('/environments')

  await expect(page.getByRole('heading', { name: '环境通过率' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '环境目录' })).toBeVisible()
  await expect(page.getByText('stage13-qa', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '新建环境' }).click()
  await expect(page.getByLabel('环境 key')).toBeEditable()
  await page.getByLabel('环境 key').fill('stage13-pre')
  await page.getByLabel('环境名称').fill('Stage13 Pre')
  await page.getByLabel('环境地址').fill('https://stage13-pre.example.invalid/api')
  await page.getByLabel('环境描述').fill('预发布回归环境')
  await page.getByRole('button', { name: '保存环境' }).click()

  await expect(page.getByText('已进入队列')).toBeVisible()
  await expect(page.getByText(/模块子任务/)).toHaveCount(0)
  await expect(page.getByText(/模块级 Allure/)).toHaveCount(0)
})

test('TC-S13-F3-011：member 只看到 R1，且不会请求目录管理接口', async ({ page }) => {
  const api = await mockStage13Api(page, memberUser)

  await page.goto('/environments')

  await expect(page.getByRole('heading', { name: '环境通过率' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '环境目录' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '新建环境' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '同步测试环境数据' })).toHaveCount(0)
  expect(api.requestedManagementEndpoints).toEqual([])
})
