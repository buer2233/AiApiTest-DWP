<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/client'
import { register as registerUser } from '@/api/platform'
import AuthShell from '@/components/auth/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const loginError = shallowRef('')
const registerError = shallowRef('')
const registerSuccess = shallowRef('')
const redirectTarget = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'))

async function login(payload: { username: string; password: string }) {
  loginError.value = ''
  try {
    await authStore.login(payload)
    await router.replace(redirectTarget.value)
  } catch (error) {
    loginError.value = toApiError(error).message || '账号或密码错误。'
  }
}

async function register(payload: { invitation_code: string; username: string; password: string; confirm_password: string }) {
  registerError.value = ''
  registerSuccess.value = ''
  try {
    await registerUser(payload)
    registerSuccess.value = '注册成功，请返回登录后进入平台。'
  } catch (error) {
    registerError.value = toApiError(error).message
  }
}
</script>

<template>
  <AuthShell
    :authenticated="authStore.isAuthenticated"
    :loading="authStore.loading"
    :login-error="loginError"
    :register-error="registerError"
    :register-success="registerSuccess"
    @login="login"
    @register="register"
  />
</template>
