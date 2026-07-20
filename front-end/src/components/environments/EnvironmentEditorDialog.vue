<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import type { CreateTestEnvironmentPayload, EnvironmentCatalogEnvironment, UpdateTestEnvironmentPayload } from '@/types/environment-catalog'

const props = defineProps<{
  environment: EnvironmentCatalogEnvironment | null
  submitting: boolean
  errorMessage: string
}>()

const emit = defineEmits<{
  submit: [payload: CreateTestEnvironmentPayload | UpdateTestEnvironmentPayload]
}>()

const visible = defineModel<boolean>('visible', { default: false })

const form = reactive({
  env_key: '',
  url_name: '',
  base_url: '',
  url_desc: '',
})
const validationMessage = computed(() => {
  if (!form.env_key.trim() && !props.environment) {
    return '请填写环境 key。'
  }
  if (!form.url_name.trim() || !form.base_url.trim() || !form.url_desc.trim()) {
    return '环境名称、环境地址和环境描述均为必填项。'
  }
  return ''
})
const isEditing = computed(() => props.environment !== null)
const dialogTitle = computed(() => (isEditing.value ? '编辑环境' : '新建环境'))

watch(
  [visible, () => props.environment],
  ([isVisible, environment]) => {
    if (!isVisible) {
      return
    }
    form.env_key = environment?.env_key ?? ''
    form.url_name = environment?.url_name ?? environment?.env_name ?? ''
    form.base_url = environment?.base_url ?? ''
    form.url_desc = environment?.url_desc ?? ''
  },
  { immediate: true },
)

function submit() {
  if (validationMessage.value) {
    return
  }
  const commonPayload = {
    url_name: form.url_name.trim(),
    base_url: form.base_url.trim(),
    url_desc: form.url_desc.trim(),
  }
  emit('submit', isEditing.value ? commonPayload : { env_key: form.env_key.trim(), ...commonPayload })
}
</script>

<template>
  <ElDialog v-model="visible" :title="dialogTitle" width="min(560px, calc(100vw - 32px))" :close-on-click-modal="false">
    <form class="environment-form" @submit.prevent="submit">
      <p v-if="validationMessage || errorMessage" class="form-error" role="alert">{{ validationMessage || errorMessage }}</p>

      <label class="form-field" for="environment-key">
        <span>环境 key</span>
        <input id="environment-key" v-model="form.env_key" :readonly="isEditing" :disabled="submitting" required autocomplete="off" />
        <small v-if="isEditing">环境 key 创建后不可修改。</small>
      </label>

      <label class="form-field" for="environment-name">
        <span>环境名称</span>
        <input id="environment-name" v-model="form.url_name" :disabled="submitting" required autocomplete="off" />
      </label>

      <label class="form-field" for="environment-url">
        <span>环境地址</span>
        <input id="environment-url" v-model="form.base_url" :disabled="submitting" required type="url" autocomplete="off" />
      </label>

      <label class="form-field" for="environment-description">
        <span>环境描述</span>
        <textarea id="environment-description" v-model="form.url_desc" :disabled="submitting" required rows="3" />
      </label>

      <footer class="dialog-actions">
        <button class="secondary-button" type="button" :disabled="submitting" @click="visible = false">取消</button>
        <button class="primary-button" type="submit" :disabled="submitting || Boolean(validationMessage)">
          {{ submitting ? '正在保存' : '保存环境' }}
        </button>
      </footer>
    </form>
  </ElDialog>
</template>

<style scoped>
.environment-form {
  display: grid;
  gap: 16px;
}

.form-field {
  display: grid;
  gap: 7px;
  color: var(--color-body);
  font-size: 14px;
  font-weight: 700;
}

.form-field input,
.form-field textarea {
  width: 100%;
  border: 1px solid var(--color-hairline);
  border-radius: 6px;
  background: var(--color-canvas);
  color: var(--color-ink);
  font: inherit;
  font-weight: 400;
}

.form-field input {
  height: 40px;
  padding: 0 11px;
}

.form-field textarea {
  min-height: 84px;
  padding: 10px 11px;
  resize: vertical;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: 2px solid color-mix(in srgb, var(--color-primary) 48%, transparent);
  outline-offset: 1px;
}

.form-field small {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 400;
}

.form-error {
  margin: 0;
  color: var(--color-error);
  font-size: 13px;
  font-weight: 700;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
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
</style>
