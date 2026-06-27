import { computed, ref } from "vue";
import { defineStore } from "pinia";

import * as authApi from "@/api/auth";
import { clearToken, getToken, setToken } from "@/api/http";
import type { User } from "@/types";

// 认证状态：单一数据源（token + user），其余派生。
export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(getToken());
  const user = ref<User | null>(null);

  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === "admin");

  async function login(username: string, password: string) {
    const result = await authApi.login(username, password);
    token.value = result.token;
    user.value = result.user;
    setToken(result.token);
    return result;
  }

  async function fetchMe() {
    user.value = await authApi.fetchMe();
    return user.value;
  }

  async function logout() {
    try {
      await authApi.logout();
    } catch {
      // 后端登出失败（网络/401 等）不阻止本地清除
    } finally {
      // 无论后端是否成功，本地一律清登录态
      token.value = null;
      user.value = null;
      clearToken();
    }
  }

  return { token, user, isAuthenticated, isAdmin, login, fetchMe, logout };
});
