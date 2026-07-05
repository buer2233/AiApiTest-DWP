import { expect, test } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

type LiveAudit = {
  consoleErrors: string[]
  pageErrors: string[]
  requestFailures: string[]
  apiErrors: string[]
}

const auditPath = resolve(process.cwd(), 'tests/evidence/stage6-p5-live-regression-audit-20260705.json')
const screenshotPath = resolve(process.cwd(), 'tests/evidence/screenshots/stage6-p5-live-modules-actual-cases-20260705.png')

function writeAudit(audit: LiveAudit) {
  mkdirSync(dirname(auditPath), { recursive: true })
  writeFileSync(auditPath, `${JSON.stringify(audit, null, 2)}\n`, 'utf-8')
}

test('本地真实服务回归：模块页、实际用例详情、趋势和错误审计', async ({ page }) => {
  test.skip(process.env.P5_LIVE_REGRESSION !== '1', '设置 P5_LIVE_REGRESSION=1 后才执行真实本地服务审计。')

  const username = process.env.P5_LIVE_USERNAME
  const password = process.env.P5_LIVE_PASSWORD
  test.skip(!username || !password, '真实服务审计需要从本地私有环境提供 P5_LIVE_USERNAME/P5_LIVE_PASSWORD。')
  const liveUsername = username ?? ''
  const livePassword = password ?? ''

  await page.goto('/login')
  await page.getByLabel('账号', { exact: true }).fill(liveUsername)
  await page.getByLabel('密码', { exact: true }).fill(livePassword)
  await page.getByRole('button', { name: '进入平台' }).click()
  await expect(page.getByRole('heading', { name: '平台访问已解锁' })).toBeVisible()

  const audit: LiveAudit = {
    consoleErrors: [],
    pageErrors: [],
    requestFailures: [],
    apiErrors: [],
  }
  page.on('console', (message) => {
    if (message.type() === 'error') {
      audit.consoleErrors.push(message.text())
    }
  })
  page.on('pageerror', (error) => audit.pageErrors.push(error.message))
  page.on('requestfailed', (request) => audit.requestFailures.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText ?? ''}`))
  page.on('response', (response) => {
    if (/\/api\/v1\//.test(response.url()) && response.status() >= 400) {
      audit.apiErrors.push(`${response.status()} ${response.url()}`)
    }
  })

  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: '平台访问已解锁' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: '平台导航' }).getByRole('link', { name: /概览/ })).toHaveCount(0)

  await page.goto('/environments')
  await expect(page.getByRole('heading', { name: '环境通过率' })).toBeVisible()

  await page.goto('/modules?environment_id=1')
  await expect(page.getByRole('heading', { name: '模块通过率' })).toBeVisible()
  await expect(page.getByText('test_gbif_case')).toBeVisible()
  await expect(page.getByText('test_gbif_case_module2')).toBeVisible()
  await expect(page.getByRole('link', { name: /AiApiTest-DWP/ })).toHaveAttribute('href', '/environments')

  await page.getByRole('button', { name: /查看.*用例详情/ }).first().click()
  await expect(page.getByLabel('用例详情')).toBeVisible()
  await expect(page.getByText(/test_gbif_api/)).toBeVisible()
  await page.keyboard.press('Escape')

  const trendButton = page.getByRole('button', { name: /7天趋势/ }).first()
  if (await trendButton.isEnabled()) {
    await trendButton.click()
    await expect(page.getByLabel('模块趋势')).toBeVisible()
    await page.keyboard.press('Escape')
  }

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/modules?environment_id=1')
  const horizontalOverflow = await page.evaluate(() => {
    const documentWidth = document.documentElement.clientWidth
    return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - documentWidth
  })
  expect(horizontalOverflow).toBeLessThanOrEqual(1)
  await page.screenshot({ path: screenshotPath, fullPage: true })

  writeAudit(audit)
  expect(audit.consoleErrors).toEqual([])
  expect(audit.pageErrors).toEqual([])
  expect(audit.requestFailures).toEqual([])
  expect(audit.apiErrors).toEqual([])
})
