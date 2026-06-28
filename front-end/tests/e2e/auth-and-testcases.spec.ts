import { expect, test } from '@playwright/test'

test.describe('用户登录注册和测试用例展示', () => {
  test('未登录访问测试用例页会跳转到登录页', async ({ page }) => {
    await page.goto('/test-cases')

    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: '登录 AiApiTest-DWP' })).toBeVisible()
  })

  test('用户可以注册后登录并查看测试用例列表', async ({ page }) => {
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            id: 7,
            username: 'newmember',
            email: 'newmember@example.com',
            role: 'member',
            status: 'active',
          },
        }),
      })
    })
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            token: 'test-token',
            user: {
              id: 7,
              username: 'newmember',
              email: 'newmember@example.com',
              role: 'member',
              status: 'active',
            },
          },
        }),
      })
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            id: 7,
            username: 'newmember',
            email: 'newmember@example.com',
            role: 'member',
            status: 'active',
          },
        }),
      })
    })
    await page.route('**/api/v1/test-cases**', async (route) => {
      if (route.request().url().includes('/api/v1/test-cases/sync')) {
        await route.fallback()
        return
      }
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

    await page.goto('/register')
    await page.getByLabel('邀请码').fill('INVITE-001')
    await page.getByLabel('用户名').fill('newmember')
    await page.getByLabel('邮箱').fill('newmember@example.com')
    await page.getByLabel('密码', { exact: true }).fill('StrongPass123')
    await page.getByLabel('确认密码').fill('StrongPass123')
    await page.getByRole('button', { name: '创建账号' }).click()
    await expect(page.getByText('注册成功，请登录')).toBeVisible()

    await page.getByLabel('账号').fill('newmember@example.com')
    await page.getByLabel('密码').fill('StrongPass123')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/test-cases/)
    await expect(page.getByRole('heading', { name: '测试用例展示' })).toBeVisible()
    await expect(page.getByText('test_login', { exact: true })).toBeVisible()
    await expect(page.getByText('Demo 模块')).toBeVisible()
  })

  test('admin 可以管理邀请码并同步测试用例', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            token: 'admin-token',
            user: { id: 1, username: 'admin', email: 'admin@example.com', role: 'admin', status: 'active' },
          },
        }),
      })
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
    await page.route('**/api/v1/invite-codes**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              id: 10,
              code: 'INVITE-ADMIN',
              status: 'active',
              max_uses: 5,
              used_count: 0,
              expires_at: null,
              created_by: { id: 1, username: 'admin' },
              created_at: '2026-06-28T10:00:00+08:00',
            },
          }),
        })
        return
      }
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
              used_count: 0,
              expires_at: null,
              created_by: { id: 1, username: 'admin' },
              created_at: '2026-06-28T10:00:00+08:00',
            },
          ],
          meta: { total: 1, page: 1, page_size: 20, total_pages: 1 },
        }),
      })
    })
    await page.route('**/api/v1/test-cases/sync', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: { created: 1, updated: 2, missing: 0, total: 3 } }),
      })
    })
    await page.route('**/api/v1/test-cases**', async (route) => {
      if (route.request().url().includes('/api/v1/test-cases/sync')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: { created: 1, updated: 2, missing: 0, total: 3 } }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], meta: { total: 0, page: 1, page_size: 20, total_pages: 0 } }),
      })
    })

    await page.goto('/login')
    await page.getByLabel('账号').fill('admin@example.com')
    await page.getByLabel('密码').fill('StrongPass123')
    await page.getByRole('button', { name: '登录' }).click()

    await page.getByRole('link', { name: '邀请码管理' }).click()
    await page.getByLabel('邀请码').fill('INVITE-ADMIN')
    await page.getByLabel('最大使用次数').fill('5')
    await page.getByRole('button', { name: '创建邀请码' }).click()
    await expect(page.getByText('INVITE-ADMIN')).toBeVisible()

    await page.getByRole('link', { name: '测试用例' }).click()
    await page.getByRole('button', { name: '同步用例' }).click()
    await expect(page.getByText('同步完成：新增 1，更新 2，总数 3')).toBeVisible()
  })

  test('member 不能通过直达地址访问邀请码管理', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('aiapitest_token', 'member-token')
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            id: 7,
            username: 'member',
            email: 'member@example.com',
            role: 'member',
            status: 'active',
          },
        }),
      })
    })
    await page.route('**/api/v1/test-cases**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], meta: { total: 0, page: 1, page_size: 20, total_pages: 0 } }),
      })
    })

    await page.goto('/invite-codes')

    await expect(page).toHaveURL(/\/test-cases/)
    await expect(page.getByRole('link', { name: '邀请码管理' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: '测试用例展示' })).toBeVisible()
  })

  test('admin 可以禁用可用邀请码', async ({ page }) => {
    let inviteStatus = 'active'
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
    await page.route('**/api/v1/invite-codes**', async (route) => {
      if (route.request().url().includes('/disable')) {
        inviteStatus = 'disabled'
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              id: 10,
              code: 'INVITE-DISABLE',
              status: 'disabled',
              max_uses: 5,
              used_count: 0,
              expires_at: null,
              created_by: { id: 1, username: 'admin' },
              created_at: '2026-06-28T10:00:00+08:00',
            },
          }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            {
              id: 10,
              code: 'INVITE-DISABLE',
              status: inviteStatus,
              max_uses: 5,
              used_count: 0,
              expires_at: null,
              created_by: { id: 1, username: 'admin' },
              created_at: '2026-06-28T10:00:00+08:00',
            },
          ],
          meta: { total: 1, page: 1, page_size: 20, total_pages: 1 },
        }),
      })
    })

    await page.goto('/invite-codes')
    await expect(page.getByText('INVITE-DISABLE')).toBeVisible()

    await page.getByRole('button', { name: '禁用' }).click()
    await page.getByRole('button', { name: '禁用' }).last().click()

    await expect(page.getByText('邀请码已禁用')).toBeVisible()
    await expect(page.getByRole('row', { name: /INVITE-DISABLE 已禁用 5 0 admin/ })).toBeVisible()
  })

  test('注册错误会展示字段级反馈', async ({ page }) => {
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'validation_error',
            message: '请求参数不合法',
            details: [
              { field: 'password_confirm', message: '两次密码不一致' },
              { field: 'invite_code', message: '邀请码不存在' },
            ],
          },
        }),
      })
    })

    await page.goto('/register')
    await page.getByLabel('邀请码').fill('BAD001')
    await page.getByLabel('用户名').fill('newmember')
    await page.getByLabel('邮箱').fill('newmember@example.com')
    await page.getByLabel('密码', { exact: true }).fill('StrongPass123')
    await page.getByLabel('确认密码').fill('Mismatch123')
    await page.getByRole('button', { name: '创建账号' }).click()

    await expect(page.getByText('邀请码不存在')).toBeVisible()
    await expect(page.getByText('两次密码不一致')).toBeVisible()
  })

  test('邀请码创建错误会展示字段级反馈', async ({ page }) => {
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
    await page.route('**/api/v1/invite-codes**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'validation_error',
              message: '请求参数不合法',
              details: [
                { field: 'code', message: '邀请码长度不能少于 6 个字符' },
                { field: 'max_uses', message: '最大使用次数必须大于等于 1' },
              ],
            },
          }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], meta: { total: 0, page: 1, page_size: 20, total_pages: 0 } }),
      })
    })

    await page.goto('/invite-codes')
    await page.getByLabel('邀请码').fill('BAD')
    await page.getByLabel('最大使用次数').fill('1')
    await page.getByRole('button', { name: '创建邀请码' }).click()

    await expect(page.getByText('邀请码长度不能少于 6 个字符')).toBeVisible()
    await expect(page.getByText('最大使用次数必须大于等于 1')).toBeVisible()
  })

  test('测试用例列表展示类名并按分页参数请求', async ({ page }) => {
    const requests: string[] = []
    await page.addInitScript(() => {
      window.localStorage.setItem('aiapitest_token', 'member-token')
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { id: 7, username: 'member', email: 'member@example.com', role: 'member', status: 'active' },
        }),
      })
    })
    await page.route('**/api/v1/test-cases**', async (route) => {
      requests.push(route.request().url())
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
          meta: { total: 21, page: 1, page_size: 20, total_pages: 2 },
        }),
      })
    })

    await page.goto('/test-cases')
    await expect(page.getByText('TestDemo', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Go to next page' })).toBeVisible()
    await page.getByRole('button', { name: 'Go to next page' }).click()

    await expect.poll(() => requests.some((url) => url.includes('page=2') && url.includes('page_size=20'))).toBe(true)
  })

  test('认证凭据失效时清空登录态并跳转登录页', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('aiapitest_token', 'expired-token')
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'unauthorized', message: '请先登录' } }),
      })
    })

    await page.goto('/test-cases')

    await expect(page).toHaveURL(/\/login/)
    await expect.poll(() => page.evaluate(() => window.localStorage.getItem('aiapitest_token'))).toBeNull()
  })
})
