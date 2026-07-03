<script setup lang="ts">
import { storeToRefs } from 'pinia'

import ProtectedPreview from '@/components/auth/ProtectedPreview.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
</script>

<template>
  <AppLayout>
    <section class="dashboard-hero">
      <div>
        <span class="badge">authToken Cookie 已验证</span>
        <h1 class="serif-title">平台访问已解锁</h1>
        <p>{{ user?.display_name || user?.username }}，你已通过 Cookie 授权进入 AiApiTest-DWP。</p>
      </div>
    </section>
    <ProtectedPreview unlocked />
  </AppLayout>
</template>

<style scoped>
.dashboard-hero {
  padding: 28px;
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  background: var(--color-surface-card);
}

.badge {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(93, 184, 114, 0.14);
  color: #2d7c43;
  font-size: 13px;
  font-weight: 700;
}

h1 {
  margin: 0 0 8px;
  font-size: 36px;
}

p {
  margin: 0;
  color: var(--color-body);
}
</style>
