<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/client'
import AuthShell from '@/components/auth/AuthShell.vue'
import LoginPanel from '@/components/auth/LoginPanel.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const loginError = shallowRef('')
// 默认进入当前平台主入口；显式 redirect 仍优先用于受保护 URL 的登录回跳。
const defaultAuthenticatedRoute = '/environments'
const redirectTarget = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : defaultAuthenticatedRoute))

async function login(payload: { username: string; password: string }) {
  loginError.value = ''
  try {
    await authStore.login(payload)
    await router.replace(redirectTarget.value)
  } catch (error) {
    loginError.value = toApiError(error).message || '账户或密码错误。'
  }
}
</script>

<template>
  <AuthShell variant="login">
    <LoginPanel :loading="authStore.loading" :error-message="loginError" @submit="login" />
  </AuthShell>
</template>
