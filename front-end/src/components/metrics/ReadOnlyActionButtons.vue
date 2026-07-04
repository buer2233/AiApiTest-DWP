<script setup lang="ts">
import { computed } from 'vue'

import type { ModuleSnapshotActions } from '@/types/metrics'

const props = defineProps<{
  actions: ModuleSnapshotActions
}>()

const emit = defineEmits<{
  trend: [days: 7 | 30]
}>()

const actionItems = computed(() => [
  { key: 'failed_rerun', label: '失败重试', enabled: props.actions.failed_rerun },
  { key: 'module_rerun', label: '模块重试', enabled: props.actions.module_rerun },
  { key: 'trend_7d', label: '7天趋势', enabled: props.actions.trend_7d },
  { key: 'trend_30d', label: '30天趋势', enabled: props.actions.trend_30d },
  { key: 'jenkins_tasks', label: 'Jenkins 任务', enabled: props.actions.jenkins_tasks },
])

function handleAction(key: string) {
  if (key === 'trend_7d' && props.actions.trend_7d) {
    emit('trend', 7)
  }
  if (key === 'trend_30d' && props.actions.trend_30d) {
    emit('trend', 30)
  }
}
</script>

<template>
  <div class="readonly-actions" aria-label="后置能力占位">
    <button
      v-for="item in actionItems"
      :key="item.key"
      class="readonly-actions__button"
      type="button"
      :disabled="!item.enabled"
      @click="handleAction(item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<style scoped>
.readonly-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 260px;
}

.readonly-actions__button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-body);
  font-size: 12px;
  font-weight: 700;
}

.readonly-actions__button:disabled {
  background: var(--color-surface-soft);
  color: var(--color-muted);
  opacity: 0.68;
}
</style>
