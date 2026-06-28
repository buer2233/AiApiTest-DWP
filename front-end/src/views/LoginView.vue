<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getApiErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  account: '',
  password: '',
})
const errorMessage = shallowRef('')

async function handleLogin() {
  errorMessage.value = ''
  try {
    await auth.loginWithPassword(form)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/test-cases'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '账号或密码不正确')
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-page__brand" aria-label="平台说明">
      <div class="auth-page__brand-block">
        <p class="auth-page__eyebrow">AI 协作自动化测试平台</p>
        <h1>AiApiTest-DWP</h1>
        <p>统一管理登录身份、测试用例资产和后续 Jenkins 执行入口。</p>
      </div>
    </section>

    <section class="auth-panel" aria-label="登录表单">
      <p class="auth-panel__kicker">平台入口</p>
      <h2>登录 AiApiTest-DWP</h2>
      <el-alert v-if="route.query.registered" class="auth-panel__alert" type="success" show-icon :closable="false">
        注册成功，请登录
      </el-alert>
      <el-alert v-if="errorMessage" class="auth-panel__alert" type="error" show-icon :closable="false" role="alert">
        {{ errorMessage }}
      </el-alert>

      <el-form class="auth-form" @submit.prevent="handleLogin">
        <div class="form-field">
          <label for="login-account">账号</label>
          <el-input id="login-account" v-model="form.account" autocomplete="username" placeholder="用户名或邮箱" />
        </div>
        <div class="form-field">
          <label for="login-password">密码</label>
          <el-input
            id="login-password"
            v-model="form.password"
            autocomplete="current-password"
            placeholder="请输入密码"
            show-password
            type="password"
          />
        </div>
        <el-button class="auth-form__submit" native-type="submit" type="primary" :loading="auth.loading">登录</el-button>
      </el-form>

      <p class="auth-panel__footer">
        没有账号？
        <RouterLink to="/register">使用邀请码注册</RouterLink>
      </p>
    </section>
  </main>
</template>
