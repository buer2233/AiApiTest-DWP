<script setup lang="ts">
import { computed, reactive, shallowRef, watch } from 'vue'

import { toApiError } from '@/api/client'
import { createFailedCaseRetry, fetchModuleSnapshotCases } from '@/api/metrics'
import CaseStatusUpdateDialog from '@/components/metrics/CaseStatusUpdateDialog.vue'
import type {
  CaseDisplayStatus,
  CaseResult,
  CaseStatusUpdateResult,
  JenkinsTask,
  ModuleSnapshot,
} from '@/types/metrics'

const props = defineProps<{
  modelValue: boolean
  snapshot: ModuleSnapshot | null
  environmentName: string
  isAdmin: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  statusUpdated: [result: CaseStatusUpdateResult]
  retryCreated: [task: JenkinsTask]
}>()

const cases = shallowRef<CaseResult[]>([])
const loading = shallowRef(false)
const errorMessage = shallowRef('')
const successMessage = shallowRef('')
const expandedCaseId = shallowRef<number | null>(null)
const statusDialogOpen = shallowRef(false)
const selectedCase = shallowRef<CaseResult | null>(null)
const meta = shallowRef({ total: 0, page: 1, per_page: 20, total_pages: 0 })
const selectedRetryCaseIds = shallowRef<number[]>([])
const retrySubmitting = shallowRef<'selected' | 'all' | null>(null)

const filters = reactive({
  status: 'failed' as CaseDisplayStatus,
  case_name: '',
  node_id: '',
  error_type: '',
})

const casePerPageOptions = [20, 50, 100]

const title = computed(() => {
  if (!props.snapshot) {
    return '用例详情'
  }
  return `${props.snapshot.module_name} / ${props.environmentName} / 用例详情`
})

const emptyText = computed(() => {
  const labelMap: Record<CaseDisplayStatus, string> = {
    failed: '暂无失败用例',
    passed: '暂无通过用例',
    skipped: '暂无跳过用例',
  }
  return labelMap[filters.status]
})

const selectedRetryCount = computed(() => selectedRetryCaseIds.value.length)

function closeDialog() {
  emit('update:modelValue', false)
}

function resetLocalState() {
  cases.value = []
  loading.value = false
  errorMessage.value = ''
  successMessage.value = ''
  expandedCaseId.value = null
  selectedCase.value = null
  statusDialogOpen.value = false
  selectedRetryCaseIds.value = []
  retrySubmitting.value = null
  meta.value = { total: 0, page: 1, per_page: 20, total_pages: 0 }
  filters.status = 'failed'
  filters.case_name = ''
  filters.node_id = ''
  filters.error_type = ''
}

async function loadCases(page = 1) {
  if (!props.snapshot) {
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchModuleSnapshotCases(props.snapshot.id, {
      status: filters.status,
      case_name: filters.case_name || undefined,
      node_id: filters.node_id || undefined,
      error_type: filters.error_type || undefined,
      page,
      per_page: meta.value.per_page,
    })
    cases.value = response.data
    meta.value = response.meta
    expandedCaseId.value = null
    selectedRetryCaseIds.value = []
  } catch (error) {
    const apiError = toApiError(error)
    cases.value = []
    errorMessage.value = apiError.message
  } finally {
    loading.value = false
  }
}

function isCaseRetryable(row: CaseResult) {
  return props.isAdmin && row.display_status === 'failed' && row.actions.can_retry
}

function isCaseSelected(row: CaseResult) {
  return selectedRetryCaseIds.value.includes(row.id)
}

function toggleRetryCase(row: CaseResult, checked: boolean) {
  if (!isCaseRetryable(row)) {
    return
  }
  const nextIds = new Set(selectedRetryCaseIds.value)
  if (checked) {
    nextIds.add(row.id)
  } else {
    nextIds.delete(row.id)
  }
  selectedRetryCaseIds.value = Array.from(nextIds)
}

async function retrySelectedCases() {
  if (!props.snapshot || selectedRetryCaseIds.value.length === 0 || retrySubmitting.value) {
    return
  }
  retrySubmitting.value = 'selected'
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const task = await createFailedCaseRetry(props.snapshot.id, {
      retry_scope: 'selected_failed',
      case_result_ids: selectedRetryCaseIds.value,
    })
    successMessage.value = '开始执行失败重试'
    selectedRetryCaseIds.value = []
    emit('retryCreated', task)
  } catch (error) {
    errorMessage.value = toApiError(error).message
  } finally {
    retrySubmitting.value = null
  }
}

