/**
 * Vue Router 路由配置模块。
 * 本模块定义登录页、平台首页和认证守卫，确保未登录用户只能访问登录页。
 */

import {
  createRouter,
  createWebHistory,
  type Router,
  type RouteRecordRaw,
  type RouterHistory,
} from 'vue-router';

import { useAuthStore } from '@/stores/auth';

/**
 * 平台路由表。
 * 路由 meta 中的 requiresAuth 和 guestOnly 会被全局守卫统一处理。
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/platform',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: {
      guestOnly: true,
    },
  },
  {
    path: '/platform',
    name: 'platform',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: {
      requiresAuth: true,
    },
  },
];

function applyAuthGuard(router: Router) {
  /**
   * 注册登录态守卫。
   * 未登录访问平台页时跳转登录页，并保留 redirect 以便登录后返回原目标。
   */
  router.beforeEach((to) => {
    const auth = useAuthStore();

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return {
        name: 'login',
        query: {
          redirect: to.fullPath,
        },
      };
    }

    if (to.meta.guestOnly && auth.isAuthenticated) {
      return { name: 'platform' };
    }

    return true;
  });
}

export function createPlatformRouter(history: RouterHistory = createWebHistory()) {
  /**
   * 创建平台路由实例。
   * Args:
   *   history: 路由历史实现；测试中可注入 memory history，生产默认使用浏览器 history。
   * Returns:
   *   Router: 已挂载认证守卫的 Vue Router 实例。
   */
  const router = createRouter({
    history,
    routes,
  });

  applyAuthGuard(router);

  return router;
}

const router = createPlatformRouter();

export default router;
