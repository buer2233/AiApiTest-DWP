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
const redirectTarget = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'))

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
