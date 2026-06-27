import { createRouter, createWebHistory } from "vue-router";

import { getToken } from "@/api/http";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/test-cases" },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { public: true },
    },
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
      meta: { public: true },
    },
    {
      path: "/test-cases",
      name: "test-cases",
      component: () => import("@/views/TestCasesView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

// 路由守卫：未登录访问受保护页 → /login；已登录访问 login/register → /test-cases。
router.beforeEach((to) => {
  const authed = !!getToken();
  if (to.meta.requiresAuth && !authed) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.meta.public && authed) {
    return { name: "test-cases" };
  }
  return true;
});

export default router;
