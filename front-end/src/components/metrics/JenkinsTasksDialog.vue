<script setup lang="ts">
import { computed, onUnmounted, reactive, shallowRef, watch } from 'vue'

import { cancelJenkinsTask, fetchModuleSnapshotJenkinsTasks, syncJenkinsTask } from '@/api/metrics'
import { toApiError } from '@/api/client'
import type { JenkinsTask, JenkinsTaskStatus, JenkinsTaskType, ModuleSnapshot } from '@/types/metrics'
import type { PaginationMeta } from '@/types/api'

const props = defineProps<{
  modelValue: boolean
  snapshot: ModuleSnapshot | null
  environmentName: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  taskUpdated: [task: JenkinsTask]
}>()

const tasks = shallowRef<JenkinsTask[]>([])
const loading = shallowRef(false)
const errorMessage = shallowRef('')
const cancelingTaskId = shallowRef<number | null>(null)
const syncing = shallowRef(false)
const refreshing = shallowRef(false)
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, per_page: 20, total_pages: 0 })
let pollTimer: number | null = null

const filters = reactive<{
  date: 'today' | string
  status: '' | JenkinsTaskStatus
  task_type: '' | JenkinsTaskType
}>({
  date: 'today',
  status: '',
  task_type: '',
})

const statusOptions: Array<{ label: string; value: JenkinsTaskStatus }> = [
  { value: 'queued', label: '排队中' },
  { value: 'running', label: '运行中' },
  { value: 'success', label: '成功' },
  { value: 'test_failed', label: '测试失败' },
  { value: 'failed', label: '执行失败' },
  { value: 'canceling', label: '取消中' },
  { value: 'canceled', label: '已取消' },
]

const taskTypeOptions: Array<{ label: string; value: JenkinsTaskType }> = [
  { value: 'daily_full', label: '每日全量' },
  { value: 'failed_rerun', label: '失败重试' },
  { value: 'module_rerun', label: '模块重试' },
]

const title = computed(() => {
  if (!props.snapshot) {
    return 'Jenkins 任务'
  }
  return `${props.snapshot.module_name} / ${props.environmentName} / Jenkins 任务`
})

const hasPollingTask = computed(() => {
  return tasks.value.some((task) => ['queued', 'running', 'canceling'].includes(task.status))
})

function statusLabel(status: JenkinsTaskStatus) {
  const labels: Record<JenkinsTaskStatus, string> = {
    queued: '排队中',
    running: '运行中',
    success: '成功',
    test_failed: '测试失败',
    failed: '执行失败',
    canceling: '取消中',
    canceled: '已取消',
  }
  return labels[status]
}

function taskTypeLabel(taskType: JenkinsTaskType) {
  const labels: Record<JenkinsTaskType, string> = {
    daily_full: '每日全量',
    failed_rerun: '失败重试',
    module_rerun: '模块重试',
  }
  return labels[taskType]
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', { hour12: false })
}

function closeDialog() {
  emit('update:modelValue', false)
}

function clearPollTimer() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function ensurePollTimer() {
  clearPollTimer()
  if (!props.modelValue || !hasPollingTask.value) {
    return
  }
  // P5 冻结轮询间隔为 5 秒；关闭弹窗时会在 watch 中清理。
  pollTimer = window.setInterval(() => {
    void refreshRunningTasks(meta.value.page || 1)
  }, 5000)
}

async function syncActiveTasks(): Promise<boolean> {
  if (syncing.value) {
    return true
  }
  const activeTasks = tasks.value.filter((task) => ['queued', 'running', 'canceling'].includes(task.status))
  if (activeTasks.length === 0) {
    return true
  }
  syncing.value = true
  try {
    const syncedTasks = await Promise.all(activeTasks.map((task) => syncJenkinsTask(task.id)))
    for (const syncedTask of syncedTasks) {
      tasks.value = tasks.value.map((task) => (task.id === syncedTask.id ? syncedTask : task))
      emit('taskUpdated', syncedTask)
    }
    return true
  } catch (error) {
    errorMessage.value = toApiError(error).message
    return false
  } finally {
    syncing.value = false
  }
}

