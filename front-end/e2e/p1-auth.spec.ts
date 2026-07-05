import { expect, test, type Page } from '@playwright/test'

import { playwrightPermissionOrigin } from '../playwright.config'

const adminUser = {
  id: 1,
  username: 'admin_user',
  display_name: '平台管理员',
  role: 'admin',
  permissions: ['users:read', 'invitations:read', 'invitations:create', 'invitations:revoke'],
}

const memberUser = {
  id: 2,
  username: 'member_user',
  display_name: '普通成员',
  role: 'member',
  permissions: ['profile:read'],
}

async function mockApi(page: Page, options: { user?: typeof adminUser | typeof memberUser | null } = {}) {
  let currentUser = options.user ?? null
  let invitationStatus: 'unused' | 'revoked' = 'unused'
  let registerRequestCount = 0

  await page.route('**/api/v1/auth/me', async (route) => {
    if (!currentUser) {
      await route.fulfill({
        status: 401,
        json: { error: { code: 'authentication_required', message: '未登录或登录已过期，请重新登录。', details: [] } },
      })
      return
    }
    await route.fulfill({ status: 200, json: { data: currentUser } })
  })

  await page.route('**/api/v1/auth/login', async (route) => {
    const body = route.request().postDataJSON() as { username: string; password: string }
    if (body.password !== 'TestPass123') {
      await route.fulfill({
        status: 401,
        json: { error: { code: 'invalid_credentials', message: '账户或密码错误。', details: [] } },
      })
      return
    }
    currentUser = adminUser
    await route.fulfill({
      status: 200,
      headers: { 'set-cookie': 'authToken=test-cookie; HttpOnly; SameSite=Lax; Path=/' },
      json: { data: adminUser },
    })
  })

  await page.route('**/api/v1/auth/logout', async (route) => {
    currentUser = null
    await route.fulfill({ status: 204, headers: { 'set-cookie': 'authToken=; Max-Age=0; Path=/' } })
  })

  await page.route('**/api/v1/auth/register', async (route) => {
    registerRequestCount += 1
    const body = route.request().postDataJSON() as { invitation_code: string; username: string; password: string }
    if (body.invitation_code === 'USED-CODE') {
      await route.fulfill({
        status: 422,
        json: { error: { code: 'invalid_invitation_code', message: '邀请码已经被使用。', details: [] } },
      })
      return
    }
    if (body.password === '12345678') {
      await route.fulfill({
        status: 422,
        json: {
          error: {
            code: 'weak_password',
            message: '密码需 8-64 位，至少包含字母和数字；当前缺少字母。',
            details: [],
          },
        },
      })
      return
    }
    await route.fulfill({
      status: 201,
      json: {
        data: {
          id: 3,
          username: body.username,
          display_name: '普通成员01',
          role: 'member',
          created_at: '2026-07-03T10:00:00+08:00',
        },
      },
    })
  })

  await page.route('**/api/v1/users**', async (route) => {
    if (currentUser?.role !== 'admin') {
      await route.fulfill({
        status: 403,
        json: { error: { code: 'admin_required', message: '需要管理人员权限。', details: [] } },
      })
      return
    }
    const url = new URL(route.request().url())
    const role = url.searchParams.get('role')
    const page = Number(url.searchParams.get('page') ?? '1')
    const users = role === 'admin' ? [adminUser] : role === 'member' ? [memberUser] : page === 2 ? [memberUser] : [adminUser, memberUser]
    await route.fulfill({
      status: 200,
      json: {
        data: users,
        meta: { total: role ? 1 : 2, page, per_page: 20, total_pages: role ? 1 : 2 },
      },
    })
  })

  await page.route('**/api/v1/invitations/*/revoke', async (route) => {
    if (currentUser?.role !== 'admin') {
      await route.fulfill({
        status: 403,
        json: { error: { code: 'admin_required', message: '需要管理人员权限。', details: [] } },
      })
      return
    }
    invitationStatus = 'revoked'
    await route.fulfill({
      status: 200,
      json: {
        data: {
          id: 10,
          role: 'member',
          status: invitationStatus,
          expires_at: '2026-07-10T10:00:00+08:00',
          created_by: 'admin_user',
          used_by: null,
          used_at: null,
          revoked_at: '2026-07-03T11:00:00+08:00',
          created_at: '2026-07-03T10:00:00+08:00',
        },
      },
    })
  })

  await page.route('**/api/v1/invitations**', async (route) => {
    if (route.request().url().includes('/revoke')) {
      if (currentUser?.role !== 'admin') {
        await route.fulfill({
          status: 403,
          json: { error: { code: 'admin_required', message: '需要管理人员权限。', details: [] } },
        })
        return
      }
      invitationStatus = 'revoked'
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: 10,
            role: 'member',
            status: invitationStatus,
            expires_at: '2026-07-10T10:00:00+08:00',
            created_by: 'admin_user',
            used_by: null,
            used_at: null,
            revoked_at: '2026-07-03T11:00:00+08:00',
            created_at: '2026-07-03T10:00:00+08:00',
          },
        },
      })
      return
    }

    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { role: 'admin' | 'member'; expires_at?: string }
      await route.fulfill({
        status: 201,
        json: {
          data: {
            id: 10,
            plain_code: 'INVITE-EXAMPLE-REDACTED',
            role: body.role,
            status: 'unused',
            expires_at: body.expires_at || '2026-07-10T10:00:00+08:00',
            created_at: '2026-07-03T10:00:00+08:00',
          },
        },
      })
      return
    }
    const url = new URL(route.request().url())
    const role = url.searchParams.get('role') as 'admin' | 'member' | null
    const status = url.searchParams.get('status') as 'unused' | 'revoked' | null
    const page = Number(url.searchParams.get('page') ?? '1')
    const rowRole = role || 'member'
    const rowStatus = status || invitationStatus
    await route.fulfill({
      status: 200,
      json: {
        data: [
          {
            id: 10,
            role: rowRole,
            status: rowStatus,
            expires_at: '2026-07-10T10:00:00+08:00',
            created_by: 'admin_user',
            used_by: null,
            used_at: null,
            revoked_at: rowStatus === 'revoked' ? '2026-07-03T11:00:00+08:00' : null,
            created_at: '2026-07-03T10:00:00+08:00',
          },
        ],
        meta: { total: 2, page, per_page: 20, total_pages: 2 },
      },
    })
  })

  return {
    get registerRequestCount() {
      return registerRequestCount
    },
  }
}

