/**
 * 登录态与路由守卫测试。
 * 覆盖匿名用户跳转登录、登录成功保存会话、admin/member 进入平台壳三类核心行为。
 */

import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi } from 'vitest';
import { createMemoryHistory } from 'vue-router';

import { login } from '@/api/auth';
import AppLayout from '@/layouts/AppLayout.vue';
import { createPlatformRouter } from '@/router';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
}));

function buildRouter() {
  /** 创建带真实守卫的路由实例，并用内存 history 隔离 jsdom 全局浏览器状态。 */
  return createPlatformRouter(createMemoryHistory());
}

describe('auth flow', () => {
  it('redirects anonymous users from the platform shell to login', async () => {
    /** 未登录用户访问平台页时应被路由守卫拦截。 */
    setActivePinia(createPinia());
    const router = buildRouter();

    await router.push('/platform');
    await router.isReady();

    expect(router.currentRoute.value.name).toBe('login');
    expect(router.currentRoute.value.query.redirect).toBe('/platform');
  });

  it('stores token and user profile after a successful login', async () => {
    /** 登录成功后 token 和用户信息应同时写入 Pinia 与 localStorage。 */
    setActivePinia(createPinia());
    vi.mocked(login).mockResolvedValue({
      token: 'stage8-token',
      user: {
        id: 7,
        username: 'platform-admin',
        role: 'admin',
      },
    });

    const auth = useAuthStore();
    await auth.login('platform-admin', 'local-password');

    expect(auth.token).toBe('stage8-token');
    expect(auth.user?.username).toBe('platform-admin');
    expect(auth.user?.role).toBe('admin');
    expect(localStorage.getItem('auth.token')).toBe('stage8-token');
    expect(JSON.parse(localStorage.getItem('auth.user') ?? '{}')).toMatchObject({
      username: 'platform-admin',
      role: 'admin',
    });
  });

  it.each(['admin', 'member'] as const)('allows %s users to enter the platform shell', async (role) => {
    /** 第一版 admin/member 权限一致，都可以进入平台主布局。 */
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.setSession({
      token: `${role}-token`,
      user: {
        id: role === 'admin' ? 1 : 2,
        username: `${role}-user`,
        role,
      },
    });

    const router = buildRouter();
    await router.push('/platform');
    await router.isReady();

    expect(router.currentRoute.value.name).toBe('platform');
    expect(AppLayout).toBeTruthy();
  });
});
