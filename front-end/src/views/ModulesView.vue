<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/client'
import {
  createFailedCaseRetry,
  createModuleRerun,
  fetchModuleSnapshotFilterOptions,
  fetchModuleSnapshots,
  fetchTestEnvironments,
} from '@/api/metrics'
import AppLayout from '@/components/layout/AppLayout.vue'
import CaseDetailsDialog from '@/components/metrics/CaseDetailsDialog.vue'
import JenkinsTasksDialog from '@/components/metrics/JenkinsTasksDialog.vue'
import ModuleTrendDialog from '@/components/metrics/ModuleTrendDialog.vue'
import RateBadge from '@/components/metrics/RateBadge.vue'
import ReadOnlyActionButtons from '@/components/metrics/ReadOnlyActionButtons.vue'
import { useAuthStore } from '@/stores/auth'
import type { PaginationMeta } from '@/types/api'
import type {
  CaseStatusUpdateResult,
  JenkinsTask,
  ModuleSnapshot,
  ModuleSnapshotActionKey,
  ModuleSnapshotFilterOptions,
  TestEnvironment,
} from '@/types/metrics'

type ExecutionAction = 'failed_rerun' | 'module_rerun'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const environments = shallowRef<TestEnvironment[]>([])
const modules = shallowRef<ModuleSnapshot[]>([])
const filterOptions = shallowRef<ModuleSnapshotFilterOptions>({
  module_names: [],
  package_names: [],
  module_devs: [],
  module_tests: [],
})
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, per_page: 20, total_pages: 0 })
const loading = shallowRef(false)
const environmentLoading = shallowRef(false)
const filterOptionsLoading = shallowRef(false)
const errorMessage = shallowRef('')
const filterOptionsError = shallowRef('')
const selectedSnapshot = shallowRef<ModuleSnapshot | null>(null)
const caseDialogOpen = shallowRef(false)
const trendDialogOpen = shallowRef(false)
const trendDays = shallowRef<7 | 30>(7)
const jenkinsTasksDialogOpen = shallowRef(false)
const confirmDialogOpen = shallowRef(false)
const pendingExecutionAction = shallowRef<ExecutionAction | null>(null)
const submittingExecutionAction = shallowRef<ExecutionAction | null>(null)
const operationMessage = shallowRef('')
const operationError = shallowRef('')
const loadedFilterOptionsEnvironmentId = shallowRef('')

const filters = reactive({
  environment_id: '',
  module_name: [] as string[],
  package_name: [] as string[],
  module_dev: [] as string[],
  module_test: [] as string[],
  sort: 'pass_rate,-completed_at',
})

const currentPage = shallowRef(1)
const perPage = shallowRef(20)

const selectedEnvironmentName = computed(() => {
  return environments.value.find((environment) => String(environment.id) === filters.environment_id)?.env_name ?? '当前环境'
})

const isAdmin = computed(() => authStore.isAdmin)

const confirmTitle = computed(() => {
  return '确认模块重试'
})

const confirmDescription = computed(() => {
  return '模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？'
})

const confirmButtonLabel = computed(() => {
  return submittingExecutionAction.value === 'module_rerun' ? '提交中' : '确认模块重试'
})

function getQueryValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value[0] ? String(value[0]) : ''
  }
  return value ? String(value) : ''
}

