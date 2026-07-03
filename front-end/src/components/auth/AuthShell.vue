<script setup lang="ts">
import { computed } from 'vue'

import LoginPanel from './LoginPanel.vue'
import ProtectedPreview from './ProtectedPreview.vue'
import RegisterPanel from './RegisterPanel.vue'
import RoleSplitRail from './RoleSplitRail.vue'

const props = defineProps<{
  authenticated: boolean
  loading: boolean
  loginError: string
  registerError: string
  registerSuccess: string
}>()

const emit = defineEmits<{
  login: [payload: { username: string; password: string }]
  register: [payload: { invitation_code: string; username: string; password: string; confirm_password: string }]
}>()

const rightTitle = computed(() => (props.authenticated ? '安全守护测试数据' : '统一身份访问控制 · 安全守护测试数据'))
</script>

<template>
  <main class="auth-page">
    <header class="auth-header">
      <a class="brand" href="/login" aria-label="AiApiTest-DWP 登录入口">
        <span class="brand-mark">A</span>
        <strong class="serif-title">AiApiTest-DWP</strong>
        <i></i>
        <span>Access Split Gate</span>
      </a>
      <p>{{ rightTitle }}</p>
    </header>

    <section class="auth-grid">
      <LoginPanel :loading="props.loading" :error-message="props.loginError" @submit="emit('login', $event)" />
      <RoleSplitRail />
      <RegisterPanel
        :loading="props.loading"
        :error-message="props.registerError"
        :success-message="props.registerSuccess"
        @submit="emit('register', $event)"
      />
    </section>

    <ProtectedPreview :unlocked="props.authenticated" />
  </main>
</template>

<style scoped>
.auth-page {
  display: grid;
  gap: 10px;
  min-height: 100vh;
  padding: 26px 34px 32px;
  background:
    radial-gradient(circle at 20% 10%, rgba(204, 120, 92, 0.12), transparent 26%),
    var(--color-canvas);
}

.auth-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  min-height: 50px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-ink);
  text-decoration: none;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
}

.brand strong {
  font-size: 34px;
}

.brand i {
  width: 1px;
  height: 24px;
  background: var(--color-hairline);
}

.brand span:last-child {
  color: var(--color-primary);
  font-size: 18px;
  font-weight: 600;
}

.auth-header p {
  margin: 0;
  color: var(--color-body);
  font-size: 14px;
  font-weight: 600;
}

.auth-grid {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) 150px minmax(320px, 1fr);
  gap: 10px;
}

@media (max-width: 980px) {
  .auth-page {
    padding: 18px;
  }

  .auth-header,
  .brand {
    align-items: flex-start;
  }

  .auth-header {
    display: grid;
  }

  .brand {
    flex-wrap: wrap;
  }

  .brand strong {
    font-size: 28px;
  }

  .auth-grid {
    grid-template-columns: 1fr;
  }
}
</style>
