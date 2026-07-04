<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  tone?: 'default' | 'success' | 'warning' | 'danger'
}>()
</script>

<template>
  <article class="metric-stat" :class="tone ? `metric-stat--${tone}` : ''">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
  </article>
</template>

<style scoped>
.metric-stat {
  display: grid;
  gap: 6px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
}

.metric-stat span {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 700;
}

.metric-stat strong {
  color: var(--color-ink);
  font-size: 22px;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}

.metric-stat--success {
  border-color: color-mix(in srgb, var(--color-success) 38%, var(--color-hairline));
}

.metric-stat--warning {
  border-color: color-mix(in srgb, var(--color-warning) 38%, var(--color-hairline));
}

.metric-stat--danger {
  border-color: color-mix(in srgb, var(--color-error) 38%, var(--color-hairline));
}
</style>
