<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchEnvironmentSummary, fetchTestEnvironments } from '@/api/metrics'
import AppLayout from '@/components/layout/AppLayout.vue'
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
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(value: string | number | null | undefined): string {
  const seconds = Number(value)
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '-'
  }
  if (seconds >= 60) {
    return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`
  }
  return `${seconds.toFixed(1)}秒`
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

function showReportPlaceholder() {
  ElMessage.info('AI 分析报告功能后续实现')
}

onMounted(loadEnvironments)
</script>

<template>
  <AppLayout>
    <section class="page-panel">
      <header class="page-heading">
        <div>
          <h1 class="serif-title">环境通过率</h1>
          <p>只读查看当前测试环境最新执行快照，报告生成在后续阶段接入。</p>
        </div>
        <RouterLink class="secondary-link" :to="moduleLink">模块通过率</RouterLink>
      </header>

      <div class="filter-bar">
        <label class="filter-field" for="environment-select">
          <span>测试环境</span>
          <select
            id="environment-select"
            v-model.number="selectedEnvironmentId"
            :disabled="environmentLoading || environments.length === 0"
            @change="changeEnvironment"
          >
            <option v-for="environment in environments" :key="environment.id" :value="environment.id">
              {{ environment.env_name }}
            </option>
          </select>
        </label>
        <button class="primary-button" type="button" :disabled="!summary?.actions.generate_report" @click="showReportPlaceholder">
          生成环境报告
        </button>
      </div>

      <p v-if="errorMessage" class="status-line" role="alert">{{ errorMessage }}</p>

      <section v-loading="summaryLoading" class="summary-grid" aria-label="通过率汇总">
        <div class="environment-card">
          <span class="card-label">当前环境</span>
          <strong>{{ selectedEnvironment?.env_name || '暂无环境' }}</strong>
          <code>{{ selectedEnvironment?.base_url || '-' }}</code>
        </div>
        <div class="rate-card">
          <span class="card-label">通过率</span>
          <RateBadge :value="summary?.pass_rate ?? 0" />
        </div>
        <MetricStatTile label="总用例数" :value="summary?.total_count ?? 0" />
        <MetricStatTile label="通过" :value="summary?.passed_count ?? 0" tone="success" />
        <MetricStatTile label="失败" :value="summary?.failed_count ?? 0" tone="danger" />
        <MetricStatTile label="跳过" :value="summary?.skipped_count ?? 0" tone="warning" />
      </section>

      <section class="run-window" aria-label="运行窗口">
        <div>
          <span>开始时间</span>
          <strong>{{ formatDateTime(summary?.started_at) }}</strong>
        </div>
        <div>
          <span>结束时间</span>
          <strong>{{ formatDateTime(summary?.finished_at) }}</strong>
        </div>
        <div>
          <span>运行时间</span>
          <strong>{{ formatDuration(summary?.duration_seconds) }}</strong>
        </div>
      </section>

      <p v-if="summary && !hasSnapshot" class="empty-state">暂无执行结果</p>
    </section>
  </AppLayout>
</template>

<style scoped>
.page-panel {
  display: grid;
  gap: 18px;
  min-width: 0;
  padding: 24px;
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  background: color-mix(in srgb, var(--color-canvas) 88%, white);
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 12px;
}

.filter-field {
  display: grid;
  gap: 6px;
  min-width: min(260px, 100%);
  color: var(--color-body);
  font-size: 13px;
  font-weight: 700;
}

.filter-field select {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

h1 {
  margin: 0 0 8px;
  font-size: 32px;
}

p {
  margin: 0;
  color: var(--color-muted);
}

.primary-button,
.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.primary-button {
  border: 0;
  background: var(--color-primary);
  color: white;
}

.primary-button:disabled {
  background: var(--color-hairline);
  color: var(--color-muted);
}

.secondary-link {
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
}

.summary-grid {
  display: grid;
  grid-template-columns: minmax(220px, 1.3fr) minmax(180px, 1fr) repeat(4, minmax(120px, 0.7fr));
  gap: 12px;
  min-width: 0;
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
  background: var(--color-canvas);
}

.environment-card strong {
  color: var(--color-ink);
  font-size: 20px;
}

.environment-card code {
  overflow-wrap: anywhere;
  color: var(--color-body);
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 13px;
}

.card-label {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 700;
}

.run-window {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  background: var(--color-surface-dark);
  color: var(--color-on-dark);
}

.run-window div {
  display: grid;
  gap: 5px;
}

.run-window span {
  color: color-mix(in srgb, var(--color-on-dark) 68%, var(--color-surface-dark));
  font-size: 12px;
}

.run-window strong {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.status-line {
  color: var(--color-error);
  font-weight: 700;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 92px;
  border: 1px dashed var(--color-hairline);
  border-radius: 8px;
  background: var(--color-surface-soft);
  color: var(--color-muted);
  font-weight: 700;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .page-panel {
    padding: 18px;
  }

  .page-heading,
  .filter-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid,
  .run-window {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 28px;
  }
}
</style>
