<script setup lang="ts">
import { Eye, EyeOff, Gift, LockKeyhole, UserRound } from '@lucide/vue'
import { computed, reactive, shallowRef, watch } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps<{
  loading: boolean
  errorMessage: string
  successMessage: string
}>()

const emit = defineEmits<{
  submit: [payload: { invitation_code: string; username: string; password: string; confirm_password: string }]
  clearStatus: []
}>()

const form = reactive({
  invitation_code: '',
  username: '',
  password: '',
  confirm_password: '',
})
const showPassword = shallowRef(false)
const localError = shallowRef('')
const displayError = computed(() => localError.value || props.errorMessage)
const usernamePattern = /^[A-Za-z0-9_.-]+$/

watch(
  () => [form.invitation_code, form.username, form.password, form.confirm_password],
  () => {
    localError.value = ''
    emit('clearStatus')
  },
)

function submitRegister() {
  localError.value = ''
  if (!form.invitation_code || !form.username || !form.password || !form.confirm_password) {
    localError.value = '请完整填写邀请码、账号和密码。'
    return
  }
  // 账号格式在前端先拦截，减少无效注册请求并保持与后端契约一致。
  if (!usernamePattern.test(form.username)) {
    localError.value = '账号只能包含字母、数字、下划线、短横线和点。'
    return
  }
  if (form.password !== form.confirm_password) {
    localError.value = '两次输入的密码不一致。'
    return
  }
  emit('submit', { ...form })
}
</script>

<template>
  <section class="auth-card" aria-labelledby="register-title">
    <h1 id="register-title" class="serif-title auth-title">邀请码注册</h1>
    <p class="auth-subtitle">通过邀请码创建账号，加入 AiApiTest-DWP 平台</p>

    <div v-if="props.successMessage" class="form-status" role="status">
      {{ props.successMessage }}
    </div>
    <div v-if="displayError" class="form-alert" role="alert">
      {{ displayError }}
    </div>

    <form class="auth-form" @submit.prevent="submitRegister">
      <label class="field-label" for="register-code">邀请码</label>
      <div class="input-shell">
        <Gift :size="18" aria-hidden="true" />
        <input id="register-code" v-model="form.invitation_code" aria-label="邀请码" placeholder="请输入邀请码" />
      </div>

      <label class="field-label" for="register-username">账号</label>
      <div class="input-shell">
        <UserRound :size="18" aria-hidden="true" />
        <input id="register-username" v-model="form.username" aria-label="注册账号" autocomplete="username" placeholder="请输入账号" />
      </div>

      <label class="field-label" for="register-password">密码</label>
      <div class="input-shell">
        <LockKeyhole :size="18" aria-hidden="true" />
        <input
          id="register-password"
          v-model="form.password"
          aria-label="注册密码"
          autocomplete="new-password"
          placeholder="请输入密码"
          :type="showPassword ? 'text' : 'password'"
        />
        <button class="icon-button" type="button" :aria-label="showPassword ? '隐藏注册密码' : '显示注册密码'" @click="showPassword = !showPassword">
          <EyeOff v-if="showPassword" :size="18" aria-hidden="true" />
          <Eye v-else :size="18" aria-hidden="true" />
        </button>
      </div>

      <label class="field-label" for="register-confirm">确认密码</label>
      <div class="input-shell">
        <LockKeyhole :size="18" aria-hidden="true" />
        <input
          id="register-confirm"
          v-model="form.confirm_password"
          aria-label="确认密码"
          autocomplete="new-password"
          placeholder="请再次输入密码"
          :type="showPassword ? 'text' : 'password'"
        />
      </div>

      <button class="primary-button" type="submit" :disabled="props.loading">
        {{ props.loading ? '创建中...' : '创建账号' }}
      </button>
    </form>

    <div class="switch-line">
      <span>已有账号?</span>
      <RouterLink to="/login">立即登录 -></RouterLink>
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
  gap: 12px;
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
  min-height: 44px;
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

.primary-button {
  min-height: 50px;
  margin-top: 2px;
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid var(--color-hairline);
  color: var(--color-muted);
  font-size: 14px;
}

.switch-line a {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
}

.form-alert,
.form-status {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
}

.form-alert {
  border: 1px solid rgba(198, 69, 69, 0.24);
  background: rgba(198, 69, 69, 0.08);
  color: var(--color-error);
}

.form-status {
  border: 1px solid rgba(93, 184, 114, 0.28);
  background: rgba(93, 184, 114, 0.12);
  color: #2d7c43;
}
</style>