function getQueryValues(value: unknown): string[] {
  const rawValue = getQueryValue(value)
  if (!rawValue) {
    return []
  }
  return rawValue
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function joinSelectedOptions(values: string[]): string | undefined {
  return values.length > 0 ? values.join(',') : undefined
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(value: string | number | null): string {
  const seconds = Number(value)
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '-'
  }
  return `${seconds.toFixed(1)}秒`
}

function syncFiltersFromRoute() {
  filters.environment_id = getQueryValue(route.query.environment_id)
  filters.module_name = getQueryValues(route.query.module_name)
  filters.package_name = getQueryValues(route.query.package_name)
  filters.module_dev = getQueryValues(route.query.module_dev)
  filters.module_test = getQueryValues(route.query.module_test)
  filters.sort = getQueryValue(route.query.sort) || 'pass_rate,-completed_at'
  currentPage.value = Number(getQueryValue(route.query.page) || 1)
  if (!Number.isInteger(currentPage.value) || currentPage.value < 1) {
    currentPage.value = 1
  }
  const nextPerPage = Number(getQueryValue(route.query.per_page) || 20)
  perPage.value = [20, 50, 100].includes(nextPerPage) ? nextPerPage : 20
}

function buildQuery(nextPage = 1) {
  const query: Record<string, string> = {}
  if (filters.environment_id) {
    query.environment_id = filters.environment_id
  }
  const multiSelectEntries = {
    module_name: joinSelectedOptions(filters.module_name),
    package_name: joinSelectedOptions(filters.package_name),
    module_dev: joinSelectedOptions(filters.module_dev),
    module_test: joinSelectedOptions(filters.module_test),
  }
  for (const [key, value] of Object.entries(multiSelectEntries)) {
    if (value) {
      query[key] = value
    }
  }
  if (filters.sort) {
    query.sort = filters.sort
  }
  if (nextPage > 1) {
    query.page = String(nextPage)
  }
  if (perPage.value !== 20) {
    query.per_page = String(perPage.value)
  }
  return query
}

function isSameRouteQuery(nextQuery: Record<string, string>) {
  const currentEntries = Object.entries(route.query)
    .map(([key, value]) => [key, getQueryValue(value)] as const)
    .filter(([, value]) => value)
    .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
  const nextEntries = Object.entries(nextQuery)
    .filter(([, value]) => value)
    .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
  if (currentEntries.length !== nextEntries.length) {
    return false
  }
  return nextEntries.every(([key, value], index) => currentEntries[index][0] === key && currentEntries[index][1] === value)
}

async function refreshCurrentQuery(nextPage = 1) {
  currentPage.value = nextPage
  await Promise.all([loadFilterOptions(), loadModules()])
}

async function ensureDefaultEnvironmentSelected() {
  if (filters.environment_id || !environments.value[0]) {
    return false
  }
  filters.environment_id = String(environments.value[0].id)
  await router.replace({ path: '/modules', query: buildQuery(1) })
  return true
}

async function loadEnvironments() {
  environmentLoading.value = true
  try {
    environments.value = await fetchTestEnvironments({ is_active: true })
    await ensureDefaultEnvironmentSelected()
  } finally {
    environmentLoading.value = false
  }
}

async function loadFilterOptions() {
  if (!filters.environment_id) {
    filterOptions.value = { module_names: [], package_names: [], module_devs: [], module_tests: [] }
    loadedFilterOptionsEnvironmentId.value = ''
    return
  }
  if (loadedFilterOptionsEnvironmentId.value === filters.environment_id) {
    return
  }
  filterOptionsLoading.value = true
  filterOptionsError.value = ''
  try {
    filterOptions.value = await fetchModuleSnapshotFilterOptions({
      environment_id: Number(filters.environment_id),
    })
    loadedFilterOptionsEnvironmentId.value = filters.environment_id
  } catch {
    filterOptions.value = { module_names: [], package_names: [], module_devs: [], module_tests: [] }
    loadedFilterOptionsEnvironmentId.value = ''
    filterOptionsError.value = '筛选选项加载失败，可稍后重试。'
  } finally {
    filterOptionsLoading.value = false
  }
}

async function loadModules() {
  if (!filters.environment_id) {
    modules.value = []
    meta.value = { total: 0, page: 1, per_page: perPage.value, total_pages: 0 }
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchModuleSnapshots({
      environment_id: Number(filters.environment_id),
      module_name: joinSelectedOptions(filters.module_name),
      package_name: joinSelectedOptions(filters.package_name),
      module_dev: joinSelectedOptions(filters.module_dev),
      module_test: joinSelectedOptions(filters.module_test),
      sort: filters.sort || undefined,
      page: currentPage.value,
      per_page: perPage.value,
    })
    modules.value = response.data
    meta.value = response.meta
  } catch {
    modules.value = []
    errorMessage.value = '模块快照加载失败，请检查筛选条件后重试。'
  } finally {
    loading.value = false
  }
}

function actionLoadingFor(row: ModuleSnapshot): Partial<Record<ModuleSnapshotActionKey, boolean>> {
  return {
    failed_rerun: submittingExecutionAction.value === 'failed_rerun' && selectedSnapshot.value?.id === row.id,
    module_rerun: submittingExecutionAction.value === 'module_rerun' && selectedSnapshot.value?.id === row.id,
  }
}

async function triggerFailedRerun(snapshot: ModuleSnapshot) {
  selectedSnapshot.value = snapshot
  operationMessage.value = ''
  operationError.value = ''
  submittingExecutionAction.value = 'failed_rerun'
  try {
    await createFailedCaseRetry(snapshot.id, { retry_scope: 'all_failed' })
    operationMessage.value = '开始执行失败重试'
    await loadModules()
  } catch (error) {
    operationError.value = toApiError(error).message
  } finally {
    submittingExecutionAction.value = null
  }
}

function openExecutionConfirm(snapshot: ModuleSnapshot, action: ExecutionAction) {
  if (action === 'failed_rerun') {
    void triggerFailedRerun(snapshot)
    return
  }
  selectedSnapshot.value = snapshot
  pendingExecutionAction.value = action
  operationMessage.value = ''
  operationError.value = ''
  confirmDialogOpen.value = true
}

function closeExecutionConfirm() {
  if (submittingExecutionAction.value) {
    return
  }
  confirmDialogOpen.value = false
  pendingExecutionAction.value = null
}

async function confirmExecutionAction() {
  if (!selectedSnapshot.value || pendingExecutionAction.value !== 'module_rerun' || submittingExecutionAction.value) {
    return
  }
  submittingExecutionAction.value = 'module_rerun'
  operationMessage.value = ''
  operationError.value = ''
  try {
    const task = await createModuleRerun(selectedSnapshot.value.id)
    operationMessage.value = `Jenkins 任务已创建：${task.job_name}`
    confirmDialogOpen.value = false
    pendingExecutionAction.value = null
    await loadModules()
  } catch (error) {
    operationError.value = toApiError(error).message
  } finally {
    submittingExecutionAction.value = null
  }
}

async function applyFilters() {
  const query = buildQuery(1)
  if (isSameRouteQuery(query)) {
    await refreshCurrentQuery(1)
    return
  }
  await router.replace({ path: '/modules', query })
}

async function handleFilterChanged() {
  await applyFilters()
}

async function handleEnvironmentChanged() {
  filters.module_name = []
  filters.package_name = []
  filters.module_dev = []
  filters.module_test = []
  loadedFilterOptionsEnvironmentId.value = ''
  await router.replace({ path: '/modules', query: buildQuery(1) })
}

async function resetFilters() {
  filters.module_name = []
  filters.package_name = []
  filters.module_dev = []
  filters.module_test = []
  filters.sort = 'pass_rate,-completed_at'
  perPage.value = 20
  const query = buildQuery(1)
  if (isSameRouteQuery(query)) {
    await refreshCurrentQuery(1)
    return
  }
  await router.replace({ path: '/modules', query })
}

async function changePerPage() {
  await router.replace({ path: '/modules', query: buildQuery(1) })
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || (meta.value.total_pages > 0 && nextPage > meta.value.total_pages)) {
    return
  }
  await router.replace({ path: '/modules', query: buildQuery(nextPage) })
}