async function refreshRunningTasks(page = 1) {
  if (refreshing.value) {
    return
  }
  refreshing.value = true
  try {
    const syncOk = await syncActiveTasks()
    await loadTasks(page, { preserveError: !syncOk })
  } finally {
    refreshing.value = false
  }
}

async function loadTasks(page = 1, options: { preserveError?: boolean } = {}) {
  if (!props.snapshot) {
    return
  }
  loading.value = true
  if (!options.preserveError) {
    errorMessage.value = ''
  }
  try {
    const response = await fetchModuleSnapshotJenkinsTasks(props.snapshot.id, {
      date: filters.date || 'today',
      status: filters.status || undefined,
      task_type: filters.task_type || undefined,
      page,
      per_page: meta.value.per_page || 20,
    })
    tasks.value = response.data
    meta.value = response.meta
  } catch (error) {
    tasks.value = []
    errorMessage.value = toApiError(error).message
  } finally {
    loading.value = false
    ensurePollTimer()
  }
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || (meta.value.total_pages > 0 && nextPage > meta.value.total_pages)) {
    return
  }
  await loadTasks(nextPage)
}

async function applyFilters() {
  await loadTasks(1)
}

async function cancelTask(task: JenkinsTask) {
  if (!task.actions.cancel || cancelingTaskId.value) {
    return
  }
  cancelingTaskId.value = task.id
  errorMessage.value = ''
  try {
    const updatedTask = await cancelJenkinsTask(task.id)
    tasks.value = tasks.value.map((item) => (item.id === updatedTask.id ? updatedTask : item))
    emit('taskUpdated', updatedTask)
  } catch (error) {
    errorMessage.value = toApiError(error).message
  } finally {
    cancelingTaskId.value = null
    ensurePollTimer()
  }
}

function resetLocalState() {
  tasks.value = []
  loading.value = false
  errorMessage.value = ''
  cancelingTaskId.value = null
  meta.value = { total: 0, page: 1, per_page: 20, total_pages: 0 }
  filters.date = 'today'
  filters.status = ''
  filters.task_type = ''
  clearPollTimer()
}

watch(
  () => [props.modelValue, props.snapshot?.id] as const,
  ([open]) => {
    if (open) {
      resetLocalState()
      void loadTasks(1)
    } else {
      resetLocalState()
    }
  },
)

onUnmounted(clearPollTimer)
</script>

