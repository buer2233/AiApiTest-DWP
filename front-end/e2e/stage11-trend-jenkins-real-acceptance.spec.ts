import { expect, request as playwrightRequest, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

type EnvMap = Record<string, string>
type Snapshot = { id: number; package_name: string; module_name: string }
type JenkinsTask = { id: number; status: string; jenkins_build_url: string }
type TrendPoint = { run_date: string; run_type: string; pass_rate: string }
type TrendPayload = { days: 7 | 30; series: TrendPoint[] }

const evidenceDir = resolve(
  process.cwd(),
  '..',
  'project-info',
  'test_case',
  'Stage11-Jenkins依赖复用与趋势图修复',
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

async function settleActiveTasks(page: Page, baseUrl: string, snapshotId: number) {
  const deadline = Date.now() + 3 * 60 * 1000
  while (Date.now() < deadline) {
    const response = await page.request.get(`${baseUrl}/api/v1/module-snapshots/${snapshotId}/jenkins-tasks`, {
      params: { date: 'today', page: 1, per_page: 100 },
    })
    expect(response.status()).toBe(200)
    const active = ((await response.json()).data as JenkinsTask[]).filter((task) =>
      ['queued', 'running', 'canceling'].includes(task.status),
    )
    if (active.length === 0) {
      return
    }
    await Promise.all(active.map((task) => page.request.post(`${baseUrl}/api/v1/jenkins-tasks/${task.id}/sync`)))
    await page.waitForTimeout(1000)
  }
  throw new Error('等待模块现有 Jenkins 任务结束超时。')
}

function expectDailyUnique(trend: TrendPayload) {
  const dates = trend.series.map((point) => point.run_date)
  expect(new Set(dates).size).toBe(dates.length)
  expect(dates).toEqual([...dates].sort())
  expect(trend.series.length).toBeLessThanOrEqual(trend.days)
}

test('Stage11 真实验收：模块依赖跳过、每日趋势去重和真实折线图', async ({ page }) => {
  test.skip(process.env.STAGE11_REAL_ACCEPTANCE !== '1', '设置 STAGE11_REAL_ACCEPTANCE=1 后执行真实验收。')
  test.setTimeout(12 * 60 * 1000)
  const env = readLocalEnv()
  const baseUrl = process.env.STAGE11_REAL_BASE_URL || 'http://127.0.0.1:5173'
  const environmentId = process.env.STAGE11_REAL_ENVIRONMENT_ID || '1'
  const packageName = process.env.STAGE11_REAL_PACKAGE_NAME || 'test_gbif_case_module2'
  const username = process.env.STAGE11_REAL_USERNAME || env.INITIAL_ADMIN_USERNAME
  const password = process.env.STAGE11_REAL_PASSWORD || env.INITIAL_ADMIN_PASSWORD
  const jenkinsUsername = process.env.STAGE11_JENKINS_USERNAME || process.env.JENKINS_USERNAME || env.JENKINS_USERNAME
  const jenkinsToken = process.env.STAGE11_JENKINS_TOKEN || process.env.JENKINS_API_TOKEN || env.JENKINS_API_TOKEN
  test.skip(!username || !password || !jenkinsUsername || !jenkinsToken, '真实验收缺少本地私有账号配置。')

  await login(page, baseUrl, username, password)
  await page.goto(`${baseUrl}/modules?environment_id=${environmentId}&sort=pass_rate,-completed_at`)
  const snapshotsResponse = await page.request.get(`${baseUrl}/api/v1/module-snapshots`, {
    params: { environment_id: environmentId, per_page: 100 },
  })
  expect(snapshotsResponse.status()).toBe(200)
  const module2 = ((await snapshotsResponse.json()).data as Snapshot[]).find(
    (snapshot) => snapshot.package_name === packageName,
  )
  expect(module2).toBeTruthy()

  await settleActiveTasks(page, baseUrl, module2!.id)
  const trigger = await page.request.post(`${baseUrl}/api/v1/module-snapshots/${module2!.id}/module-reruns`, { data: {} })
  expect(trigger.status()).toBe(202)
  const task = (await trigger.json()).data as JenkinsTask
  const jenkinsApi = await playwrightRequest.newContext({
    extraHTTPHeaders: {
      Authorization: `Basic ${Buffer.from(`${jenkinsUsername}:${jenkinsToken}`).toString('base64')}`,
    },
  })
  const terminalStatuses = new Set(['success', 'test_failed', 'failed', 'canceled'])
  let current = task
  let dependencySkipSeen = false
  let dependencyInstallSeen = false
  const deadline = Date.now() + 8 * 60 * 1000
  while (Date.now() < deadline) {
    const sync = await page.request.post(`${baseUrl}/api/v1/jenkins-tasks/${task.id}/sync`)
    expect(sync.status()).toBe(200)
    current = (await sync.json()).data as JenkinsTask
    if (current.jenkins_build_url) {
      const consoleResponse = await jenkinsApi.get(`${current.jenkins_build_url}consoleText`)
      if (consoleResponse.ok()) {
        const consoleText = await consoleResponse.text()
        dependencySkipSeen ||= consoleText.includes('All requirements already satisfied; skip pip install.')
        dependencyInstallSeen ||=
          consoleText.includes('Installing missing requirements:') || consoleText.includes('Successfully installed')
      }
    }
    if (terminalStatuses.has(current.status)) {
      break
    }
    await page.waitForTimeout(1000)
  }
  await jenkinsApi.dispose()
  expect(['success', 'test_failed']).toContain(current.status)
  expect(dependencySkipSeen).toBe(true)
  expect(dependencyInstallSeen).toBe(false)

  const [trend7Response, trend30Response] = await Promise.all([
    page.request.get(`${baseUrl}/api/v1/module-snapshots/${module2!.id}/trend`, { params: { days: 7 } }),
    page.request.get(`${baseUrl}/api/v1/module-snapshots/${module2!.id}/trend`, { params: { days: 30 } }),
  ])
  expect(trend7Response.status()).toBe(200)
  expect(trend30Response.status()).toBe(200)
  const trend7 = (await trend7Response.json()).data as TrendPayload
  const trend30 = (await trend30Response.json()).data as TrendPayload
  expectDailyUnique(trend7)
  expectDailyUnique(trend30)
  expect(trend7.series.at(-1)?.run_type).toBe('module_rerun')
  expect(trend30.series.at(-1)?.run_type).toBe('module_rerun')

  await page.reload()
  const moduleRow = page.locator('.el-table__row').filter({ hasText: module2!.package_name }).first()
  await moduleRow.getByRole('button', { name: '7天趋势', exact: true }).click()
  const trend7Dialog = page.getByRole('dialog', { name: /近 7 天趋势/ })
  const chart7 = trend7Dialog.getByRole('group', { name: '通过率趋势折线图' })
  await expect(chart7.locator('circle')).toHaveCount(trend7.series.length)
  await expect(chart7.locator('.trend-dialog__axis-label--y')).toHaveText(['100%', '50%', '0%'])
  await expect(chart7.locator('polyline')).not.toHaveAttribute('points', /NaN/)
  const lastPoint = chart7.locator('circle').last()
  await expect(lastPoint).toHaveAttribute('aria-label', new RegExp(trend7.series.at(-1)!.run_date))
  await expect(chart7.getByRole('img', { name: new RegExp(trend7.series.at(-1)!.run_date) })).toBeVisible()
  await lastPoint.focus()
  await expect(lastPoint).toBeFocused()
  mkdirSync(evidenceDir, { recursive: true })
  await page.screenshot({
    path: resolve(evidenceDir, '环境与模块通过率页面-Jenkins依赖复用与趋势图修复-Playwright验收-桌面.png'),
    fullPage: true,
  })
  await trend7Dialog.getByRole('button', { name: '关闭' }).click()

  await moduleRow.getByRole('button', { name: '30天趋势', exact: true }).click()
  const trend30Dialog = page.getByRole('dialog', { name: /近 30 天趋势/ })
  await expect(trend30Dialog).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  const chart30 = trend30Dialog.getByRole('group', { name: '通过率趋势折线图' })
  await expect(chart30.locator('circle')).toHaveCount(trend30.series.length)
  expect(await chart30.locator('.trend-dialog__axis-label--x').count()).toBeLessThanOrEqual(7)
  const labelBoxes = await chart30.locator('.trend-dialog__axis-label--x').evaluateAll((labels) =>
    labels.map((label) => {
      const box = label.getBoundingClientRect()
      return { left: box.left, right: box.right, height: box.height }
    }),
  )
  expect(labelBoxes.length).toBeGreaterThanOrEqual(2)
  expect(Math.min(...labelBoxes.map((box) => box.height))).toBeGreaterThanOrEqual(8)
  expect(labelBoxes.every((box, index) => index === 0 || labelBoxes[index - 1].right <= box.left + 1)).toBe(true)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
  await page.waitForTimeout(350)
  await page.screenshot({
    path: resolve(evidenceDir, '环境与模块通过率页面-Jenkins依赖复用与趋势图修复-Playwright验收-移动端.png'),
    fullPage: true,
  })
})
