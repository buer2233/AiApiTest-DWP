import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi } from 'vitest';
import { createWebHistory } from 'vue-router';

import { login } from '@/api/auth';
import AppLayout from '@/layouts/AppLayout.vue';
import { createPlatformRouter } from '@/router';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
}));

function buildRouter() {
  return createPlatformRouter(createWebHistory());
}

describe('auth flow', () => {
  it('redirects anonymous users from the platform shell to login', async () => {
    setActivePinia(createPinia());
    const router = buildRouter();

    await router.push('/platform');
    await router.isReady();

    expect(router.currentRoute.value.name).toBe('login');
    expect(router.currentRoute.value.query.redirect).toBe('/platform');
  });

  it('stores token and user profile after a successful login', async () => {
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
