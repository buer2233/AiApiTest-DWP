<script setup lang="ts">
import { Eye, EyeOff, LockKeyhole, UserRound } from '@lucide/vue'
import { reactive, shallowRef } from 'vue'

const props = defineProps<{
  loading: boolean
  errorMessage: string
}>()

const emit = defineEmits<{
  submit: [payload: { username: string; password: string }]
}>()

const form = reactive({
  username: '',
  password: '',
})
const showPassword = shallowRef(false)
const localError = shallowRef('')

function submitLogin() {
  localError.value = ''
  if (!form.username || !form.password) {
    localError.value = '请输入账号和密码。'
    return
  }
  emit('submit', { username: form.username, password: form.password })
}
</script>

<template>
  <section class="auth-card auth-card-login" aria-labelledby="login-title">
    <h1 id="login-title" class="serif-title auth-title">登录</h1>
    <p class="auth-subtitle">使用平台账号登录，验证通过后进入测试平台</p>

    <div v-if="props.errorMessage || localError" class="form-alert" role="alert">
      {{ props.errorMessage || localError }}
    </div>

    <form class="auth-form" @submit.prevent="submitLogin">
      <label class="field-label" for="login-username">账号</label>
      <div class="input-shell">
        <UserRound :size="18" aria-hidden="true" />
        <input id="login-username" v-model="form.username" aria-label="账号" autocomplete="username" placeholder="请输入账号" />
      </div>

      <label class="field-label" for="login-password">密码</label>
      <div class="input-shell">
        <LockKeyhole :size="18" aria-hidden="true" />
        <input
          id="login-password"
          v-model="form.password"
          aria-label="密码"
          autocomplete="current-password"
          placeholder="请输入密码"
          :type="showPassword ? 'text' : 'password'"
        />
        <button class="icon-button" type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
          <EyeOff v-if="showPassword" :size="18" aria-hidden="true" />
          <Eye v-else :size="18" aria-hidden="true" />
        </button>
      </div>

      <div class="form-row">
        <label class="remember">
          <input type="checkbox" />
          <span>记住我</span>
        </label>
        <span class="text-link">忘记密码?</span>
      </div>

      <button class="primary-button" type="submit" :disabled="props.loading">
        {{ props.loading ? '验证中...' : '进入平台' }}
      </button>
    </form>

    <div class="switch-line">
      <span>没有账号?</span>
      <a href="/register">使用邀请码注册 -></a>
    </div>
  </section>
</template>

<style scoped>
.auth-card {
  min-height: 540px;
  padding: 34px 40px;
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  background: rgba(250, 249, 245, 0.88);
}

.auth-title {
  margin: 0;
  text-align: center;
  font-size: 32px;
  line-height: 1.2;
}

.auth-subtitle {
  margin: 12px 0 30px;
  color: var(--color-muted);
  text-align: center;
  font-size: 14px;
}

.auth-form {
  display: grid;
  gap: 14px;
}

.field-label {
  color: var(--color-body);
  font-size: 14px;
  font-weight: 600;
}

.input-shell {
  display: grid;
  grid-template-columns: 22px 1fr auto;
  align-items: center;
  min-height: 50px;
  padding: 0 14px;
  border: 1px solid #dacfc2;
  border-radius: 8px;
  background: rgba(250, 249, 245, 0.92);
  color: var(--color-muted);
}

.input-shell:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(204, 120, 92, 0.16);
}

.input-shell input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-ink);
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  background: transparent;
  color: var(--color-muted);
}

.form-row,
.remember,
.switch-line {
  display: flex;
  align-items: center;
}

.form-row {
  justify-content: space-between;
  margin: 4px 0 14px;
}

.remember {
  gap: 8px;
  color: var(--color-body);
  font-size: 14px;
}

.text-link,
.switch-line a {
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}

.primary-button {
  min-height: 50px;
  border: 0;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 700;
}

.primary-button:hover {
  background: var(--color-primary-active);
}

.primary-button:disabled {
  background: #e6dfd8;
  color: var(--color-muted);
}

.switch-line {
  justify-content: center;
  gap: 14px;
  margin-top: 36px;
  padding-top: 28px;
  border-top: 1px solid var(--color-hairline);
  color: var(--color-muted);
  font-size: 14px;
}

.form-alert {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(198, 69, 69, 0.24);
  border-radius: 8px;
  background: rgba(198, 69, 69, 0.08);
  color: var(--color-error);
  font-size: 14px;
}
</style>
