<script setup lang="ts">
import { Ellipsis, Pencil, RotateCcw } from '@lucide/vue'
import { computed } from 'vue'

import type { EnvironmentCatalogEnvironment, EnvironmentCatalogState } from '@/types/environment-catalog'

const props = defineProps<{
  environments: EnvironmentCatalogEnvironment[]
  catalogState: EnvironmentCatalogState | null
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [environment: EnvironmentCatalogEnvironment]
  toggleActive: [environment: EnvironmentCatalogEnvironment]
  showSync: []
}>()

const syncStatusText = computed(() => {
  const status = props.catalogState?.status
  const labels: Record<string, string> = {
    pending: '待处理',
    queued: '已进入队列',
    running: '同步中',
    synced: '已同步',
    failed: '同步失败',
    conflict: '存在冲突',
  }
  return labels[status ?? ''] ?? '暂无同步记录'
})

const syncStatusClass = computed(() => `sync-badge--${props.catalogState?.status ?? 'unknown'}`)

function activeText(environment: EnvironmentCatalogEnvironment) {
  return environment.is_active ? '启用' : '已停用'
}
</script>

<template>
  <div class="table-scroll">
    <table class="catalog-table" :aria-busy="loading">
      <thead>
        <tr>
          <th scope="col">环境 KEY</th>
          <th scope="col">环境名称</th>
          <th scope="col">BASE URL</th>
          <th scope="col">描述</th>
          <th scope="col">状态</th>
          <th scope="col">目录同步</th>
          <th scope="col" class="action-column">操作</th>
        </tr>
      </thead>
      <tbody v-if="loading">
        <tr v-for="index in 5" :key="index" class="skeleton-row" aria-hidden="true">
          <td v-for="column in 7" :key="column"><span /></td>
        </tr>
      </tbody>
      <tbody v-else-if="environments.length">
        <tr v-for="environment in environments" :key="environment.id">
          <td><code>{{ environment.env_key }}</code></td>
          <td>
            <strong>{{ environment.url_name || environment.env_name }}</strong>
            <span v-if="environment.url_name !== environment.env_name" class="secondary-value">{{ environment.env_name }}</span>
          </td>
          <td><span class="url-value" :title="environment.base_url">{{ environment.base_url }}</span></td>
          <td><span class="description-value" :title="environment.url_desc">{{ environment.url_desc }}</span></td>
          <td>
            <span class="state-badge" :class="environment.is_active ? 'state-badge--active' : 'state-badge--inactive'">
              {{ activeText(environment) }}
            </span>
          </td>
          <td>
            <button class="sync-badge" :class="syncStatusClass" type="button" @click="emit('showSync')">{{ syncStatusText }}</button>
          </td>
          <td class="row-actions">
            <button class="row-action" type="button" :aria-label="`编辑 ${environment.env_key}`" title="编辑" @click="emit('edit', environment)">
              <Pencil :size="16" />
            </button>
            <button
              class="row-action"
              type="button"
              :aria-label="environment.is_active ? `停用 ${environment.env_key}` : `恢复 ${environment.env_key}`"
              :title="environment.is_active ? '停用' : '恢复'"
              @click="emit('toggleActive', environment)"
            >
              <RotateCcw :size="16" />
            </button>
            <button class="row-action" type="button" aria-label="更多环境操作" title="更多环境操作" @click="emit('showSync')">
              <Ellipsis :size="17" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-if="!loading && environments.length === 0" class="empty-state">没有符合当前筛选条件的环境。</p>
</template>

<style scoped>
.table-scroll {
  overflow-x: auto;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
}

.catalog-table {
  width: 100%;
  min-width: 940px;
  border-collapse: collapse;
  background: var(--color-canvas);
  text-align: left;
}

.catalog-table th,
.catalog-table td {
  padding: 13px 14px;
  border-bottom: 1px solid var(--color-hairline);
  vertical-align: middle;
}

.catalog-table th {
  background: var(--color-surface-soft);
  color: var(--color-body);
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.catalog-table tbody tr:last-child td {
  border-bottom: 0;
}

.catalog-table code {
  color: var(--color-ink);
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 13px;
}

.catalog-table strong,
.secondary-value {
  display: block;
}

.catalog-table strong {
  color: var(--color-ink);
  font-size: 14px;
}

.secondary-value {
  margin-top: 3px;
  color: var(--color-muted);
  font-size: 12px;
}

.url-value,
.description-value {
  display: block;
  max-width: 210px;
  overflow: hidden;
  color: var(--color-body);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.url-value {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
}

.state-badge,
.sync-badge {
  display: inline-flex;
  align-items: center;
  min-height: 25px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.state-badge--active {
  background: color-mix(in srgb, var(--color-success) 18%, var(--color-canvas));
  color: #2d7c43;
}

.state-badge--inactive {
  background: var(--color-surface-card);
  color: var(--color-muted);
}

.sync-badge {
  border: 0;
  background: var(--color-surface-card);
  color: var(--color-body);
}

.sync-badge--synced {
  background: color-mix(in srgb, var(--color-success) 16%, var(--color-canvas));
  color: #2d7c43;
}

.sync-badge--pending,
.sync-badge--queued,
.sync-badge--running {
  background: color-mix(in srgb, var(--color-warning) 18%, var(--color-canvas));
  color: #8a6200;
}

.sync-badge--failed,
.sync-badge--conflict {
  background: color-mix(in srgb, var(--color-error) 14%, var(--color-canvas));
  color: #9e3535;
}

.row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.action-column {
  text-align: right;
}

.row-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--color-hairline);
  border-radius: 6px;
  background: var(--color-canvas);
  color: var(--color-body);
}

.skeleton-row span {
  display: block;
  min-width: 70px;
  min-height: 14px;
  border-radius: 4px;
  background: var(--color-surface-card);
}

.empty-state {
  margin: 0;
  padding: 36px 16px;
  border: 1px dashed var(--color-hairline);
  border-radius: 8px;
  color: var(--color-muted);
  text-align: center;
  font-weight: 700;
}
</style>
