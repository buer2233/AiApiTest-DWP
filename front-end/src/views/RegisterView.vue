<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import { useRouter } from 'vue-router'

import { register } from '@/api/auth'
import { getApiErrorMessage, getApiFieldErrors } from '@/api/http'

const router = useRouter()

const form = reactive({
  invite_code: '',
  username: '',
  email: '',
  password: '',
  password_confirm: '',
})

const loading = shallowRef(false)
const errorMessage = shallowRef('')
const fieldErrors = reactive<Record<string, string>>({})

async function handleRegister() {
  errorMessage.value = ''
  Object.keys(fieldErrors).forEach((key) => {
    delete fieldErrors[key]
  })
  loading.value = true
  try {
    await register(form)
    await router.replace({ path: '/login', query: { registered: '1' } })
  } catch (error) {
    Object.assign(fieldErrors, getApiFieldErrors(error))
    if (!Object.keys(fieldErrors).length && getApiErrorMessage(error).includes('邀请码')) {
      fieldErrors.invite_code = getApiErrorMessage(error)
    }
    errorMessage.value = getApiErrorMessage(error, '注册失败，请检查邀请码和表单信息')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page auth-page--compact">
    <section class="auth-panel auth-panel--wide" aria-label="注册表单">
      <p class="auth-panel__kicker">账号注册</p>
      <h1>使用邀请码创建账号</h1>
      <el-alert v-if="errorMessage" class="auth-panel__alert" type="error" show-icon :closable="false" role="alert">
        {{ errorMessage }}
      </el-alert>

      <el-form class="auth-form auth-form--grid" @submit.prevent="handleRegister">
        <div class="form-field">
          <label for="register-invite">邀请码</label>
          <el-input id="register-invite" v-model="form.invite_code" autocomplete="one-time-code" />
          <span v-if="fieldErrors.invite_code" class="field-error">{{ fieldErrors.invite_code }}</span>
        </div>
        <div class="form-field">
          <label for="register-username">用户名</label>
          <el-input id="register-username" v-model="form.username" autocomplete="username" />
          <span v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</span>
        </div>
        <div class="form-field auth-form__span">
          <label for="register-email">邮箱</label>
          <el-input id="register-email" v-model="form.email" autocomplete="email" type="email" />
          <span v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</span>
        </div>
        <div class="form-field">
          <label for="register-password">密码</label>
          <el-input id="register-password" v-model="form.password" show-password type="password" autocomplete="new-password" />
          <span v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</span>
        </div>
        <div class="form-field">
          <label for="register-password-confirm">确认密码</label>
          <el-input
            id="register-password-confirm"
            v-model="form.password_confirm"
            show-password
            type="password"
            autocomplete="new-password"
          />
          <span v-if="fieldErrors.password_confirm" class="field-error">{{ fieldErrors.password_confirm }}</span>
        </div>
        <el-button class="auth-form__submit auth-form__span" native-type="submit" type="primary" :loading="loading">
          创建账号
        </el-button>
      </el-form>

      <p class="auth-panel__footer">
        已有账号？
        <RouterLink to="/login">返回登录</RouterLink>
      </p>
    </section>
  </main>
</template>
