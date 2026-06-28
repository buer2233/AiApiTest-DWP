<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
}>()

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    active: '可用',
    disabled: '已禁用',
    exhausted: '已用尽',
    expired: '已过期',
    synced: '已同步',
    missing: '缺失',
  }
  return labels[props.status] || props.status
})

const badgeClass = computed(() => `status-badge status-badge--${props.status}`)
</script>

<template>
  <span :class="badgeClass">{{ statusLabel }}</span>
</template>
