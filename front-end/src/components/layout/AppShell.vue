<script setup lang="ts">
import { DataLine, Key, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getApiErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.loadCurrentUser()
    } catch {
      await router.replace('/login')
    }
  }
})

async function handleLogout() {
  try {
    await auth.logoutCurrentUser()
    await router.replace('/login')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '退出失败，请重试'))
  }
}
</script>

<template>
  <div class="app-shell">
    <aside class="app-shell__sidebar" aria-label="主导航">
      <RouterLink class="app-shell__brand" to="/test-cases">
        <span class="app-shell__brand-mark">AI</span>
        <span>
          <strong>AiApiTest-DWP</strong>
          <small>自动化测试平台</small>
        </span>
      </RouterLink>

      <nav class="app-shell__nav">
        <RouterLink class="app-shell__nav-link" :class="{ active: route.name === 'test-cases' }" to="/test-cases">
          <el-icon><DataLine /></el-icon>
          <span>测试用例</span>
        </RouterLink>
        <RouterLink
          v-if="auth.isAdmin"
          class="app-shell__nav-link"
          :class="{ active: route.name === 'invite-codes' }"
          to="/invite-codes"
        >
          <el-icon><Key /></el-icon>
          <span>邀请码管理</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="app-shell__main">
      <header class="app-shell__topbar">
        <div class="app-shell__user">
          <span class="app-shell__user-name">{{ auth.user?.username || '加载中' }}</span>
          <span class="app-shell__user-role">{{ auth.user?.role || 'member' }}</span>
        </div>
        <el-button :icon="SwitchButton" text @click="handleLogout">退出登录</el-button>
      </header>
      <main class="app-shell__content">
        <slot />
      </main>
    </div>
  </div>
</template>
