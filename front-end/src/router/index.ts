import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/test-cases',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { public: true },
  },
  {
    path: '/test-cases',
    name: 'test-cases',
    component: () => import('@/views/TestCasesView.vue'),
  },
  {
    path: '/invite-codes',
    name: 'invite-codes',
    component: () => import('@/views/InviteCodesView.vue'),
    meta: { adminOnly: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!to.meta.public && auth.isAuthenticated && !auth.user) {
    try {
      // 管理员权限依赖用户角色，直达受保护页面时必须先恢复当前用户。
      await auth.loadCurrentUser()
    } catch {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  if (to.meta.adminOnly && auth.user?.role !== 'admin') {
    return { path: '/test-cases' }
  }
  return true
})

export default router
