<script setup lang="ts">
import { computed } from 'vue'

import type { ModuleSnapshotActionKey, ModuleSnapshotActionReasons, ModuleSnapshotActions } from '@/types/metrics'

const props = defineProps<{
  actions: ModuleSnapshotActions
  disabledReasons?: ModuleSnapshotActionReasons
  loadingActions?: Partial<Record<ModuleSnapshotActionKey, boolean>>
}>()

const emit = defineEmits<{
  failedRerun: []
  moduleRerun: []
  jenkinsTasks: []
  trend: [days: 7 | 30]
}>()

const actionItems = computed(() => [
  { key: 'failed_rerun' as const, label: '失败重试', enabled: props.actions.failed_rerun },
  { key: 'module_rerun' as const, label: '模块重试', enabled: props.actions.module_rerun },
  { key: 'trend_7d' as const, label: '7天趋势', enabled: props.actions.trend_7d },
  { key: 'trend_30d' as const, label: '30天趋势', enabled: props.actions.trend_30d },
  { key: 'jenkins_tasks' as const, label: 'Jenkins 任务', enabled: props.actions.jenkins_tasks },
])

function isLoading(key: ModuleSnapshotActionKey) {
  return Boolean(props.loadingActions?.[key])
}

function isDisabled(key: ModuleSnapshotActionKey, enabled: boolean) {
  return !enabled || isLoading(key)
}

function getButtonLabel(key: ModuleSnapshotActionKey, label: string) {
  return isLoading(key) ? '提交中' : label
}

function getDisabledReason(key: ModuleSnapshotActionKey, enabled: boolean) {
  if (isLoading(key)) {
    return '请求提交中'
  }
  if (enabled) {
    return ''
  }
  return props.disabledReasons?.[key] || '当前操作不可用'
}

function handleAction(key: ModuleSnapshotActionKey) {
  if (isDisabled(key, props.actions[key])) {
    return
  }
  if (key === 'failed_rerun') {
    emit('failedRerun')
  }
  if (key === 'module_rerun') {
    emit('moduleRerun')
  }
  if (key === 'trend_7d' && props.actions.trend_7d) {
    emit('trend', 7)
  }
  if (key === 'trend_30d' && props.actions.trend_30d) {
    emit('trend', 30)
  }
  if (key === 'jenkins_tasks') {
    emit('jenkinsTasks')
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
      :disabled="isDisabled(item.key, item.enabled)"
      :title="getDisabledReason(item.key, item.enabled)"
      @click="handleAction(item.key)"
    >
      {{ getButtonLabel(item.key, item.label) }}
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