function openCaseDetails(snapshot: ModuleSnapshot) {
  selectedSnapshot.value = snapshot
  caseDialogOpen.value = true
}

function openTrend(snapshot: ModuleSnapshot, days: 7 | 30) {
  selectedSnapshot.value = snapshot
  trendDays.value = days
  trendDialogOpen.value = true
}

function openJenkinsTasks(snapshot: ModuleSnapshot) {
  selectedSnapshot.value = snapshot
  operationMessage.value = ''
  operationError.value = ''
  jenkinsTasksDialogOpen.value = true
}

function handleCaseStatusUpdated(_result: CaseStatusUpdateResult) {
  void loadModules()
}

function handleRetryCreated(_task: JenkinsTask) {
  operationMessage.value = '开始执行失败重试'
  operationError.value = ''
  void loadModules()
}

function handleTaskUpdated(_task: JenkinsTask) {
  void loadModules()
}

watch(
  () => route.query,
  async () => {
    const previousEnvironmentId = filters.environment_id
    syncFiltersFromRoute()
    if (!filters.environment_id && previousEnvironmentId) {
      filters.environment_id = previousEnvironmentId
      await router.replace({ path: '/modules', query: buildQuery(1) })
      return
    }
    if (await ensureDefaultEnvironmentSelected()) {
      return
    }
    await Promise.all([loadFilterOptions(), loadModules()])
  },
  { immediate: true },
)

