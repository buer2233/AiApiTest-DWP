import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

import { fetchMe, login, logout, type LoginPayload, type PlatformUser } from '@/api/auth'

const TOKEN_KEY = 'aiapitest_token'

export const useAuthStore = defineStore('auth', () => {
  const token = shallowRef(window.localStorage.getItem(TOKEN_KEY) || '')
  const user = shallowRef<PlatformUser | null>(null)
  const loading = shallowRef(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setSession(nextToken: string, nextUser: PlatformUser) {
    token.value = nextToken
    user.value = nextUser
    window.localStorage.setItem(TOKEN_KEY, nextToken)
  }

  function clearSession() {
    token.value = ''
    user.value = null
    window.localStorage.removeItem(TOKEN_KEY)
  }

  async function loginWithPassword(payload: LoginPayload) {
    loading.value = true
    try {
      const result = await login(payload)
      setSession(result.token, result.user)
      return result.user
    } finally {
      loading.value = false
    }
  }

  async function loadCurrentUser() {
    if (!token.value) return null
    loading.value = true
    try {
      user.value = await fetchMe()
      return user.value
    } catch (error) {
      clearSession()
      throw error
    } finally {
      loading.value = false
    }
  }

  async function logoutCurrentUser() {
    try {
      if (token.value) {
        await logout()
      }
    } finally {
      clearSession()
    }
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    isAdmin,
    setSession,
    clearSession,
    loginWithPassword,
    loadCurrentUser,
    logoutCurrentUser,
  }
})
