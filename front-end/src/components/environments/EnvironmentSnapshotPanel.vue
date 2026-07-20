<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchEnvironmentSummary, fetchTestEnvironments } from '@/api/metrics'
import MetricStatTile from '@/components/metrics/MetricStatTile.vue'
import RateBadge from '@/components/metrics/RateBadge.vue'
import type { EnvironmentSummary, TestEnvironment } from '@/types/metrics'

const route = useRoute()
const router = useRouter()

const environments = shallowRef<TestEnvironment[]>([])
const selectedEnvironmentId = shallowRef<number | null>(null)
const summary = shallowRef<EnvironmentSummary | null>(null)
const environmentLoading = shallowRef(false)
const summaryLoading = shallowRef(false)
const errorMessage = shallowRef('')

const selectedEnvironment = computed(() => {
  return environments.value.find((environment) => environment.id === selectedEnvironmentId.value) ?? summary.value?.environment ?? null
})

const hasSnapshot = computed(() => {
  return Boolean(summary.value?.started_at || summary.value?.finished_at || summary.value?.total_count)
})

const moduleLink = computed(() => {
  return selectedEnvironmentId.value ? `/modules?environment_id=${selectedEnvironmentId.value}` : '/modules'
})

function normalizeEnvironmentId(value: unknown): number | null {
  const rawValue = Array.isArray(value) ? value[0] : value
  const numericValue = Number(rawValue)
  return Number.isInteger(numericValue) && numericValue > 0 ? numericValue : null
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(value: string | number | null | undefined): string {
  const seconds = Number(value)
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '-'
  }
  return seconds >= 60 ? `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒` : `${seconds.toFixed(1)}秒`
}

async function loadSummary(environmentId: number) {
  summaryLoading.value = true
  errorMessage.value = ''
  try {
    summary.value = await fetchEnvironmentSummary(environmentId)
  } catch {
    summary.value = null
    errorMessage.value = '环境汇总加载失败，请稍后重试。'
  } finally {
    summaryLoading.value = false
  }
}

async function loadEnvironments() {
  environmentLoading.value = true
  errorMessage.value = ''
  try {
    environments.value = await fetchTestEnvironments({ is_active: true })
    const queryEnvironmentId = normalizeEnvironmentId(route.query.environment_id)
    selectedEnvironmentId.value = queryEnvironmentId ?? environments.value[0]?.id ?? null
    if (selectedEnvironmentId.value) {
      await loadSummary(selectedEnvironmentId.value)
    }
  } catch {
    errorMessage.value = '测试环境加载失败，请稍后重试。'
  } finally {
    environmentLoading.value = false
  }
}

async function changeEnvironment() {
  if (!selectedEnvironmentId.value) {
    return
  }
  await router.replace({ path: '/environments', query: { environment_id: String(selectedEnvironmentId.value) } })
  await loadSummary(selectedEnvironmentId.value)
}

onMounted(loadEnvironments)
</script>

<template>
  <section class="snapshot-panel" aria-labelledby="environment-summary-title">
    <header class="snapshot-heading">
      <div>
        <p class="eyebrow">测试运营 / 环境通过率</p>
        <h1 id="environment-summary-title" class="serif-title">环境通过率</h1>
      </div>
      <RouterLink class="secondary-link" :to="moduleLink">模块通过率</RouterLink>
    </header>

    <p v-if="errorMessage" class="status-line" role="alert">
      {{ errorMessage }}
      <button type="button" class="text-button" @click="loadEnvironments">重试</button>
    </p>

    <div v-if="environmentLoading" class="summary-skeleton" aria-label="环境快照加载中">
      <span v-for="index in 4" :key="index" />
    </div>

    <template v-else>
      <div class="summary-grid">
        <label class="environment-card" for="environment-select">
          <span class="card-label">当前查看环境</span>
          <select
            id="environment-select"
            v-model.number="selectedEnvironmentId"
            :disabled="environments.length === 0"
            @change="changeEnvironment"
          >
            <option v-for="environment in environments" :key="environment.id" :value="environment.id">
              {{ environment.env_name }}
            </option>
          </select>
          <code>{{ selectedEnvironment?.base_url || '暂无启用环境' }}</code>
        </label>
        <div class="rate-card" :aria-busy="summaryLoading">
          <span class="card-label">模块通过率</span>
          <RateBadge :value="summary?.pass_rate ?? 0" />
        </div>
        <MetricStatTile label="已通过 / 总用例" :value="`${summary?.passed_count ?? 0} / ${summary?.total_count ?? 0}`" />
        <MetricStatTile label="启用环境" :value="environments.length" tone="success" />
      </div>

      <section v-if="summary && hasSnapshot" class="run-window" aria-label="最近执行窗口">
        <div>
          <span>最近开始</span>
          <strong>{{ formatDateTime(summary.started_at) }}</strong>
        </div>
        <div>
          <span>最近结束</span>
          <strong>{{ formatDateTime(summary.finished_at) }}</strong>
        </div>
        <div>
          <span>执行时长</span>
          <strong>{{ formatDuration(summary.duration_seconds) }}</strong>
        </div>
      </section>

      <p v-if="environments.length === 0" class="empty-state">暂无启用环境，请联系管理员维护环境目录。</p>
      <p v-else-if="summary && !hasSnapshot" class="empty-state">当前环境暂无执行结果。</p>
    </template>
  </section>
</template>

<style scoped>
.snapshot-panel {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.snapshot-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--color-hairline);
}

.eyebrow,
.card-label {
  margin: 0;
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 700;
}

.snapshot-heading h1 {
  margin: 4px 0 0;
  font-size: 32px;
}

.secondary-link,
.text-button {
  color: var(--color-body);
  font-size: 14px;
  font-weight: 700;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  text-decoration: none;
}

.text-button {
  margin-left: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  text-decoration: underline;
}

.summary-grid {
  display: grid;
  grid-template-columns: minmax(230px, 1.5fr) minmax(185px, 1fr) repeat(2, minmax(150px, 0.8fr));
  gap: 12px;
}

.environment-card,
.rate-card {
  display: grid;
  align-content: start;
  gap: 8px;
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-surface-soft);
}

.environment-card select {
  min-width: 0;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 6px;
  background: var(--color-canvas);
  color: var(--color-ink);
  font-weight: 700;
}

.environment-card code {
  overflow-wrap: anywhere;
  color: var(--color-body);
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
}

.run-window {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--color-surface-dark);
  color: var(--color-on-dark);
}

.run-window div {
  display: grid;
  gap: 4px;
}

.run-window span {
  color: color-mix(in srgb, var(--color-on-dark) 66%, var(--color-surface-dark));
  font-size: 12px;
}

.run-window strong {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.status-line {
  margin: 0;
  color: var(--color-error);
  font-weight: 700;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 72px;
  margin: 0;
  border: 1px dashed var(--color-hairline);
  border-radius: 8px;
  color: var(--color-muted);
  font-weight: 700;
}

.summary-skeleton {
  display: grid;
  grid-template-columns: minmax(230px, 1.5fr) minmax(185px, 1fr) repeat(2, minmax(150px, 0.8fr));
  gap: 12px;
}

.summary-skeleton span {
  min-height: 118px;
  border-radius: 8px;
  background: var(--color-surface-card);
}

@media (max-width: 1024px) {
  .summary-grid,
  .summary-skeleton {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .snapshot-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .run-window {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .summary-grid,
  .summary-skeleton {
    grid-template-columns: 1fr;
  }
}
</style>