onMounted(loadEnvironments)
</script>

<template>
  <AppLayout>
    <section class="page-panel">
      <header class="page-heading">
        <div>
          <h1 class="serif-title">模块通过率</h1>
          <p>{{ selectedEnvironmentName }} 的模块快照只读查询。</p>
        </div>
        <RouterLink class="secondary-link" aria-label="环境通过率" to="/environments">环境汇总</RouterLink>
      </header>

      <form class="filter-bar" @submit.prevent>
        <label class="filter-field" for="module-environment-filter">
          <span>测试环境</span>
          <select
            id="module-environment-filter"
            v-model="filters.environment_id"
            :disabled="environmentLoading"
            @change="handleEnvironmentChanged"
          >
            <option v-for="environment in environments" :key="environment.id" :value="String(environment.id)">
              {{ environment.env_name }}
            </option>
          </select>
        </label>
        <label class="filter-field">
          <span>名称筛选</span>
          <el-select
            v-model="filters.module_name"
            data-testid="module-name-filter"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择模块名称"
            :loading="filterOptionsLoading"
            @change="handleFilterChanged"
          >
            <el-option
              v-for="option in filterOptions.module_names"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </label>
        <label class="filter-field">
          <span>包名筛选</span>
          <el-select
            v-model="filters.package_name"
            data-testid="package-name-filter"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择用例包名"
            :loading="filterOptionsLoading"
            @change="handleFilterChanged"
          >
            <el-option
              v-for="option in filterOptions.package_names"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </label>
        <label class="filter-field">
          <span>模块开发</span>
          <el-select
            v-model="filters.module_dev"
            data-testid="module-dev-filter"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择模块开发"
            :loading="filterOptionsLoading"
            @change="handleFilterChanged"
          >
            <el-option
              v-for="option in filterOptions.module_devs"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </label>
        <label class="filter-field">
          <span>模块测试</span>
          <el-select
            v-model="filters.module_test"
            data-testid="module-test-filter"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择模块测试"
            :loading="filterOptionsLoading"
            @change="handleFilterChanged"
          >
            <el-option
              v-for="option in filterOptions.module_tests"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </label>
        <div class="filter-actions">
          <button class="primary-button primary-button--small" type="button" @click="resetFilters">重置</button>
        </div>
      </form>

      <p v-if="errorMessage" class="status-line" role="alert">{{ errorMessage }}</p>
      <p v-if="filterOptionsError" class="status-line" role="alert">{{ filterOptionsError }}</p>
      <p v-if="operationMessage" class="status-line status-line--success">{{ operationMessage }}</p>
      <p v-if="operationError && !confirmDialogOpen" class="status-line" role="alert">{{ operationError }}</p>

      <div class="table-frame">
        <el-table v-loading="loading" :data="modules" border>
          <el-table-column label="日期" min-width="125">
            <template #default="{ row }">
              {{ formatDateTime(row.completed_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="package_name" label="用例包名" min-width="120" />
          <el-table-column prop="module_name" label="模块名称" min-width="120" />
          <el-table-column label="执行时间" min-width="80">
            <template #default="{ row }">
              {{ formatDuration(row.duration_seconds) }}
            </template>
          </el-table-column>
          <el-table-column prop="module_dev" label="模块开发" min-width="80" />
          <el-table-column prop="module_test" label="模块测试" min-width="80" />
          <el-table-column prop="total_count" label="总数" min-width="50" />
          <el-table-column prop="failed_count" label="失败" min-width="50" />
          <el-table-column prop="skipped_count" label="跳过" min-width="50" />
          <el-table-column label="通过率" min-width="90">
            <template #default="{ row }">
              <button
                class="rate-entry-button"
                type="button"
                :aria-label="`查看${row.module_name}用例详情 ${Number(row.pass_rate) * 100}%`"
                @click="openCaseDetails(row)"
              >
                <RateBadge :value="row.pass_rate" compact />
              </button>
            </template>
          </el-table-column>
          <el-table-column label="后置能力" min-width="210">
            <template #default="{ row }">
              <ReadOnlyActionButtons
                :actions="row.actions"
                :disabled-reasons="row.disabled_reasons"
                :loading-actions="actionLoadingFor(row)"
                @failed-rerun="openExecutionConfirm(row, 'failed_rerun')"
                @module-rerun="openExecutionConfirm(row, 'module_rerun')"
                @jenkins-tasks="openJenkinsTasks(row)"
                @trend="openTrend(row, $event)"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="mobile-card-list" aria-label="模块移动端列表">
        <article v-for="item in modules" :key="item.id" class="module-card">
          <header class="module-card__header">
            <div>
              <span>{{ item.package_name }}</span>
              <strong>{{ item.module_name }}</strong>
            </div>
          </header>
          <dl class="module-card__facts">
            <div>
              <dt>日期</dt>
              <dd>{{ formatDateTime(item.completed_at) }}</dd>
            </div>
            <div>
              <dt>执行时间</dt>
              <dd>{{ formatDuration(item.duration_seconds) }}</dd>
            </div>
            <div>
              <dt>模块开发</dt>
              <dd>{{ item.module_dev }}</dd>
            </div>
            <div>
              <dt>模块测试</dt>
              <dd>{{ item.module_test }}</dd>
            </div>
            <div>
              <dt>总数</dt>
              <dd>{{ item.total_count }}</dd>
            </div>
            <div>
              <dt>失败</dt>
              <dd>{{ item.failed_count }}</dd>
            </div>
            <div>
              <dt>跳过</dt>
              <dd>跳过 {{ item.skipped_count }}</dd>
            </div>
            <div>
              <dt>通过率</dt>
              <dd>
                <button
                  class="rate-entry-button"
                  type="button"
                  :aria-label="`查看${item.module_name}用例详情 ${Number(item.pass_rate) * 100}%`"
                  @click="openCaseDetails(item)"
                >
                  <RateBadge :value="item.pass_rate" compact />
                </button>
              </dd>
            </div>
          </dl>
          <ReadOnlyActionButtons
            :actions="item.actions"
            :disabled-reasons="item.disabled_reasons"
            :loading-actions="actionLoadingFor(item)"
            @failed-rerun="openExecutionConfirm(item, 'failed_rerun')"
            @module-rerun="openExecutionConfirm(item, 'module_rerun')"
            @jenkins-tasks="openJenkinsTasks(item)"
            @trend="openTrend(item, $event)"
          />
        </article>
      </div>

      <p v-if="!loading && modules.length === 0" class="empty-state">暂无模块快照</p>

      <footer class="pagination-line">
        <span>共 {{ meta.total }} 条，当前第 {{ meta.page }} 页</span>
        <div class="pagination-actions">
          <label class="per-page-field" for="module-per-page">
            <span>每页条数</span>
            <select id="module-per-page" v-model.number="perPage" @change="changePerPage">
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </label>
          <button type="button" :disabled="meta.page <= 1" @click="changePage(meta.page - 1)">上一页</button>
          <button type="button" :disabled="meta.total_pages === 0 || meta.page >= meta.total_pages" @click="changePage(meta.page + 1)">下一页</button>
        </div>
      </footer>
    </section>

    <CaseDetailsDialog
      v-model="caseDialogOpen"
      :snapshot="selectedSnapshot"
      :environment-name="selectedEnvironmentName"
      :is-admin="isAdmin"
      @status-updated="handleCaseStatusUpdated"
      @retry-created="handleRetryCreated"
    />
    <ModuleTrendDialog
      v-model="trendDialogOpen"
      :snapshot="selectedSnapshot"
      :environment-name="selectedEnvironmentName"
      :days="trendDays"
    />
    <JenkinsTasksDialog
      v-model="jenkinsTasksDialogOpen"
      :snapshot="selectedSnapshot"
      :environment-name="selectedEnvironmentName"
      @task-updated="handleTaskUpdated"
    />

    <el-dialog
      v-if="confirmDialogOpen && selectedSnapshot"
      :model-value="confirmDialogOpen"
      :title="confirmTitle"
      width="min(520px, calc(100vw - 32px))"
      destroy-on-close
      @close="closeExecutionConfirm"
      @update:model-value="confirmDialogOpen = $event"
    >
      <section class="execution-confirm" aria-label="Jenkins 执行确认">
        <p>{{ confirmDescription }}</p>
        <p v-if="operationError" class="status-line" role="alert">{{ operationError }}</p>
      </section>
      <template #footer>
        <div class="execution-confirm__footer">
          <button class="secondary-button" type="button" :disabled="submittingExecutionAction !== null" @click="closeExecutionConfirm">
            取消
          </button>
          <button class="primary-button" type="button" :disabled="submittingExecutionAction !== null" @click="confirmExecutionAction">
            {{ confirmButtonLabel }}
          </button>
        </div>
      </template>
    </el-dialog>
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

h1 {
  margin: 0 0 8px;
  font-size: 32px;
}

p {
  margin: 0;
  color: var(--color-muted);
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(180px, 1.05fr) repeat(4, minmax(150px, 1fr)) auto;
  align-items: end;
  gap: 12px;
}

.filter-field {
  display: grid;
  gap: 6px;
  min-width: 0;
  color: var(--color-body);
  font-size: 13px;
  font-weight: 700;
}

.filter-field select,
.filter-field input {
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

.filter-field :deep(.el-select) {
  width: 100%;
}

.filter-field :deep(.el-select__wrapper) {
  min-height: 40px;
  border-radius: 8px;
  background: var(--color-canvas);
  box-shadow: 0 0 0 1px var(--color-hairline) inset;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: max-content;
}

.primary-button,
.secondary-button,
.secondary-link,
.pagination-actions button {
  min-height: 40px;
  border-radius: 8px;
  font-weight: 700;
}

.primary-button {
  padding: 0 18px;
  border: 0;
  background: var(--color-primary);
  color: white;
}

.primary-button--small {
  min-height: 34px;
  padding: 0 12px;
  font-size: 13px;
}

.secondary-button {
  padding: 0 16px;
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
  text-decoration: none;
}

.table-frame {
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.rate-entry-button {
  display: block;
  width: 100%;
  min-height: 44px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.rate-entry-button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--color-primary) 45%, transparent);
  outline-offset: 3px;
}

.mobile-card-list {
  display: none;
}

.status-line {
  color: var(--color-error);
  font-weight: 700;
}

.status-line--success {
  color: var(--color-success);
}

.execution-confirm {
  display: grid;
  gap: 12px;
}

.execution-confirm__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 86px;
  border: 1px dashed var(--color-hairline);
  border-radius: 8px;
  background: var(--color-surface-soft);
  color: var(--color-muted);
  font-weight: 700;
}

.pagination-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pagination-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.pagination-actions button {
  padding: 0 12px;
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
}

.pagination-actions button:disabled {
  color: var(--color-muted);
  opacity: 0.54;
}

.per-page-field {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 700;
}

.per-page-field select {
  min-height: 40px;
  padding: 0 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

@media (max-width: 1120px) {
  .filter-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .page-panel {
    padding: 18px;
  }

  .page-heading,
  .pagination-line {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .table-frame {
    display: none;
  }

  .mobile-card-list {
    display: grid;
    gap: 12px;
  }

  .module-card {
    display: grid;
    gap: 14px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--color-hairline);
    border-radius: 8px;
    background: var(--color-canvas);
  }

  .module-card__header {
    display: grid;
    gap: 12px;
  }

  .module-card__header div {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .module-card__header span {
    overflow-wrap: anywhere;
    color: var(--color-muted);
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: 12px;
  }

  .module-card__header strong {
    overflow-wrap: anywhere;
    color: var(--color-ink);
    font-size: 18px;
  }

  .module-card__facts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 0;
  }

  .module-card__facts div {
    display: grid;
    gap: 3px;
    min-width: 0;
  }

  .module-card__facts dt {
    color: var(--color-muted);
    font-size: 12px;
    font-weight: 700;
  }

  .module-card__facts dd {
    margin: 0;
    overflow-wrap: anywhere;
    color: var(--color-body);
    font-size: 14px;
  }

  h1 {
    font-size: 28px;
  }
}
</style>
