<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'

import { toApiError } from '@/api/client'
import { fetchModuleSnapshotTrend } from '@/api/metrics'
import type { ModuleSnapshot, ModuleTrend, ModuleTrendPoint, RateValue } from '@/types/metrics'

const props = defineProps<{
  modelValue: boolean
  snapshot: ModuleSnapshot | null
  environmentName: string
  days: 7 | 30
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const trend = shallowRef<ModuleTrend | null>(null)
const loading = shallowRef(false)
const errorMessage = shallowRef('')

const title = computed(() => {
  const moduleName = props.snapshot?.module_name ?? '模块'
  const environmentName = trend.value?.module.environment_name || props.environmentName
  return `${moduleName} / ${environmentName} / 近 ${props.days} 天趋势`
})

const series = computed(() => trend.value?.series ?? [])

const hasSeries = computed(() => series.value.length > 0)

const polylinePoints = computed(() => {
  if (!hasSeries.value) {
    return ''
  }
  const rates = series.value.map((item) => Number(item.pass_rate))
  const min = Math.min(...rates)
  const max = Math.max(...rates)
  const range = max - min || 0.01
  return series.value
    .map((item, index) => {
      const x = 32 + (index * 416) / Math.max(series.value.length - 1, 1)
      const y = 128 - ((Number(item.pass_rate) - min) / range) * 88
      return `${x},${y}`
    })
    .join(' ')
})

const firstRate = computed(() => formatPercent(series.value[0]?.pass_rate))
const lastRate = computed(() => formatPercent(series.value.at(-1)?.pass_rate))

function closeDialog() {
  emit('update:modelValue', false)
}

function formatPercent(value: RateValue | undefined) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '-'
  }
  return `${(numeric * 100).toFixed(2)}%`
}

function formatDuration(value: ModuleTrendPoint['duration_seconds']) {
  const seconds = Number(value)
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '-'
  }
  return `${seconds.toFixed(1)}秒`
}

async function loadTrend() {
  if (!props.snapshot) {
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    trend.value = await fetchModuleSnapshotTrend(props.snapshot.id, props.days)
  } catch (error) {
    const apiError = toApiError(error)
    trend.value = null
    errorMessage.value = apiError.message
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.snapshot?.id, props.days] as const,
  ([open]) => {
    if (open) {
      void loadTrend()
    } else {
      trend.value = null
      errorMessage.value = ''
    }
  },
  { immediate: true },
)
</script>

<template>
  <el-dialog
    v-if="modelValue && snapshot"
    :model-value="modelValue"
    :title="title"
    width="min(920px, calc(100vw - 32px))"
    destroy-on-close
    @close="closeDialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <section v-loading="loading" class="trend-dialog" aria-label="模块趋势">
      <p v-if="errorMessage" class="trend-dialog__error" role="alert">{{ errorMessage }}</p>

      <template v-if="hasSeries">
        <p class="trend-dialog__summary">
          区间通过率从 {{ firstRate }} 到 {{ lastRate }}，趋势数据来自后端历史模块运行记录。
        </p>
        <svg class="trend-dialog__chart" viewBox="0 0 480 160" aria-label="通过率趋势折线图" role="img">
          <line x1="32" y1="136" x2="448" y2="136" />
          <line x1="32" y1="24" x2="32" y2="136" />
          <polyline :points="polylinePoints" fill="none" />
          <circle
            v-for="point in polylinePoints.split(' ')"
            :key="point"
            :cx="Number(point.split(',')[0])"
            :cy="Number(point.split(',')[1])"
            r="4"
          />
        </svg>
      </template>

      <div v-else-if="!loading" class="trend-dialog__empty">
        <strong>暂无趋势数据</strong>
        <span>当前模块在所选窗口内没有历史运行记录。</span>
      </div>

      <div class="trend-dialog__table-frame">
        <table class="trend-dialog__table">
          <thead>
            <tr>
              <th>日期</th>
              <th>运行类型</th>
              <th>总数</th>
              <th>失败</th>
              <th>跳过</th>
              <th>通过率</th>
              <th>执行时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in series" :key="`${row.run_date}-${row.run_type}`">
              <td>{{ row.run_date }}</td>
              <td>{{ row.run_type }}</td>
              <td>{{ row.total_count }}</td>
              <td>{{ row.failed_count }}</td>
              <td>{{ row.skipped_count }}</td>
              <td>{{ formatPercent(row.pass_rate) }}</td>
              <td>{{ formatDuration(row.duration_seconds) }}</td>
            </tr>
            <tr v-if="!loading && series.length === 0">
              <td colspan="7" class="trend-dialog__no-record">无历史记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <template #footer>
      <button class="secondary-button" type="button" @click="closeDialog">关闭</button>
    </template>
  </el-dialog>
</template>

<style scoped>
.trend-dialog {
  display: grid;
  gap: 14px;
  min-height: 220px;
}

.trend-dialog__summary,
.trend-dialog__error {
  margin: 0;
  color: var(--color-body);
  font-weight: 700;
}

.trend-dialog__error {
  color: var(--color-error);
}

.trend-dialog__chart {
  width: 100%;
  max-height: 240px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
}

.trend-dialog__chart line {
  stroke: var(--color-hairline);
  stroke-width: 2;
}

.trend-dialog__chart polyline {
  stroke: var(--color-primary);
  stroke-width: 4;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.trend-dialog__chart circle {
  fill: var(--color-primary);
  stroke: var(--color-canvas);
  stroke-width: 2;
}

.trend-dialog__empty {
  display: grid;
  place-items: center;
  min-height: 150px;
  border: 1px dashed var(--color-hairline);
  border-radius: 8px;
  background: var(--color-surface-soft);
  color: var(--color-muted);
  text-align: center;
}

.trend-dialog__empty strong {
  color: var(--color-ink);
}

.trend-dialog__table-frame {
  overflow-x: auto;
}

.trend-dialog__table {
  width: 100%;
  min-width: 700px;
  border-collapse: collapse;
  background: var(--color-canvas);
  font-size: 13px;
}

.trend-dialog__table th,
.trend-dialog__table td {
  padding: 10px;
  border: 1px solid var(--color-hairline);
  text-align: left;
}

.trend-dialog__table th {
  background: var(--color-surface-soft);
  color: var(--color-body);
  font-weight: 800;
}

.trend-dialog__no-record {
  height: 64px;
  text-align: center !important;
  color: var(--color-muted);
  font-weight: 700;
}

.secondary-button {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-body);
  font-weight: 700;
}
</style>
