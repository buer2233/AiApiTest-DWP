import { expect, test } from '@playwright/test'

async function mockAdminSession(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('aiapitest_token', 'admin-token')
  })
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { id: 1, username: 'admin', email: 'admin@example.com', role: 'admin', status: 'active' },
      }),
    })
  })
  await page.route('**/api/v1/test-cases**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          {
            id: 1,
            node_id: 'test_case/test_demo/test_demo_api.py::TestDemo::test_login',
            package_name: 'test_demo',
            module_name: 'Demo 模块',
            file_path: 'api-test/test_case/test_demo/test_demo_api.py',
            class_name: 'TestDemo',
            function_name: 'test_login',
            title: '登录接口',
            description: '验证登录接口',
            sync_status: 'synced',
            last_synced_at: '2026-06-28T10:00:00+08:00',
          },
        ],
        meta: { total: 1, page: 1, page_size: 20, total_pages: 1 },
      }),
    })
  })
  await page.route('**/api/v1/invite-codes**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          {
            id: 10,
            code: 'INVITE-ADMIN',
            status: 'active',
            max_uses: 5,
            used_count: 1,
            expires_at: null,
            created_by: { id: 1, username: 'admin' },
            created_at: '2026-06-28T10:00:00+08:00',
          },
        ],
        meta: { total: 1, page: 1, page_size: 20, total_pages: 1 },
      }),
    })
  })
}

test.describe('关键页面截图', () => {
  test('保存登录、注册、测试用例和邀请码页面截图', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: '登录 AiApiTest-DWP' })).toBeVisible()
    await page.screenshot({ path: 'tests/screenshots/01-login.png', fullPage: true })

    await page.goto('/register')
    await expect(page.getByRole('heading', { name: '使用邀请码创建账号' })).toBeVisible()
    await page.screenshot({ path: 'tests/screenshots/02-register.png', fullPage: true })

    await mockAdminSession(page)
    await page.goto('/test-cases')
    await expect(page.getByRole('heading', { name: '测试用例展示' })).toBeVisible()
    await page.screenshot({ path: 'tests/screenshots/03-testcases.png', fullPage: true })

    await page.goto('/invite-codes')
    await expect(page.getByRole('heading', { name: '邀请码管理' })).toBeVisible()
    await page.screenshot({ path: 'tests/screenshots/04-invite-codes.png', fullPage: true })
  })
})