<template>
  <el-dialog
    v-if="modelValue && snapshot"
    :model-value="modelValue"
    :title="title"
    width="min(1080px, calc(100vw - 32px))"
    destroy-on-close
    @close="closeDialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <section class="jenkins-dialog" aria-label="Jenkins 任务列表">
      <form class="jenkins-dialog__filters" @submit.prevent="applyFilters">
        <label for="jenkins-task-status-filter">
          <span>任务状态</span>
          <select id="jenkins-task-status-filter" v-model="filters.status" aria-label="任务状态">
            <option value="">全部状态</option>
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label for="jenkins-task-date-filter">
          <span>任务日期</span>
          <input id="jenkins-task-date-filter" v-model.trim="filters.date" aria-label="任务日期" placeholder="today 或 YYYY-MM-DD" />
        </label>
        <label for="jenkins-task-type-filter">
          <span>任务类型</span>
          <select id="jenkins-task-type-filter" v-model="filters.task_type" aria-label="任务类型">
            <option value="">全部类型</option>
            <option v-for="option in taskTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <button class="primary-button" type="submit">查询</button>
      </form>

      <p v-if="errorMessage" class="jenkins-dialog__error" role="alert">{{ errorMessage }}</p>

      <div v-loading="loading" class="jenkins-dialog__table-frame">
        <table class="jenkins-dialog__table">
          <thead>
            <tr>
              <th>任务</th>
              <th>任务类型</th>
              <th>任务名</th>
              <th>环境 URL</th>
              <th>状态</th>
              <th>触发人</th>
              <th>开始时间</th>
              <th>结束时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id">
              <td>#{{ task.id }}</td>
              <td>{{ taskTypeLabel(task.task_type) }}</td>
              <td>{{ task.job_name }}</td>
              <td class="jenkins-dialog__url">{{ task.environment_url }}</td>
              <td>{{ statusLabel(task.status) }}</td>
              <td>{{ task.triggered_by || '-' }}</td>
              <td>{{ formatDateTime(task.started_at) }}</td>
              <td>{{ formatDateTime(task.finished_at) }}</td>
              <td>
                <div class="jenkins-dialog__actions">
                  <button
                    class="secondary-button"
                    type="button"
                    :disabled="!task.actions.cancel || cancelingTaskId !== null"
                    @click="cancelTask(task)"
                  >
                    {{ cancelingTaskId === task.id ? '取消中' : '取消任务' }}
                  </button>
                  <a
                    v-if="task.actions.view_report && task.allure_report_url"
                    class="secondary-link"
                    :href="task.allure_report_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    查看报告
                  </a>
                  <button v-else class="secondary-button" type="button" disabled>查看报告</button>
                  <a
                    v-if="task.actions.view_jenkins_task && task.jenkins_build_url"
                    class="secondary-link"
                    :href="task.jenkins_build_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    查看 Jenkins 任务
                  </a>
                  <button v-else class="secondary-button" type="button" disabled>查看 Jenkins 任务</button>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && tasks.length === 0">
              <td colspan="9" class="jenkins-dialog__empty">暂无 Jenkins 任务</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-loading="loading" class="jenkins-dialog__mobile-list" aria-label="移动端 Jenkins 任务列表">
        <article v-for="task in tasks" :key="task.id" class="jenkins-dialog__mobile-card">
          <header>
            <strong>#{{ task.id }} {{ task.job_name }}</strong>
            <span>{{ statusLabel(task.status) }}</span>
          </header>
          <dl>
            <div>
              <dt>任务类型</dt>
              <dd>{{ taskTypeLabel(task.task_type) }}</dd>
            </div>
            <div>
              <dt>触发人</dt>
              <dd>{{ task.triggered_by || '-' }}</dd>
            </div>
            <div>
              <dt>开始时间</dt>
              <dd>{{ formatDateTime(task.started_at) }}</dd>
            </div>
            <div>
              <dt>结束时间</dt>
              <dd>{{ formatDateTime(task.finished_at) }}</dd>
            </div>
            <div>
              <dt>环境 URL</dt>
              <dd>{{ task.environment_url }}</dd>
            </div>
          </dl>
          <div class="jenkins-dialog__actions">
            <button
              class="secondary-button"
              type="button"
              :disabled="!task.actions.cancel || cancelingTaskId !== null"
              @click="cancelTask(task)"
            >
              {{ cancelingTaskId === task.id ? '取消中' : '取消任务' }}
            </button>
            <a
              v-if="task.actions.view_report && task.allure_report_url"
              class="secondary-link"
              :href="task.allure_report_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看报告
            </a>
            <button v-else class="secondary-button" type="button" disabled>查看报告</button>
            <a
              v-if="task.actions.view_jenkins_task && task.jenkins_build_url"
              class="secondary-link"
              :href="task.jenkins_build_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看 Jenkins 任务
            </a>
            <button v-else class="secondary-button" type="button" disabled>查看 Jenkins 任务</button>
          </div>
        </article>
        <p v-if="!loading && tasks.length === 0" class="jenkins-dialog__mobile-empty">暂无 Jenkins 任务</p>
      </div>
    </section>

    <template #footer>
      <div class="jenkins-dialog__footer">
        <span>共 {{ meta.total }} 条，当前第 {{ meta.page }} 页</span>
        <div class="jenkins-dialog__pagination-actions">
          <button class="secondary-button" type="button" :disabled="meta.page <= 1" @click="changePage(meta.page - 1)">
            上一页
          </button>
          <button
            class="secondary-button"
            type="button"
            :disabled="meta.total_pages === 0 || meta.page >= meta.total_pages"
            @click="changePage(meta.page + 1)"
          >
            下一页
          </button>
        </div>
        <button class="secondary-button" type="button" @click="closeDialog">关闭</button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.jenkins-dialog {
  display: grid;
  gap: 12px;
}

