<script setup lang="ts">
import { storeToRefs } from 'pinia'

import EnvironmentCatalogSection from '@/components/environments/EnvironmentCatalogSection.vue'
import EnvironmentSnapshotPanel from '@/components/environments/EnvironmentSnapshotPanel.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const { isAdmin } = storeToRefs(authStore)
</script>

<template>
  <AppLayout>
    <main class="environment-workspace">
      <EnvironmentSnapshotPanel />
      <EnvironmentCatalogSection v-if="isAdmin" />
    </main>
  </AppLayout>
</template>

<style scoped>
.environment-workspace {
  display: grid;
  gap: 26px;
  min-width: 0;
  padding: 24px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-canvas) 88%, white);
}

@media (max-width: 768px) {
  .environment-workspace {
    padding: 18px;
  }
}
</style>
