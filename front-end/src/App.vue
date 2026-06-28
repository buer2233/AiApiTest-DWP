<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const isPublicRoute = computed(() => Boolean(route.meta.public))

function handleUnauthorized() {
  auth.clearSession()
}

onMounted(() => {
  window.addEventListener('auth:unauthorized', handleUnauthorized)
})

onUnmounted(() => {
  window.removeEventListener('auth:unauthorized', handleUnauthorized)
})
</script>

<template>
  <RouterView v-if="isPublicRoute" />
  <AppShell v-else>
    <RouterView />
  </AppShell>
</template>