.jenkins-dialog__filters {
  display: grid;
  grid-template-columns: minmax(140px, 0.8fr) minmax(180px, 1fr) minmax(160px, 0.9fr) auto;
  align-items: end;
  gap: 10px;
}

.jenkins-dialog__filters label {
  display: grid;
  gap: 6px;
  min-width: 0;
  color: var(--color-body);
  font-size: 13px;
  font-weight: 800;
}

.jenkins-dialog__filters select,
.jenkins-dialog__filters input {
  min-height: 38px;
  width: 100%;
  padding: 0 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

.jenkins-dialog__table-frame {
  min-height: 180px;
  overflow-x: auto;
}

.jenkins-dialog__table {
  width: 100%;
  min-width: 980px;
  border-collapse: collapse;
  background: var(--color-canvas);
  font-size: 13px;
}

.jenkins-dialog__table th,
.jenkins-dialog__table td {
  padding: 10px;
  border: 1px solid var(--color-hairline);
  text-align: left;
  vertical-align: top;
}

.jenkins-dialog__table th {
  background: var(--color-surface-soft);
  color: var(--color-body);
  font-weight: 800;
}

.jenkins-dialog__url {
  max-width: 220px;
  overflow-wrap: anywhere;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
}

.jenkins-dialog__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.jenkins-dialog__empty {
  height: 72px;
  text-align: center !important;
  color: var(--color-muted);
  font-weight: 700;
}

.jenkins-dialog__error {
  margin: 0;
  color: var(--color-error);
  font-weight: 700;
}

.jenkins-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.jenkins-dialog__pagination-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.jenkins-dialog__mobile-list {
  display: none;
}

.primary-button,
.secondary-button,
.secondary-link {
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

.secondary-button:disabled,
.secondary-button:disabled:hover {
  border-color: var(--color-disabled-border);
  background: var(--color-disabled-bg);
  color: var(--color-disabled-text);
  cursor: not-allowed;
  box-shadow: none;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
  text-decoration: none;
}

@media (max-width: 700px) {
  .jenkins-dialog__filters {
    grid-template-columns: 1fr;
  }

  .jenkins-dialog__table-frame {
    display: none;
  }

  .jenkins-dialog__mobile-list {
    display: grid;
    gap: 10px;
    min-height: 160px;
  }

  .jenkins-dialog__mobile-card {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--color-hairline);
    border-radius: 8px;
    background: var(--color-canvas);
  }

  .jenkins-dialog__mobile-card header {
    display: flex;
    justify-content: space-between;
    gap: 10px;
  }

  .jenkins-dialog__mobile-card span {
    width: fit-content;
    height: fit-content;
    padding: 2px 8px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-primary) 16%, var(--color-canvas));
    color: var(--color-primary-active);
    font-size: 12px;
    font-weight: 800;
  }

  .jenkins-dialog__mobile-card strong,
  .jenkins-dialog__mobile-card dd {
    overflow-wrap: anywhere;
  }

  .jenkins-dialog__mobile-card dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 0;
  }

  .jenkins-dialog__mobile-card div {
    min-width: 0;
  }

  .jenkins-dialog__mobile-card dt {
    color: var(--color-muted);
    font-size: 12px;
    font-weight: 800;
  }

  .jenkins-dialog__mobile-card dd {
    margin: 0;
    color: var(--color-body);
    font-size: 13px;
  }

  .jenkins-dialog__footer {
    align-items: stretch;
    flex-direction: column;
  }

  .jenkins-dialog__mobile-empty {
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
