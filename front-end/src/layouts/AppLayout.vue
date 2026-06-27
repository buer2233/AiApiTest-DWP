<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { useAuthStore } from "@/stores/auth";

// 受保护页外壳：顶部导航 + 当前用户 + 角色标识 + 登出。
const auth = useAuthStore();
const router = useRouter();

onMounted(async () => {
  // 进入布局时拉取当前用户（刷新后 store 为空但 token 仍在）
  if (!auth.user) {
    try {
      await auth.fetchMe();
    } catch {
      // 401 由 http 响应拦截兜底跳登录
    }
  }
});

async function handleLogout() {
  await auth.logout();
  ElMessage.success("已登出");
  router.push({ name: "login" });
}
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="brand">Hermes 测试平台</div>
      <nav class="nav">
        <router-link class="nav-link" :to="{ name: 'test-cases' }">测试用例</router-link>
      </nav>
      <div v-if="auth.user" class="user-area">
        <el-tag :type="auth.isAdmin ? 'warning' : 'info'" effect="plain" size="small">
          {{ auth.isAdmin ? "管理员" : "成员" }}
        </el-tag>
        <span class="username">{{ auth.user.username }}</span>
        <el-button text @click="handleLogout">登出</el-button>
      </div>
    </header>
    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100%;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  height: 56px;
  padding: 0 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-base);
}
.brand {
  font-weight: 600;
  color: var(--brand-primary);
}
.nav {
  flex: 1;
}
.nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}
.nav-link.router-link-active {
  color: var(--text-primary);
  border-bottom-color: var(--brand-primary);
}
.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: var(--text-primary);
}
.app-main {
  padding: 24px;
}
</style>
