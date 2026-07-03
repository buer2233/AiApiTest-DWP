<script setup lang="ts">
import { shallowRef } from 'vue'

import { toApiError } from '@/api/client'
import { register as registerUser } from '@/api/platform'
import AuthShell from '@/components/auth/AuthShell.vue'
import RegisterPanel from '@/components/auth/RegisterPanel.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const registerError = shallowRef('')
const registerSuccess = shallowRef('')

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

function clearRegisterStatus() {
  registerError.value = ''
  registerSuccess.value = ''
}
</script>

<template>
  <AuthShell variant="register" eyebrow="邀请码注册 · 注册成功后返回登录">
    <RegisterPanel
      :loading="authStore.loading"
      :error-message="registerError"
      :success-message="registerSuccess"
      @clear-status="clearRegisterStatus"
      @submit="register"
    />
  </AuthShell>
</template>
