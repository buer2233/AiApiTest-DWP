import { expect, request as playwrightRequest, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

type EnvMap = Record<string, string>
type Snapshot = {
  id: number
  package_name: string
  module_name: string
  total_count: number
}
type JenkinsTask = {
  id: number
  status: string
  jenkins_build_url: string
  allure_report_url: string
}

const evidencePath = resolve(
  process.cwd(),
  '..',
  'project-info',
  'test_case',
  'Stage10-Jenkins执行闭环二次验收修复',
  '环境与模块通过率页面-Jenkins执行闭环二次验收修复-Playwright验收.png',
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
  const taskList = await page.request.get(`${baseUrl}/api/v1/module-snapshots/${snapshotId}/jenkins-tasks`, {
    params: { date: 'today', page: 1, per_page: 100 },
  })
  expect(taskList.status()).toBe(200)
  let activeTasks = ((await taskList.json()).data as JenkinsTask[]).filter((item) =>
    ['queued', 'running', 'canceling'].includes(item.status),
  )
  const deadline = Date.now() + 3 * 60 * 1000
  while (activeTasks.length > 0 && Date.now() < deadline) {
    const synced = await Promise.all(
      activeTasks.map(async (task) => {
        const response = await page.request.post(`${baseUrl}/api/v1/jenkins-tasks/${task.id}/sync`)
        expect(response.status()).toBe(200)
        return (await response.json()).data as JenkinsTask
      }),
    )
    activeTasks = synced.filter((item) => ['queued', 'running', 'canceling'].includes(item.status))
    if (activeTasks.length > 0) {
      await page.waitForTimeout(1000)
    }
  }
  expect(activeTasks).toHaveLength(0)
}

test('Stage10 真实验收：Jenkins 并发、实时日志、报告入口、禁用态和三状态用例', async ({ page }) => {
  test.skip(process.env.STAGE10_REAL_ACCEPTANCE !== '1', '设置 STAGE10_REAL_ACCEPTANCE=1 后执行真实验收。')
  test.setTimeout(12 * 60 * 1000)
  const env = readLocalEnv()
  const baseUrl = process.env.STAGE10_REAL_BASE_URL || 'http://127.0.0.1:5173'
  const username = process.env.STAGE10_REAL_USERNAME || env.INITIAL_ADMIN_USERNAME
  const password = process.env.STAGE10_REAL_PASSWORD || env.INITIAL_ADMIN_PASSWORD
  const jenkinsUsername = process.env.STAGE10_JENKINS_USERNAME || process.env.JENKINS_USERNAME || env.JENKINS_USERNAME
  const jenkinsToken = process.env.STAGE10_JENKINS_TOKEN || process.env.JENKINS_API_TOKEN || env.JENKINS_API_TOKEN
  test.skip(!username || !password || !jenkinsUsername || !jenkinsToken, '真实验收缺少本地私有账号配置。')

  await login(page, baseUrl, username, password)
  await page.goto(`${baseUrl}/modules?environment_id=1&sort=pass_rate,-completed_at`)
  await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()

  const snapshotsResponse = await page.request.get(`${baseUrl}/api/v1/module-snapshots`, {
    params: { environment_id: 1, sort: 'pass_rate,-completed_at', per_page: 100 },
  })
  expect(snapshotsResponse.status()).toBe(200)
  const snapshots = (await snapshotsResponse.json()).data as Snapshot[]
  const module1 = snapshots.find((item) => item.package_name === 'test_gbif_case')
  const module2 = snapshots.find((item) => item.package_name === 'test_gbif_case_module2')
  expect(module1).toBeTruthy()
  expect(module2).toBeTruthy()

  await Promise.all([
    settleActiveTasks(page, baseUrl, module1!.id),
    settleActiveTasks(page, baseUrl, module2!.id),
  ])
  const [task1Response, task2Response] = await Promise.all([
    page.request.post(`${baseUrl}/api/v1/module-snapshots/${module1!.id}/module-reruns`, { data: {} }),
    page.request.post(`${baseUrl}/api/v1/module-snapshots/${module2!.id}/module-reruns`, { data: {} }),
  ])
  expect(task1Response.status()).toBe(202)
  expect(task2Response.status()).toBe(202)
  const task1 = (await task1Response.json()).data as JenkinsTask
  const task2 = (await task2Response.json()).data as JenkinsTask
  const jenkinsApi = await playwrightRequest.newContext({
    extraHTTPHeaders: {
      Authorization: `Basic ${Buffer.from(`${jenkinsUsername}:${jenkinsToken}`).toString('base64')}`,
    },
  })

  let current1 = task1
  let current2 = task2
  let concurrentRunningSeen = false
  let realtimePytestLogSeen = false
  const terminalStatuses = new Set(['success', 'test_failed', 'failed', 'canceled'])
  const deadline = Date.now() + 8 * 60 * 1000
  while (Date.now() < deadline) {
    const [sync1, sync2] = await Promise.all([
      page.request.post(`${baseUrl}/api/v1/jenkins-tasks/${task1.id}/sync`),
      page.request.post(`${baseUrl}/api/v1/jenkins-tasks/${task2.id}/sync`),
    ])
    expect(sync1.status()).toBe(200)
    expect(sync2.status()).toBe(200)
    current1 = (await sync1.json()).data as JenkinsTask
    current2 = (await sync2.json()).data as JenkinsTask
    concurrentRunningSeen ||= current1.status === 'running' && current2.status === 'running'

    const runningTask = [current1, current2].find((item) => item.status === 'running' && item.jenkins_build_url)
    if (runningTask) {
      const [logResponse, buildResponse] = await Promise.all([
        jenkinsApi.get(`${runningTask.jenkins_build_url}logText/progressiveText?start=0`),
        jenkinsApi.get(`${runningTask.jenkins_build_url}api/json?tree=building`),
      ])
      if (logResponse.ok() && buildResponse.ok()) {
        const logText = await logResponse.text()
        const buildState = (await buildResponse.json()) as { building: boolean }
        realtimePytestLogSeen ||=
          buildState.building && logText.includes('test session starts') && logText.includes('::test_')
      }
    }

    if (terminalStatuses.has(current1.status) && terminalStatuses.has(current2.status)) {
      break
    }
    await page.waitForTimeout(1000)
  }
  await jenkinsApi.dispose()

  expect(concurrentRunningSeen).toBe(true)
  expect(realtimePytestLogSeen).toBe(true)
  expect(terminalStatuses.has(current1.status)).toBe(true)
  expect(terminalStatuses.has(current2.status)).toBe(true)
  expect(current2.jenkins_build_url).toMatch(/\/job\/AiApiTest-DWP-Module-Rerun\/\d+\/$/)
  expect(current2.allure_report_url).toBe(`${current2.jenkins_build_url}allure/`)

  await page.reload()
  const module2Row = page.locator('.el-table__row').filter({ hasText: module2!.package_name }).first()
  await module2Row.getByRole('button', { name: 'Jenkins 任务', exact: true }).click()
  const jenkinsDialog = page.getByRole('dialog', { name: /Jenkins 任务/ })
  const taskRow = jenkinsDialog.locator('tbody tr').filter({ hasText: `#${task2.id}` })
  await expect(taskRow).toBeVisible()
  const reportLink = taskRow.getByRole('link', { name: '查看报告' })
  await expect(reportLink).toHaveAttribute('href', current2.allure_report_url)
  const reportPopupPromise = page.waitForEvent('popup')
  await reportLink.click()
  const reportPopup = await reportPopupPromise
  await reportPopup.waitForLoadState('domcontentloaded')
  const popupUrl = new URL(reportPopup.url())
  const expectedReportPath = new URL(current2.allure_report_url).pathname
  if (popupUrl.pathname === '/login') {
    expect(popupUrl.searchParams.get('from')).toBe(expectedReportPath)
  } else {
    expect(popupUrl.pathname).toBe(expectedReportPath)
  }
  await reportPopup.close()

  const cancelButton = taskRow.getByRole('button', { name: '取消任务' })
  await expect(cancelButton).toBeDisabled()
  const disabledStyle = await cancelButton.evaluate((element) => {
    const style = window.getComputedStyle(element)
    return {
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
      color: style.color,
      cursor: style.cursor,
    }
  })
  expect(disabledStyle).toEqual({
    backgroundColor: 'rgb(231, 231, 227)',
    borderColor: 'rgb(206, 206, 200)',
    color: 'rgb(133, 133, 127)',
    cursor: 'not-allowed',
  })
  await page.keyboard.press('Escape')

  const caseResponses = await Promise.all(
    ['failed', 'passed', 'skipped'].map(async (status) => {
      const response = await page.request.get(`${baseUrl}/api/v1/module-snapshots/${module2!.id}/cases`, {
        params: { status, page: 1, per_page: 100 },
      })
      expect(response.status()).toBe(200)
      return { status, payload: await response.json() }
    }),
  )
  for (const result of caseResponses) {
    expect(result.payload.meta.total, `${result.status} 用例应有数据`).toBeGreaterThan(0)
    expect(result.payload.data.every((item: { display_status: string }) => item.display_status === result.status)).toBe(true)
  }
  const caseTotal = caseResponses.reduce((total, result) => total + result.payload.meta.total, 0)
  const refreshedSnapshots = await page.request.get(`${baseUrl}/api/v1/module-snapshots`, {
    params: { environment_id: 1, per_page: 100 },
  })
  const refreshedModule2 = ((await refreshedSnapshots.json()).data as Snapshot[]).find((item) => item.id === module2!.id)
  expect(caseTotal).toBe(refreshedModule2!.total_count)

  mkdirSync(dirname(evidencePath), { recursive: true })
  await page.screenshot({ path: evidencePath, fullPage: true })
})
