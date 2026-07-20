<script setup lang="ts">
import { computed } from 'vue'

import type { EnvironmentCatalogState, EnvironmentCatalogSyncAttempt } from '@/types/environment-catalog'

const props = defineProps<{
  catalogState: EnvironmentCatalogState | null
  attempt: EnvironmentCatalogSyncAttempt | null
  submitting: boolean
  errorMessage: string
}>()

const emit = defineEmits<{
  importYaml: []
  retry: []
  refresh: []
}>()

const visible = defineModel<boolean>('visible', { default: false })

const currentStatus = computed(() => props.attempt?.status ?? props.catalogState?.status ?? 'unknown')
const statusText = computed(() => {
  const labels: Record<string, string> = {
    pending: '等待同步处理',
    queued: '已进入队列',
    running: '同步正在执行',
    synced: '目录已同步',
    failed: '同步失败',
    conflict: '目录存在冲突',
  }
  return labels[currentStatus.value] ?? '暂无同步记录'
})
const isFailed = computed(() => currentStatus.value === 'failed')
const isConflict = computed(() => currentStatus.value === 'conflict')
const isActive = computed(() => ['pending', 'queued', 'running'].includes(currentStatus.value))
const diagnostic = computed(() => props.attempt?.error_summary ?? props.catalogState?.last_error_summary ?? '')

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <ElDialog v-model="visible" title="环境目录同步" width="min(620px, calc(100vw - 32px))" :close-on-click-modal="false">
    <section class="sync-dialog" aria-live="polite">
      <div class="sync-status" :class="`sync-status--${currentStatus}`">
        <span>当前状态</span>
        <strong>{{ statusText }}</strong>
        <small v-if="attempt">请求 #{{ attempt.id }} · {{ formatDateTime(attempt.created_at) }}</small>
      </div>

      <p v-if="isActive" class="status-help">同步状态会自动刷新；关闭弹窗不会取消后台同步。</p>
      <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
      <p v-if="diagnostic" class="diagnostic" role="alert">{{ diagnostic }}</p>

      <dl v-if="attempt" class="sync-details">
        <div>
          <dt>同步方向</dt>
          <dd>{{ attempt.direction }}</dd>
        </div>
        <div>
          <dt>队列编号</dt>
          <dd>{{ attempt.queue_id || '-' }}</dd>
        </div>
        <div>
          <dt>提交标识</dt>
          <dd>{{ attempt.commit_sha || '-' }}</dd>
        </div>
        <div v-if="isConflict">
          <dt>期望 YAML SHA</dt>
          <dd>{{ attempt.expected_yaml_blob_sha || '-' }}</dd>
        </div>
        <div v-if="isConflict">
          <dt>当前 YAML SHA</dt>
          <dd>{{ attempt.observed_yaml_blob_sha || '-' }}</dd>
        </div>
      </dl>

      <section v-if="isConflict" class="conflict-help">
        <strong>YAML 已有新的版本。</strong>
        <p>请先导入 YAML 更新目录，或关闭本窗口后重新提交本次变更。系统不会直接覆盖冲突版本。</p>
      </section>

      <footer class="dialog-actions">
        <button class="secondary-button" type="button" :disabled="submitting" @click="emit('refresh')">刷新状态</button>
        <button v-if="isFailed" class="secondary-button" type="button" :disabled="submitting" @click="emit('retry')">重试同步</button>
        <button v-if="isConflict" class="secondary-button" type="button" :disabled="submitting" @click="emit('importYaml')">先导入 YAML</button>
        <button class="primary-button" type="button" :disabled="submitting || isActive" @click="emit('importYaml')">
          {{ submitting ? '正在提交' : '从 YAML 导入' }}
        </button>
      </footer>
    </section>
  </ElDialog>
</template>

<style scoped>
.sync-dialog {
  display: grid;
  gap: 16px;
}

.sync-status {
  display: grid;
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-surface-soft);
}

.sync-status span,
.sync-status small {
  color: var(--color-muted);
  font-size: 12px;
}

.sync-status strong {
  color: var(--color-ink);
  font-size: 18px;
}

.sync-status--failed,
.sync-status--conflict {
  border-color: color-mix(in srgb, var(--color-error) 45%, var(--color-hairline));
}

.sync-status--synced {
  border-color: color-mix(in srgb, var(--color-success) 45%, var(--color-hairline));
}

.status-help,
.diagnostic,
.conflict-help p,
.form-error {
  margin: 0;
  font-size: 13px;
}

.status-help {
  color: var(--color-muted);
}

.diagnostic,
.form-error {
  color: var(--color-error);
  font-weight: 700;
}

.sync-details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.sync-details div {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 6px;
}

.sync-details dt {
  color: var(--color-muted);
  font-size: 12px;
}

.sync-details dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  color: var(--color-body);
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
}

.conflict-help {
  padding: 12px;
  border-left: 3px solid var(--color-error);
  background: color-mix(in srgb, var(--color-error) 8%, var(--color-canvas));
}

.conflict-help p {
  margin-top: 5px;
  color: var(--color-body);
}

.dialog-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.primary-button,
.secondary-button {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
}

.primary-button {
  border: 0;
  background: var(--color-primary);
  color: #fff;
}

.secondary-button {
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
}

.primary-button:disabled,
.secondary-button:disabled {
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.primary-button:disabled {
  background: var(--color-disabled-bg);
}

@media (max-width: 480px) {
  .sync-details {
    grid-template-columns: 1fr;
  }

  .dialog-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
