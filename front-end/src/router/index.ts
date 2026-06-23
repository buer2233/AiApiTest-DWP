import {
  createRouter,
  createWebHistory,
  type Router,
  type RouteRecordRaw,
  type RouterHistory,
} from 'vue-router';

import { useAuthStore } from '@/stores/auth';

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
  const router = createRouter({
    history,
    routes,
  });

  applyAuthGuard(router);

  return router;
}

const router = createPlatformRouter();

export default router;
