/**
 * 登录态 Pinia store。
 * 本模块统一管理 DRF Token、当前用户信息、本地持久化和登录/登出动作。
 */

import { defineStore } from 'pinia';

import { login as requestLogin, logout as requestLogout, type PlatformUser } from '@/api/auth';

/**
 * 前端登录会话结构。
 * token 用于后续 API Authorization 请求头，user 用于页面展示和权限判断。
 */
interface AuthSession {
  token: string;
  user: PlatformUser;
}

const TOKEN_KEY = 'auth.token';
const USER_KEY = 'auth.user';

function readStoredUser(): PlatformUser | null {
  /**
   * 从 localStorage 读取已保存的用户信息。
   * Returns:
   *   PlatformUser | null: 可用的用户对象；不存在或解析失败时返回 null。
   */
  const rawUser = localStorage.getItem(USER_KEY);

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as PlatformUser;
  } catch {
    // 本地缓存损坏时清理 user，避免页面误判为已登录。
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export const useAuthStore = defineStore('auth', {
  /**
   * 初始化登录态。
   * 页面刷新后从 localStorage 恢复 token 和用户信息，保持平台访问状态。
   */
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY),
    user: readStoredUser(),
  }),
  getters: {
    /** 当前是否具备完整登录态。 */
    isAuthenticated: (state) => Boolean(state.token && state.user),
  },
  actions: {
    setSession(session: AuthSession) {
      /** 保存登录成功后的 token 和用户信息。 */
      this.token = session.token;
      this.user = session.user;
      localStorage.setItem(TOKEN_KEY, session.token);
      localStorage.setItem(USER_KEY, JSON.stringify(session.user));
    },
    clearSession() {
      /** 清空内存和本地持久化登录态。 */
      this.token = null;
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
    async login(username: string, password: string) {
      /** 调用后端登录接口并保存会话。 */
      const session = await requestLogin(username, password);
      this.setSession(session);
      return session;
    },
    async logout() {
      /** 调用后端登出接口并清理本地登录态。 */
      if (this.token) {
        await requestLogout();
      }

      this.clearSession();
    },
  },
});