async function retryAllFailedCases() {
  if (!props.snapshot || retrySubmitting.value) {
    return
  }
  retrySubmitting.value = 'all'
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const task = await createFailedCaseRetry(props.snapshot.id, { retry_scope: 'all_failed' })
    successMessage.value = '开始执行失败重试'
    selectedRetryCaseIds.value = []
    emit('retryCreated', task)
  } catch (error) {
    errorMessage.value = toApiError(error).message
  } finally {
    retrySubmitting.value = null
  }
}

function changeStatus(nextStatus: CaseDisplayStatus) {
  if (filters.status === nextStatus) {
    return
  }
  filters.status = nextStatus
  successMessage.value = ''
  void loadCases(1)
}

function resetFilters() {
  filters.status = 'failed'
  filters.case_name = ''
  filters.node_id = ''
  filters.error_type = ''
  successMessage.value = ''
  void loadCases(1)
}

function changeCasePage(nextPage: number) {
  if (nextPage < 1 || (meta.value.total_pages > 0 && nextPage > meta.value.total_pages)) {
    return
  }
  successMessage.value = ''
  void loadCases(nextPage)
}

function changeCasePerPage(event: Event) {
  const nextPerPage = Number((event.target as HTMLSelectElement).value)
  meta.value = {
    ...meta.value,
    per_page: casePerPageOptions.includes(nextPerPage) ? nextPerPage : 20,
  }
  successMessage.value = ''
  void loadCases(1)
}

function openStatusDialog(row: CaseResult) {
  selectedCase.value = row
  statusDialogOpen.value = true
}

function handleStatusUpdated(result: CaseStatusUpdateResult) {
  successMessage.value = '状态已更新，审计记录已写入'
  emit('statusUpdated', result)
  void loadCases(meta.value.page)
}

function formatStatus(value: string) {
  const labelMap: Record<string, string> = {
    failed: '失败',
    passed: '通过',
    skipped: '跳过',
    error: '错误',
  }
  return labelMap[value] ?? value
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      resetLocalState()
      void loadCases(1)
    } else {
      resetLocalState()
    }
  },
)
</script>

