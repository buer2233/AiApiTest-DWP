import { expect, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

type EnvMap = Record<string, string>
type FilterOptionPayload = {
  value: string
}

const evidencePath = resolve(process.cwd(), 'tests/evidence/screenshots/stage8-real-acceptance-modules-20260707.png')
const expectedLockedMessage = '本模块已经有真正执行的重试!'

function readLocalEnv(): EnvMap {
  const envPath = resolve(process.cwd(), '..', '.env')
  const values: EnvMap = {}
  try {
    for (const line of readFileSync(envPath, 'utf-8').split(/\r?\n/)) {
      const match = line.match(/^([^#][^=]+)=(.*)$/)
      if (match) {
        values[match[1].trim()] = match[2].trim()
      }
    }
  } catch {
    return values
  }
  return values
}

function realAcceptanceConfig() {
  const localEnv = readLocalEnv()
  return {
    baseUrl: process.env.STAGE8_REAL_BASE_URL || 'http://127.0.0.1:5174',
    username: process.env.STAGE8_REAL_USERNAME || process.env.INITIAL_ADMIN_USERNAME || localEnv.INITIAL_ADMIN_USERNAME,
    password: process.env.STAGE8_REAL_PASSWORD || process.env.INITIAL_ADMIN_PASSWORD || localEnv.INITIAL_ADMIN_PASSWORD,
  }
}

async function login(page: Page, baseUrl: string, username: string, password: string) {
  await page.goto(`${baseUrl}/login`)
  await page.getByLabel('账号', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '进入平台' }).click()
  await expect(page.getByRole('navigation', { name: '平台导航' })).toBeVisible()
}

async function expectAcceptedOrLocked(responseStatus: number) {
  expect([202, 409]).toContain(responseStatus)
}

test('AI 真实验收：5174 模块筛选、按钮动作和右侧用例详情抽屉', async ({ page }) => {
  test.skip(process.env.STAGE8_REAL_ACCEPTANCE !== '1', '设置 STAGE8_REAL_ACCEPTANCE=1 后执行真实 5174 验收。')
  const config = realAcceptanceConfig()
  test.skip(!config.username || !config.password, '真实验收需要本地 .env 或环境变量提供平台管理员账号。')

  await login(page, config.baseUrl, config.username ?? '', config.password ?? '')

  const filterOptionsResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots/filter-options') && response.status() === 200,
  )
  await page.goto(`${config.baseUrl}/modules?environment_id=1&sort=pass_rate,-completed_at`)
  const filterOptions = await filterOptionsResponse
  const filterOptionsPayload = await filterOptions.json()
  expect(filterOptionsPayload.data.module_names.map((option: FilterOptionPayload) => option.value)).toEqual(['物种数据1', '物种数据2'])
  expect(filterOptionsPayload.data.package_names.map((option: FilterOptionPayload) => option.value)).toEqual([
    'test_gbif_case',
    'test_gbif_case_module2',
  ])
  await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
  await expect(page.getByText('筛选选项加载失败，可稍后重试。')).toHaveCount(0)

  await page.getByTestId('module-name-filter').click()
  await expect(page.locator('.el-select-dropdown__item').filter({ hasText: '物种数据1' })).toBeVisible()
  const autoFilterResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots?') && response.status() === 200,
  )
  await page.locator('.el-select-dropdown__item').filter({ hasText: '物种数据1' }).click()
  await autoFilterResponse
  await expect.poll(() => new URL(page.url()).searchParams.get('module_name')).toBe('物种数据1')
  await expect(page.getByRole('button', { name: '查询', exact: true })).toHaveCount(0)
  await page.keyboard.press('Escape')

  const resetResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots?') && response.status() === 200,
  )
  await page.getByRole('button', { name: '重置' }).click()
  await resetResponse

  const jenkinsTasksResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots/') && response.url().includes('/jenkins-tasks') && response.status() === 200,
  )
  await page.getByRole('button', { name: 'Jenkins 任务' }).first().click()
  await jenkinsTasksResponse
  const jenkinsDialog = page.getByRole('dialog', { name: /Jenkins 任务/ })
  await expect(jenkinsDialog).toBeVisible()
  const viewReportLink = jenkinsDialog.getByRole('link', { name: '查看报告' }).first()
  if (await viewReportLink.isVisible()) {
    const reportPopupPromise = page.waitForEvent('popup')
    await viewReportLink.click()
    const reportPopup = await reportPopupPromise
    await expect(reportPopup).toHaveURL(/\/job\/.+\/\d+\/allure\/?$/)
    await reportPopup.close()
  }
  const viewJenkinsLink = jenkinsDialog.getByRole('link', { name: '查看 Jenkins 任务' }).first()
  if (await viewJenkinsLink.isVisible()) {
    const jenkinsPopupPromise = page.waitForEvent('popup')
    await viewJenkinsLink.click()
    const jenkinsPopup = await jenkinsPopupPromise
    await expect(jenkinsPopup).toHaveURL(/\/job\/.+\/\d+\/?$/)
    await jenkinsPopup.close()
  }
  const cancelButton = jenkinsDialog.getByRole('button', { name: '取消任务' }).first()
  if ((await cancelButton.count()) > 0 && await cancelButton.isEnabled()) {
    const cancelResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/jenkins-tasks/') && response.url().includes('/cancel'),
    )
    await cancelButton.click()
    const cancelResponse = await cancelResponsePromise
    expect(cancelResponse.status()).not.toBe(503)
  }
  await page.keyboard.press('Escape')

  const casesResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots/') && response.url().includes('/cases') && response.status() === 200,
  )
  await page.getByRole('button', { name: /查看.*用例详情/ }).first().click()
  await casesResponse
  const drawer = page.locator('.case-detail-drawer')
  await expect(drawer).toBeVisible()
  const drawerBox = await drawer.boundingBox()
  const viewport = page.viewportSize()
  expect(drawerBox?.width ?? 0).toBeGreaterThanOrEqual((viewport?.width ?? 0) * 0.68)

  await expect(drawer.getByRole('button', { name: '一键失败重试', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')

  await page.getByRole('navigation', { name: '平台导航' }).getByRole('link', { name: '模块通过率' }).click()
  await page.getByRole('navigation', { name: '平台导航' }).getByRole('link', { name: '模块通过率' }).click()
  await expect.poll(() => new URL(page.url()).searchParams.get('environment_id')).toBe('1')
  await expect(page.getByText('暂无模块快照')).toHaveCount(0)

  await expect(page.locator('.table-frame').getByRole('button', { name: '失败重试', exact: true })).toHaveCount(0)
  const listRetryResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots/') && response.url().includes('/failed-case-retries'),
  )
  await page.locator('.table-frame').getByRole('button', { name: '一键失败重试', exact: true }).first().click()
  const listRetry = await listRetryResponse
  await expectAcceptedOrLocked(listRetry.status())
  if (listRetry.status() === 202) {
    await expect(page.getByText('开始执行失败重试')).toBeVisible()
  } else {
    await expect(page.getByText(expectedLockedMessage)).toBeVisible()
  }

  await page.getByRole('button', { name: '模块重试' }).last().click()
  await expect(page.getByText('模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？')).toBeVisible()
  const moduleRerunResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/module-snapshots/') && response.url().includes('/module-reruns'),
  )
  await page.getByRole('button', { name: '确认模块重试' }).click()
  const moduleRerun = await moduleRerunResponse
  await expectAcceptedOrLocked(moduleRerun.status())
  if (moduleRerun.status() === 409) {
    await expect(page.getByText(expectedLockedMessage)).toBeVisible()
  }

  mkdirSync(dirname(evidencePath), { recursive: true })
  await page.screenshot({ path: evidencePath, fullPage: true })
})