test.describe('P1 用户权限底座', () => {
  test('未登录用户直达受保护 URL 会回到纯登录页且不展示复合原型其他区域', async ({ page }) => {
    await mockApi(page)

    await page.goto('/dashboard')

    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: '登录' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '邀请码注册' })).toHaveCount(0)
    await expect(page.getByText('选择身份')).toHaveCount(0)
    await expect(page.getByText('401')).toHaveCount(0)
    await expect(page.getByText('authToken Cookie')).toHaveCount(0)
    await expect(page.getByText('未检测到有效 Cookie')).toHaveCount(0)
    await page.screenshot({ path: 'tests/evidence/screenshots/p1-login-redirect.png', fullPage: true })
  })

  test('登录页点击邀请码注册链接后进入独立注册页', async ({ page }) => {
    await mockApi(page)
    await page.goto('/login')

    await expect(page.getByRole('heading', { name: '登录' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '邀请码注册' })).toHaveCount(0)

    await page.getByRole('link', { name: /使用邀请码注册/ }).click()

    await expect(page).toHaveURL(/\/register/)
    await expect(page.getByRole('heading', { name: '邀请码注册' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '登录' })).toHaveCount(0)
    await expect(page.getByText('选择身份')).toHaveCount(0)
    await expect(page.getByText('401')).toHaveCount(0)
    await expect(page.getByText('authToken Cookie')).toHaveCount(0)
    await expect(page.getByText('平台访问已解锁')).toHaveCount(0)
    await page.screenshot({ path: 'tests/evidence/screenshots/p1-register-route.png', fullPage: true })
  })

  test('管理人员登录成功后进入受保护布局', async ({ page }) => {
    await mockApi(page)
    await page.goto('/login')

    await page.getByLabel('账号', { exact: true }).fill('admin_user')
    await page.getByLabel('密码', { exact: true }).fill('TestPass123')
    await page.getByRole('button', { name: '进入平台' }).click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByRole('heading', { name: '平台访问已解锁' })).toBeVisible()
    await expect(page.getByText('平台管理员', { exact: true })).toBeVisible()
    await expect(page.getByRole('navigation', { name: '平台导航' }).getByRole('link', { name: /概览/ })).toHaveCount(0)
    await expect(page.getByRole('link', { name: /AiApiTest-DWP/ })).toHaveAttribute('href', '/environments')
    await page.screenshot({ path: 'tests/evidence/screenshots/p1-dashboard-admin.png', fullPage: true })
  })

  test('退出登录后返回登录页并阻止继续访问受保护 URL', async ({ page }) => {
    await mockApi(page, { user: adminUser })

    await page.goto('/dashboard')
    await page.getByRole('button', { name: '退出登录' }).click()

    await expect(page).toHaveURL(/\/login/)
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: '登录' })).toBeVisible()
    await expect(page.getByText('未检测到有效 Cookie')).toHaveCount(0)
    await expect(page.getByText('401')).toHaveCount(0)
  })

  test('登录密码错误时展示统一账户错误', async ({ page }) => {
    await mockApi(page)
    await page.goto('/login')

    await page.getByLabel('账号', { exact: true }).fill('admin_user')
    await page.getByLabel('密码', { exact: true }).fill('WrongPass123')
    await page.getByRole('button', { name: '进入平台' }).click()

    await expect(page.getByRole('alert')).toContainText('账户或密码错误')
    await expect(page).toHaveURL(/\/login/)
  })

  test('登录短密码错误时仍展示统一账户错误', async ({ page }) => {
    await mockApi(page)
    await page.goto('/login')

    await page.getByLabel('账号', { exact: true }).fill('admin_user')
    await page.getByLabel('密码', { exact: true }).fill('222')
    await page.getByRole('button', { name: '进入平台' }).click()

    await expect(page.getByRole('alert')).toContainText('账户或密码错误')
    await expect(page).toHaveURL(/\/login/)
  })

  test('邀请码注册成功后不自动登录并引导返回登录', async ({ page }) => {
    await mockApi(page)
    await page.goto('/register')

    await expect(page.getByRole('heading', { name: '邀请码注册' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '登录' })).toHaveCount(0)
    await expect(page.getByText('选择身份')).toHaveCount(0)
    await expect(page.getByText('401')).toHaveCount(0)
    await expect(page.getByText('authToken Cookie')).toHaveCount(0)
    await expect(page.getByText('平台访问已解锁')).toHaveCount(0)

    await page.getByLabel('邀请码', { exact: true }).fill('INVITE-EXAMPLE-REDACTED')
    await page.getByLabel('注册账号', { exact: true }).fill('member01')
    await page.getByLabel('注册密码', { exact: true }).fill('MemberPass123')
    await page.getByLabel('确认密码', { exact: true }).fill('MemberPass123')
    await page.getByRole('button', { name: '创建账号' }).click()

    await expect(page.getByRole('status')).toContainText('注册成功，请返回登录')
  })

  test('邀请码注册弱密码时展示缺失项提示', async ({ page }) => {
    await mockApi(page)
    await page.goto('/register')

    await page.getByLabel('邀请码', { exact: true }).fill('INVITE-EXAMPLE-REDACTED')
    await page.getByLabel('注册账号', { exact: true }).fill('weak_member')
    await page.getByLabel('注册密码', { exact: true }).fill('12345678')
    await page.getByLabel('确认密码', { exact: true }).fill('12345678')
    await page.getByRole('button', { name: '创建账号' }).click()

    await expect(page.getByRole('alert')).toContainText('密码需 8-64 位，至少包含字母和数字')
    await expect(page.getByRole('alert')).toContainText('缺少字母')
  })

  test('邀请码注册中文账号时优先提示账号格式且不提交接口', async ({ page }) => {
    const api = await mockApi(page)
    await page.goto('/register')

    await page.getByLabel('邀请码', { exact: true }).fill('INVITE-EXAMPLE-REDACTED')
    await page.getByLabel('注册账号', { exact: true }).fill('中文账号')
    await page.getByLabel('注册密码', { exact: true }).fill('MemberPass123')
    await page.getByLabel('确认密码', { exact: true }).fill('MemberPass123')
    await page.getByRole('button', { name: '创建账号' }).click()

    await expect(page.getByRole('alert')).toContainText('账号只能包含字母、数字、下划线、短横线和点。')
    expect(api.registerRequestCount).toBe(0)
  })

  test('邀请码注册使用已使用邀请码时展示明确状态', async ({ page }) => {
    await mockApi(page)
    await page.goto('/register')

    await page.getByLabel('邀请码', { exact: true }).fill('USED-CODE')
    await page.getByLabel('注册账号', { exact: true }).fill('used_code_member')
    await page.getByLabel('注册密码', { exact: true }).fill('MemberPass123')
    await page.getByLabel('确认密码', { exact: true }).fill('MemberPass123')
    await page.getByRole('button', { name: '创建账号' }).click()

    await expect(page.getByRole('alert')).toContainText('邀请码已经被使用。')
  })

  test('邀请码注册密码不一致时优先提示不一致且不提交接口', async ({ page }) => {
    const api = await mockApi(page)
    await page.goto('/register')

    await page.getByLabel('邀请码', { exact: true }).fill('INVITE-EXAMPLE-REDACTED')
    await page.getByLabel('注册账号', { exact: true }).fill('mismatch_member')
    await page.getByLabel('注册密码', { exact: true }).fill('abc1234')
    await page.getByLabel('确认密码', { exact: true }).fill('abc12345')
    await page.getByRole('button', { name: '创建账号' }).click()

    await expect(page.getByRole('alert')).toContainText('两次输入的密码不一致。')
    await expect(page.getByRole('alert')).not.toContainText('密码需 8-64 位')
    expect(api.registerRequestCount).toBe(0)
  })

  test('邀请码注册修改输入后清除上一轮服务端错误', async ({ page }) => {
    await mockApi(page)
    await page.goto('/register')

    await page.getByLabel('邀请码', { exact: true }).fill('USED-CODE')
    await page.getByLabel('注册账号', { exact: true }).fill('used_code_member')
    await page.getByLabel('注册密码', { exact: true }).fill('MemberPass123')
    await page.getByLabel('确认密码', { exact: true }).fill('MemberPass123')
    await page.getByRole('button', { name: '创建账号' }).click()
    await expect(page.getByRole('alert')).toContainText('邀请码已经被使用。')

    await page.getByLabel('邀请码', { exact: true }).fill('INVITE-EXAMPLE-REDACTED')

    await expect(page.getByRole('alert')).toHaveCount(0)
  })

  test('普通成员直达用户管理页会看到 403 权限反馈', async ({ page }) => {
    await mockApi(page, { user: memberUser })

    await page.goto('/users')

    await expect(page).toHaveURL(/\/forbidden/)
    await expect(page.getByText('403')).toBeVisible()
    await expect(page.getByText('需要管理人员权限')).toBeVisible()
  })

  test('管理人员可以查看用户列表且列表不泄露敏感字段', async ({ page }) => {
    await mockApi(page, { user: adminUser })

    await page.goto('/users')

    await expect(page.getByRole('heading', { name: '用户与权限' })).toBeVisible()
    await expect(page.getByText('admin_user')).toBeVisible()
    await expect(page.getByText('member_user')).toBeVisible()
    await expect(page.locator('tbody').getByText('管理人员', { exact: true }).first()).toBeVisible()
    await expect(page.locator('tbody').getByText('普通成员', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('password_hash')).toHaveCount(0)
    await expect(page.getByText('authToken')).toHaveCount(0)
  })

  test('管理人员可以按角色筛选用户并翻页', async ({ page }) => {
    await mockApi(page, { user: adminUser })

    await page.goto('/users')

    await page.getByLabel('角色筛选').selectOption('member')
    await expect(page.getByText('member_user')).toBeVisible()
    await expect(page.getByText('admin_user')).toHaveCount(0)

    await page.getByLabel('角色筛选').selectOption('')
    await page.getByRole('button', { name: '下一页' }).click()
    await expect(page.getByText('当前第 2 页')).toBeVisible()
  })

  test('管理人员可以查看并生成邀请码，列表不展示历史明文且可复制本次明文', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: playwrightPermissionOrigin })
    await mockApi(page, { user: adminUser })

    await page.goto('/invitations')

    await expect(page.getByRole('heading', { name: '邀请码' })).toBeVisible()
    await expect(page.locator('tbody').getByText('可使用', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('INVITE-EXAMPLE-REDACTED')).toHaveCount(0)

    await page.getByRole('button', { name: '生成邀请码' }).click()
    await page.getByLabel('目标角色', { exact: true }).selectOption('admin')
    await page.getByLabel('过期时间').fill('2026-07-12T12:00')
    await page.getByRole('button', { name: '创建邀请码' }).click()

    await expect(page.getByText('INVITE-EXAMPLE-REDACTED')).toBeVisible()
    await expect(page.getByText('目标角色：admin')).toBeVisible()
    await expect(page.getByText('过期时间：2026-07-12T12:00')).toBeVisible()
    await page.evaluate(() => navigator.clipboard.writeText(''))
    await page.getByRole('button', { name: '复制' }).click()
    await expect(page.getByRole('status')).toContainText('已复制')
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('INVITE-EXAMPLE-REDACTED')
    await page.screenshot({ path: 'tests/evidence/screenshots/p1-invitations-admin.png', fullPage: true })

    await page.getByRole('button', { name: '关闭' }).click()
    await page.getByRole('button', { name: '生成邀请码' }).click()
    await expect(page.getByText('INVITE-EXAMPLE-REDACTED')).toHaveCount(0)
  })

  test('管理人员可以作废未使用邀请码', async ({ page }) => {
    await mockApi(page, { user: adminUser })

    await page.goto('/invitations')

    await expect(page.locator('tbody').getByText('可使用', { exact: true }).first()).toBeVisible()
    await page.getByRole('button', { name: /作废邀请码/ }).click()

    await expect(page.locator('tbody').getByText('已作废', { exact: true }).first()).toBeVisible()
    await expect(page.locator('tbody').getByText('可使用', { exact: true })).toHaveCount(0)
  })

  test('管理人员可以按状态和角色筛选邀请码并翻页', async ({ page }) => {
    await mockApi(page, { user: adminUser })

    await page.goto('/invitations')

    await page.getByLabel('状态筛选').selectOption('revoked')
    await expect(page.locator('tbody').getByText('已作废', { exact: true }).first()).toBeVisible()

    await page.getByLabel('目标角色筛选').selectOption('admin')
    await expect(page.locator('tbody').getByText('admin', { exact: true }).first()).toBeVisible()

    await page.getByRole('button', { name: '下一页' }).click()
    await expect(page.getByText('当前第 2 页')).toBeVisible()
  })
})
