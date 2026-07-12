import { expect, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

type EnvMap = Record<string, string>
type Snapshot = {
  id: number
  package_name: string
  completed_at: string
  duration_seconds: string
}
type TrendPoint = { run_date: string; run_type: string }

const evidenceDir = resolve(
  process.cwd(),
  '..',
  'project-info',
  'test_case',
  'Stage12-模块快照日期与Jenkins自动同步修复',
)

function readLocalEnv(): EnvMap {
  const values: EnvMap = {}
  try {
    for (const line of readFileSync(resolve(process.cwd(), '..', '.env'), 'utf-8').split(/\r?\n/)) {
      const match = line.match(/^([^#][^=]+)=(.*)$/)
      if (match) {
        values[match[1].trim()] = match[2].trim().replace(/^['"]|['"]$/g, '')
      }
    }
  } catch {
    return values
  }
  return values
}

async function login(page: Page, baseUrl: string, username: string, password: string) {
  await page.goto(`${baseUrl}/login`)
  await page.getByLabel('账号', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '进入平台' }).click()
  await expect(page.getByRole('navigation', { name: '平台导航' })).toBeVisible()
}

test('Stage12 真实验收：模块日期、30 天趋势和 Jenkins 任务同步闭环', async ({ page, baseURL }) => {
  test.skip(process.env.STAGE12_REAL_ACCEPTANCE !== '1', '设置 STAGE12_REAL_ACCEPTANCE=1 后执行真实验收。')
  const env = readLocalEnv()
  const configuredBaseUrl = process.env.STAGE12_REAL_BASE_URL || baseURL
  test.skip(!configuredBaseUrl, '真实验收缺少 Playwright baseURL 配置。')
  const baseUrl = configuredBaseUrl as string
  const username = process.env.STAGE12_REAL_USERNAME || env.INITIAL_ADMIN_USERNAME
  const password = process.env.STAGE12_REAL_PASSWORD || env.INITIAL_ADMIN_PASSWORD
  test.skip(!username || !password, '真实验收缺少本地私有管理员配置。')

  await login(page, baseUrl, username, password)
  await page.goto(`${baseUrl}/modules?environment_id=1&sort=pass_rate,-completed_at`)

  const snapshotsResponse = await page.request.get(`${baseUrl}/api/v1/module-snapshots`, {
    params: { environment_id: 1, sort: 'pass_rate,-completed_at', page: 1, per_page: 20 },
  })
  expect(snapshotsResponse.status()).toBe(200)
  const snapshots = (await snapshotsResponse.json()).data as Snapshot[]
  const module2 = snapshots.find((snapshot) => snapshot.package_name === 'test_gbif_case_module2')
  expect(module2).toBeTruthy()
  expect(module2!.completed_at).toMatch(/^2026-07-12T/)

  const moduleRow = page.locator('.el-table__row').filter({ hasText: 'test_gbif_case_module2' }).first()
  await expect(moduleRow).toContainText('2026/7/12')
  await expect(moduleRow).toContainText(`${Number(module2!.duration_seconds).toFixed(1)}秒`)

  const trendResponse = await page.request.get(`${baseUrl}/api/v1/module-snapshots/${module2!.id}/trend`, {
    params: { days: 30 },
  })
  expect(trendResponse.status()).toBe(200)
  const trend = (await trendResponse.json()).data.series as TrendPoint[]
  expect(trend.some((point) => point.run_date === '2026-07-11' && point.run_type === 'daily_full')).toBe(true)
  expect(trend.some((point) => point.run_date === '2026-07-12' && point.run_type === 'module_rerun')).toBe(true)

  await moduleRow.getByRole('button', { name: '30天趋势', exact: true }).click()
  const trendDialog = page.getByRole('dialog', { name: /近 30 天趋势/ })
  await expect(trendDialog).toContainText('2026-07-11')
  await expect(trendDialog).toContainText('2026-07-12')
  mkdirSync(evidenceDir, { recursive: true })
  await page.screenshot({
    path: resolve(evidenceDir, '环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Playwright验收-桌面.png'),
    fullPage: true,
  })
  await trendDialog.getByRole('button', { name: '关闭' }).click()

  await moduleRow.getByRole('button', { name: 'Jenkins 任务', exact: true }).click()
  const jenkinsDialog = page.getByRole('dialog', { name: /Jenkins 任务/ })
  const recoveredTaskRow = jenkinsDialog.locator('tbody tr').filter({ hasText: '#57' })
  await expect(recoveredTaskRow).toContainText('模块重试')
  await expect(recoveredTaskRow).toContainText('测试失败')
  await expect(recoveredTaskRow).toContainText('2026/7/12')
  await jenkinsDialog.getByRole('button', { name: '关闭' }).click()

  await page.setViewportSize({ width: 390, height: 844 })
  const mobileCard = page.locator('.module-card').filter({ hasText: 'test_gbif_case_module2' }).first()
  await expect(mobileCard).toContainText('2026/7/12')
  await expect(mobileCard).toContainText(`${Number(module2!.duration_seconds).toFixed(1)}秒`)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
  await page.screenshot({
    path: resolve(evidenceDir, '环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Playwright验收-移动端.png'),
    fullPage: true,
  })
})
