import { defineStore } from 'pinia';

import { login as requestLogin, logout as requestLogout, type PlatformUser } from '@/api/auth';

interface AuthSession {
  token: string;
  user: PlatformUser;
}

const TOKEN_KEY = 'auth.token';
const USER_KEY = 'auth.user';

function readStoredUser(): PlatformUser | null {
  const rawUser = localStorage.getItem(USER_KEY);

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as PlatformUser;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY),
    user: readStoredUser(),
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
  },
  actions: {
    setSession(session: AuthSession) {
      this.token = session.token;
      this.user = session.user;
      localStorage.setItem(TOKEN_KEY, session.token);
      localStorage.setItem(USER_KEY, JSON.stringify(session.user));
    },
    clearSession() {
      this.token = null;
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
    async login(username: string, password: string) {
      const session = await requestLogin(username, password);
      this.setSession(session);
      return session;
    },
    async logout() {
      if (this.token) {
        await requestLogout();
      }

      this.clearSession();
    },
  },
});