<template>
  <el-dialog
    v-if="modelValue && snapshot"
    :model-value="modelValue"
    :title="title"
    width="min(1120px, calc(100vw - 32px))"
    destroy-on-close
    @close="closeDialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <section class="case-dialog" aria-label="用例详情">
      <div class="case-dialog__toolbar">
        <div class="case-dialog__segments" aria-label="用例状态筛选">
          <button
            v-for="item in [
              { value: 'failed', label: '失败' },
              { value: 'passed', label: '通过' },
              { value: 'skipped', label: '跳过' },
            ]"
            :key="item.value"
            type="button"
            :class="{ 'case-dialog__segment--active': filters.status === item.value }"
            @click="changeStatus(item.value as CaseDisplayStatus)"
          >
            {{ item.label }}
          </button>
        </div>

        <form class="case-dialog__filters" @submit.prevent="loadCases(1)">
          <label>
            <span>用例名</span>
            <input v-model.trim="filters.case_name" type="search" />
          </label>
          <label>
            <span>来源 node id</span>
            <input v-model.trim="filters.node_id" type="search" />
          </label>
          <label>
            <span>错误类型</span>
            <input v-model.trim="filters.error_type" type="search" />
          </label>
          <button class="primary-button" type="submit">查询</button>
          <button class="secondary-button" type="button" @click="resetFilters">重置</button>
        </form>

        <div class="case-dialog__retry-actions" aria-label="失败重试操作">
          <span>已选 {{ selectedRetryCount }} 条</span>
          <button
            class="secondary-button"
            type="button"
            :disabled="selectedRetryCount === 0 || retrySubmitting !== null"
            @click="retrySelectedCases"
          >
            {{ retrySubmitting === 'selected' ? '提交中' : '重试选中用例' }}
          </button>
          <button
            class="primary-button"
            type="button"
            :disabled="!isAdmin || retrySubmitting !== null"
            @click="retryAllFailedCases"
          >
            {{ retrySubmitting === 'all' ? '提交中' : '一键失败重试' }}
          </button>
        </div>
      </div>

      <p v-if="successMessage" class="case-dialog__success">{{ successMessage }}</p>
      <p v-if="errorMessage" class="case-dialog__error" role="alert">{{ errorMessage }}</p>

      <div v-loading="loading" class="case-dialog__table-frame">
        <table class="case-dialog__table">
          <thead>
            <tr>
              <th>选择</th>
              <th>用例名</th>
              <th>来源</th>
              <th>简述</th>
              <th>错误类型</th>
              <th>断言</th>
              <th>执行状态</th>
              <th>展示状态</th>
              <th>错误摘要</th>
              <th>确认结果</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in cases" :key="row.id">
              <td>
                <input
                  type="checkbox"
                  :aria-label="`选择 ${row.case_name}`"
                  :checked="isCaseSelected(row)"
                  :disabled="!isCaseRetryable(row)"
                  @change="toggleRetryCase(row, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td>{{ row.case_name }}</td>
              <td class="case-dialog__node">{{ row.node_id }}</td>
              <td>{{ row.case_summary || '-' }}</td>
              <td>{{ row.error_type || '-' }}</td>
              <td>{{ row.assertion_text || '-' }}</td>
              <td>{{ formatStatus(row.execution_status) }}</td>
              <td>{{ formatStatus(row.display_status) }}</td>
              <td>{{ row.error_message_summary || '-' }}</td>
              <td>{{ row.confirmation_result || '-' }}</td>
              <td>
                <div class="case-dialog__row-actions">
                  <button
                    v-if="isAdmin && row.error_message_detail"
                    class="secondary-button"
                    type="button"
                    @click="expandedCaseId = expandedCaseId === row.id ? null : row.id"
                  >
                    查看详情
                  </button>
                  <button
                    v-if="isAdmin && row.actions.can_update_status"
                    class="secondary-button"
                    type="button"
                    @click="openStatusDialog(row)"
                  >
                    修改状态
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && cases.length === 0">
              <td colspan="11" class="case-dialog__empty">{{ emptyText }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-loading="loading" class="case-dialog__mobile-list" aria-label="移动端用例详情列表">
        <article v-for="row in cases" :key="row.id" class="case-dialog__mobile-card">
          <header class="case-dialog__mobile-card-header">
            <div>
              <span>{{ formatStatus(row.display_status) }}</span>
              <strong>{{ row.case_name }}</strong>
            </div>
            <input
              type="checkbox"
              :aria-label="`选择 ${row.case_name}`"
              :checked="isCaseSelected(row)"
              :disabled="!isCaseRetryable(row)"
              @change="toggleRetryCase(row, ($event.target as HTMLInputElement).checked)"
            />
          </header>

          <p class="case-dialog__mobile-node">{{ row.node_id }}</p>

          <dl class="case-dialog__mobile-facts">
            <div>
              <dt>简述</dt>
              <dd>{{ row.case_summary || '-' }}</dd>
            </div>
            <div>
              <dt>错误类型</dt>
              <dd>{{ row.error_type || '-' }}</dd>
            </div>
            <div>
              <dt>断言</dt>
              <dd>{{ row.assertion_text || '-' }}</dd>
            </div>
            <div>
              <dt>执行状态</dt>
              <dd>{{ formatStatus(row.execution_status) }}</dd>
            </div>
            <div>
              <dt>展示状态</dt>
              <dd>{{ formatStatus(row.display_status) }}</dd>
            </div>
            <div>
              <dt>确认结果</dt>
              <dd>{{ row.confirmation_result || '-' }}</dd>
            </div>
          </dl>

          <p class="case-dialog__mobile-summary">{{ row.error_message_summary || '-' }}</p>
          <div class="case-dialog__row-actions">
            <button
              v-if="isAdmin && row.error_message_detail"
              class="secondary-button"
              type="button"
              @click="expandedCaseId = expandedCaseId === row.id ? null : row.id"
            >
              查看详情
            </button>
            <button
              v-if="isAdmin && row.actions.can_update_status"
              class="secondary-button"
              type="button"
              @click="openStatusDialog(row)"
            >
              修改状态
            </button>
          </div>
        </article>
        <p v-if="!loading && cases.length === 0" class="case-dialog__mobile-empty">{{ emptyText }}</p>
      </div>

      <article v-if="expandedCaseId" class="case-dialog__detail">
        <h3>脱敏错误详情</h3>
        <pre>{{ cases.find((row) => row.id === expandedCaseId)?.error_message_detail }}</pre>
      </article>
    </section>

    <template #footer>
      <div class="case-dialog__footer">
        <span>共 {{ meta.total }} 条，当前第 {{ meta.page }} 页</span>
        <div class="case-dialog__pagination-actions">
          <label class="case-dialog__per-page" for="case-detail-per-page">
            <span>每页条数</span>
            <select id="case-detail-per-page" :value="meta.per_page" @change="changeCasePerPage">
              <option v-for="option in casePerPageOptions" :key="option" :value="option">{{ option }}</option>
            </select>
          </label>
          <button class="secondary-button" type="button" :disabled="meta.page <= 1" @click="changeCasePage(meta.page - 1)">
            上一页
          </button>
          <button
            class="secondary-button"
            type="button"
            :disabled="meta.total_pages === 0 || meta.page >= meta.total_pages"
            @click="changeCasePage(meta.page + 1)"
          >
            下一页
          </button>
        </div>
        <button class="secondary-button" type="button" @click="closeDialog">关闭</button>
      </div>
    </template>

    <CaseStatusUpdateDialog
      v-model="statusDialogOpen"
      :case-result="selectedCase"
      @updated="handleStatusUpdated"
    />
  </el-dialog>
</template>

<style scoped>
.case-dialog {
  display: grid;
  gap: 14px;
}

.case-dialog__toolbar,
.case-dialog__filters {
  display: grid;
  gap: 10px;
}

.case-dialog__retry-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 700;
}

