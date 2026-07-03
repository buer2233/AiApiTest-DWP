<script setup lang="ts">
import { ShieldAlert } from '@lucide/vue'

import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<template>
  <AppLayout>
    <section class="forbidden">
      <ShieldAlert :size="64" aria-hidden="true" />
      <strong>403</strong>
      <h1>需要管理人员权限</h1>
      <p>当前账号没有访问用户与邀请码管理的权限。</p>
    </section>
  </AppLayout>
</template>

<style scoped>
.forbidden {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 80px 24px;
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  background: var(--color-surface-card);
  color: var(--color-error);
  text-align: center;
}

.forbidden strong {
  font-size: 48px;
}

.forbidden h1 {
  margin: 0;
  color: var(--color-ink);
}

.forbidden p {
  margin: 0;
  color: var(--color-body);
}
</style>
