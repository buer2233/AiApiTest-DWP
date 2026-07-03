<script setup lang="ts">
import { RouterLink } from 'vue-router'

const props = withDefaults(
  defineProps<{
    eyebrow?: string
    variant?: 'login' | 'register'
  }>(),
  {
    eyebrow: '统一身份访问控制 · 安全守护测试数据',
    variant: 'login',
  },
)
</script>

<template>
  <main class="auth-page" :class="`auth-page-${props.variant}`">
    <header class="auth-header">
      <RouterLink class="brand" to="/login" aria-label="AiApiTest-DWP 登录入口">
        <span class="brand-mark">A</span>
        <strong class="serif-title">AiApiTest-DWP</strong>
        <i></i>
        <span>Access Split Gate</span>
      </RouterLink>
      <p>{{ props.eyebrow }}</p>
    </header>

    <section class="auth-stage" aria-label="认证表单">
      <slot />
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  display: grid;
  align-content: start;
  gap: 28px;
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

.auth-stage {
  display: grid;
  width: min(100%, 480px);
  justify-self: center;
  padding-top: 18px;
}

.auth-page-register .auth-stage {
  width: min(100%, 520px);
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

  .auth-stage {
    width: 100%;
    padding-top: 4px;
  }
}
</style>
