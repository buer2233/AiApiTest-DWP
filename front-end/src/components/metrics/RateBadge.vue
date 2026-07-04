<script setup lang="ts">
import { computed } from 'vue'

import type { RateValue } from '@/types/metrics'

const props = defineProps<{
  value: RateValue
  compact?: boolean
}>()

const normalizedRate = computed(() => {
  const numericValue = Number(props.value)
  if (!Number.isFinite(numericValue)) {
    return 0
  }
  return Math.min(Math.max(numericValue, 0), 1)
})

const percent = computed(() => normalizedRate.value * 100)
const percentText = computed(() => `${percent.value.toFixed(2)}%`)

const rateLevel = computed<'good' | 'warning' | 'danger'>(() => {
  if (percent.value >= 95) {
    return 'good'
  }
  if (percent.value >= 80) {
    return 'warning'
  }
  return 'danger'
})

const levelText = computed(() => {
  if (rateLevel.value === 'good') {
    return '稳定'
  }
  if (rateLevel.value === 'warning') {
    return '关注'
  }
  return '风险'
})
</script>

<template>
  <div class="rate-badge" :class="[`rate-badge--${rateLevel}`, { 'rate-badge--compact': compact }]">
    <div class="rate-badge__line">
      <strong>{{ percentText }}</strong>
      <span>{{ levelText }}</span>
    </div>
    <div class="rate-badge__track" aria-hidden="true">
      <span :style="{ width: `${percent}%` }"></span>
    </div>
  </div>
</template>

<style scoped>
.rate-badge {
  --rate-color: var(--color-success);
  display: grid;
  gap: 8px;
  min-width: 132px;
}

.rate-badge--warning {
  --rate-color: var(--color-warning);
}

.rate-badge--danger {
  --rate-color: var(--color-error);
}

.rate-badge__line {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.rate-badge__line strong {
  color: var(--color-ink);
  font-variant-numeric: tabular-nums;
}

.rate-badge__line span {
  color: var(--rate-color);
  font-size: 12px;
  font-weight: 700;
}

.rate-badge__track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--rate-color) 16%, var(--color-surface-card));
}

.rate-badge__track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--rate-color);
}

.rate-badge--compact {
  min-width: 118px;
  gap: 6px;
}
</style>
