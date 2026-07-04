<script setup lang="ts">
import { BarChart3, Gauge, Home, LogOut, Ticket, UsersRound } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const { user, isAdmin } = storeToRefs(authStore)
const router = useRouter()

async function logout() {
  await authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="sidebar-brand" href="/dashboard">
        <span>A</span>
        <strong>AiApiTest-DWP</strong>
      </a>
      <nav aria-label="平台导航">
        <RouterLink class="nav-link" to="/dashboard"><Home :size="18" />概览</RouterLink>
        <RouterLink class="nav-link" to="/environments"><Gauge :size="18" />环境通过率</RouterLink>
        <RouterLink class="nav-link" to="/modules"><BarChart3 :size="18" />模块通过率</RouterLink>
        <RouterLink v-if="isAdmin" class="nav-link" to="/users"><UsersRound :size="18" />用户与权限</RouterLink>
        <RouterLink v-if="isAdmin" class="nav-link" to="/invitations"><Ticket :size="18" />邀请码</RouterLink>
      </nav>
    </aside>
    <main class="content">
      <header class="topbar">
        <div>
          <span class="eyebrow">{{ user?.role === 'admin' ? '管理人员' : '普通成员' }}</span>
          <strong>{{ user?.display_name || user?.username }}</strong>
        </div>
        <button class="ghost-button" type="button" @click="logout"><LogOut :size="16" />退出登录</button>
      </header>
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 250px 1fr;
  min-height: 100vh;
  background: var(--color-canvas);
}

.sidebar {
  display: grid;
  align-content: start;
  gap: 30px;
  min-width: 0;
  padding: 26px;
  border-right: 1px solid var(--color-hairline);
  background: var(--color-surface-soft);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: var(--color-ink);
  text-decoration: none;
}

.sidebar-brand span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
}

.sidebar nav {
  display: grid;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  min-width: 0;
  padding: 0 12px;
  border-radius: 8px;
  color: var(--color-body);
  text-decoration: none;
}

.nav-link.router-link-active {
  background: var(--color-surface-card);
  color: var(--color-primary-active);
  font-weight: 700;
}

.content {
  display: grid;
  align-content: start;
  gap: 24px;
  min-width: 0;
  padding: 26px 34px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.topbar div {
  display: grid;
  gap: 4px;
}

.eyebrow {
  color: var(--color-muted);
  font-size: 12px;
}

.ghost-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-body);
}

@media (max-width: 820px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--color-hairline);
  }

  .content {
    padding: 22px 18px;
  }
}
</style>
