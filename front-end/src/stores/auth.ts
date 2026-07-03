import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

import { toApiError } from '@/api/client'
import * as platformApi from '@/api/platform'
import type { UserSummary } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = shallowRef<UserSummary | null>(null)
  const loading = shallowRef(false)
  const authChecked = shallowRef(false)
  const lastErrorCode = shallowRef<string | null>(null)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setUser(nextUser: UserSummary | null) {
    user.value = nextUser
    authChecked.value = true
    lastErrorCode.value = null
  }

  function clearUser(code: string | null = null) {
    user.value = null
    authChecked.value = true
    lastErrorCode.value = code
  }

  async function ensureCurrentUser(): Promise<boolean> {
    loading.value = true
    try {
      setUser(await platformApi.fetchMe())
      return true
    } catch (error) {
      const apiError = toApiError(error)
      clearUser(apiError.code)
      return false
    } finally {
      loading.value = false
    }
  }

  async function login(payload: platformApi.LoginRequest): Promise<void> {
    loading.value = true
    try {
      setUser(await platformApi.login(payload))
    } catch (error) {
      const apiError = toApiError(error)
      lastErrorCode.value = apiError.code
      throw apiError
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    loading.value = true
    try {
      await platformApi.logout()
    } finally {
      clearUser(null)
      loading.value = false
    }
  }

  return {
    user,
    loading,
    authChecked,
    lastErrorCode,
    isAuthenticated,
    isAdmin,
    setUser,
    clearUser,
    ensureCurrentUser,
    login,
    logout,
  }
})
