<script setup lang="ts">
import { computed, reactive, shallowRef, watch } from 'vue'

import { toApiError } from '@/api/client'
import { updateCaseResultStatus } from '@/api/metrics'
import type { CaseDisplayStatus, CaseResult, CaseStatusUpdateResult } from '@/types/metrics'

const props = defineProps<{
  modelValue: boolean
  caseResult: CaseResult | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  updated: [result: CaseStatusUpdateResult]
}>()

const submitting = shallowRef(false)
const errorMessage = shallowRef('')
const form = reactive({
  display_status: 'skipped' as CaseDisplayStatus,
  reason: '',
})

const statusOptions: Array<{ value: CaseDisplayStatus; label: string }> = [
  { value: 'failed', label: '失败' },
  { value: 'passed', label: '通过' },
  { value: 'skipped', label: '跳过' },
]

const currentStatusLabel = computed(() => {
  return statusOptions.find((item) => item.value === props.caseResult?.display_status)?.label ?? '-'
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open || !props.caseResult) {
      return
    }
    form.display_status = statusOptions.find((item) => item.value !== props.caseResult?.display_status)?.value ?? 'skipped'
    form.reason = ''
    errorMessage.value = ''
  },
)

function closeDialog() {
  if (!submitting.value) {
    emit('update:modelValue', false)
  }
}

async function submitStatusUpdate() {
  if (!props.caseResult || submitting.value) {
    return
  }
  if (!form.reason.trim()) {
    errorMessage.value = '修改原因必填。'
    return
  }
  submitting.value = true
  errorMessage.value = ''
  try {
    const result = await updateCaseResultStatus(props.caseResult.id, {
      display_status: form.display_status,
      reason: form.reason.trim(),
    })
    emit('updated', result)
    emit('update:modelValue', false)
  } catch (error) {
    const apiError = toApiError(error)
    errorMessage.value = apiError.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="修改用例状态"
    width="520px"
    destroy-on-close
    append-to-body
    @close="closeDialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <form class="status-form" @submit.prevent="submitStatusUpdate">
      <p class="status-form__summary">
        当前状态：<strong>{{ currentStatusLabel }}</strong>
      </p>

      <label class="status-form__field" for="status-target">
        <span>目标状态</span>
        <select id="status-target" v-model="form.display_status" :disabled="submitting">
          <option
            v-for="option in statusOptions"
            :key="option.value"
            :value="option.value"
            :disabled="option.value === caseResult?.display_status"
          >
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="status-form__field" for="status-reason">
        <span>修改原因</span>
        <textarea
          id="status-reason"
          v-model.trim="form.reason"
          :disabled="submitting"
          maxlength="512"
          rows="4"
          placeholder="说明人工确认依据"
        />
      </label>

      <p class="status-form__hint">保存后会写入审计记录，并刷新模块与环境通过率统计。</p>
      <p v-if="errorMessage" class="status-form__error" role="alert">{{ errorMessage }}</p>
    </form>

    <template #footer>
      <div class="status-form__footer">
        <button class="secondary-button" type="button" :disabled="submitting" @click="closeDialog">取消</button>
        <button class="primary-button" type="button" :disabled="submitting" @click="submitStatusUpdate">
          {{ submitting ? '保存中' : '保存修改' }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.status-form {
  display: grid;
  gap: 14px;
}

.status-form__summary,
.status-form__hint,
.status-form__error {
  margin: 0;
}

.status-form__summary {
  color: var(--color-body);
}

.status-form__summary strong {
  color: var(--color-ink);
}

.status-form__field {
  display: grid;
  gap: 6px;
  color: var(--color-body);
  font-size: 13px;
  font-weight: 700;
}

.status-form__field select,
.status-form__field textarea {
  width: 100%;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
  font: inherit;
}

.status-form__field select {
  min-height: 40px;
  padding: 0 12px;
}

.status-form__field textarea {
  min-height: 104px;
  padding: 10px 12px;
  resize: vertical;
}

.status-form__hint {
  color: var(--color-muted);
  font-size: 13px;
}

.status-form__error {
  color: var(--color-error);
  font-weight: 700;
}

.status-form__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.primary-button,
.secondary-button {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  font-weight: 700;
}

.primary-button {
  border: 0;
  background: var(--color-primary);
  color: white;
}

.secondary-button {
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
}
</style>