.case-dialog__segments {
  display: inline-flex;
  width: fit-content;
  padding: 4px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-surface-soft);
}

.case-dialog__segments button {
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-body);
  font-weight: 700;
}

.case-dialog__segment--active {
  background: var(--color-primary) !important;
  color: white !important;
}

.case-dialog__filters {
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto auto;
  align-items: end;
}

.case-dialog__filters label {
  display: grid;
  gap: 6px;
  color: var(--color-body);
  font-size: 13px;
  font-weight: 700;
}

.case-dialog__filters input {
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

.case-dialog__table-frame {
  min-height: 180px;
  overflow-x: auto;
}

.case-dialog__mobile-list {
  display: none;
}

.case-dialog__table {
  width: 100%;
  min-width: 1040px;
  border-collapse: collapse;
  background: var(--color-canvas);
  font-size: 13px;
}

.case-dialog__table th,
.case-dialog__table td {
  padding: 10px;
  border: 1px solid var(--color-hairline);
  text-align: left;
  vertical-align: top;
}

.case-dialog__table th {
  background: var(--color-surface-soft);
  color: var(--color-body);
  font-weight: 800;
}

.case-dialog__node {
  max-width: 220px;
  overflow-wrap: anywhere;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
}

.case-dialog__row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.case-dialog__detail {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  background: var(--color-surface-dark);
  color: var(--color-on-dark);
}

.case-dialog__detail h3 {
  margin: 0;
  font-size: 14px;
}

.case-dialog__detail pre {
  max-height: 180px;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--color-on-dark);
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
}

.case-dialog__empty {
  height: 72px;
  text-align: center !important;
  color: var(--color-muted);
  font-weight: 700;
}

.case-dialog__success,
.case-dialog__error {
  margin: 0;
  font-weight: 700;
}

.case-dialog__success {
  color: var(--color-success);
}

.case-dialog__error {
  color: var(--color-error);
}

.case-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.case-dialog__pagination-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.case-dialog__per-page {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 700;
}

.case-dialog__per-page select {
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

.primary-button,
.secondary-button {
  min-height: 38px;
  padding: 0 12px;
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

@media (max-width: 700px) {
  .case-dialog__filters {
    grid-template-columns: 1fr;
  }

  .case-dialog__retry-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .case-dialog__table-frame {
    display: none;
  }

  .case-dialog__mobile-list {
    display: grid;
    gap: 10px;
    min-height: 160px;
  }

  .case-dialog__footer {
    align-items: stretch;
    flex-direction: column;
  }

  .case-dialog__pagination-actions {
    align-items: stretch;
  }

  .case-dialog__per-page {
    justify-content: space-between;
  }

  .case-dialog__mobile-card {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--color-hairline);
    border-radius: 8px;
    background: var(--color-canvas);
  }

  .case-dialog__mobile-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }

  .case-dialog__mobile-card-header div {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .case-dialog__mobile-card-header span {
    width: fit-content;
    padding: 2px 8px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-primary) 16%, var(--color-canvas));
    color: var(--color-primary-active);
    font-size: 12px;
    font-weight: 800;
  }

  .case-dialog__mobile-card-header strong,
  .case-dialog__mobile-node,
  .case-dialog__mobile-summary,
  .case-dialog__mobile-facts dd {
    overflow-wrap: anywhere;
  }

  .case-dialog__mobile-node {
    margin: 0;
    color: var(--color-muted);
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: 12px;
  }

  .case-dialog__mobile-facts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 0;
  }

  .case-dialog__mobile-facts div {
    display: grid;
    gap: 3px;
    min-width: 0;
  }

  .case-dialog__mobile-facts dt {
    color: var(--color-muted);
    font-size: 12px;
    font-weight: 800;
  }

  .case-dialog__mobile-facts dd {
    margin: 0;
    color: var(--color-body);
    font-size: 13px;
  }

  .case-dialog__mobile-summary {
    margin: 0;
    padding: 8px;
    border-radius: 8px;
    background: var(--color-surface-soft);
    color: var(--color-body);
    font-size: 13px;
  }

  .case-dialog__mobile-empty {
    display: grid;
    place-items: center;
    min-height: 120px;
    margin: 0;
    border: 1px dashed var(--color-hairline);
    border-radius: 8px;
    color: var(--color-muted);
    font-weight: 700;
  }
}
</style>
