<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchModuleSnapshots, fetchTestEnvironments } from '@/api/metrics'
import AppLayout from '@/components/layout/AppLayout.vue'
import RateBadge from '@/components/metrics/RateBadge.vue'
import ReadOnlyActionButtons from '@/components/metrics/ReadOnlyActionButtons.vue'
import type { PaginationMeta } from '@/types/api'
import type { ModuleSnapshot, TestEnvironment } from '@/types/metrics'

const route = useRoute()
const router = useRouter()

const environments = shallowRef<TestEnvironment[]>([])
const modules = shallowRef<ModuleSnapshot[]>([])
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, per_page: 20, total_pages: 0 })
const loading = shallowRef(false)
const environmentLoading = shallowRef(false)
const errorMessage = shallowRef('')

const filters = reactive({
  environment_id: '',
  module_name: '',
  package_name: '',
  module_test: '',
  pass_rate_lte: '',
  sort: 'pass_rate,-completed_at',
})

const currentPage = shallowRef(1)
const perPage = shallowRef(20)

const selectedEnvironmentName = computed(() => {
  return environments.value.find((environment) => String(environment.id) === filters.environment_id)?.env_name ?? '当前环境'
})

function getQueryValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value[0] ? String(value[0]) : ''
  }
  return value ? String(value) : ''
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
  filters.module_name = getQueryValue(route.query.module_name)
  filters.package_name = getQueryValue(route.query.package_name)
  filters.module_test = getQueryValue(route.query.module_test)
  filters.pass_rate_lte = getQueryValue(route.query.pass_rate_lte)
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
  for (const key of ['module_name', 'package_name', 'module_test', 'pass_rate_lte', 'sort'] as const) {
    if (filters[key]) {
      query[key] = filters[key]
    }
  }
  if (nextPage > 1) {
    query.page = String(nextPage)
  }
  if (perPage.value !== 20) {
    query.per_page = String(perPage.value)
  }
  return query
}

async function loadEnvironments() {
  environmentLoading.value = true
  try {
    environments.value = await fetchTestEnvironments({ is_active: true })
    if (!filters.environment_id && environments.value[0]) {
      filters.environment_id = String(environments.value[0].id)
      await router.replace({ path: '/modules', query: buildQuery(currentPage.value) })
    }
  } finally {
    environmentLoading.value = false
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
      module_name: filters.module_name || undefined,
      package_name: filters.package_name || undefined,
      module_test: filters.module_test || undefined,
      pass_rate_lte: filters.pass_rate_lte || undefined,
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

async function applyFilters() {
  await router.replace({ path: '/modules', query: buildQuery(1) })
}

async function resetFilters() {
  filters.module_name = ''
  filters.package_name = ''
  filters.module_test = ''
  filters.pass_rate_lte = ''
  filters.sort = 'pass_rate,-completed_at'
  perPage.value = 20
  await router.replace({ path: '/modules', query: buildQuery(1) })
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

watch(
  () => route.query,
  async () => {
    syncFiltersFromRoute()
    await loadModules()
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
          <p>{{ selectedEnvironmentName }} 的模块快照只读查询，筛选与分页状态会同步到地址栏。</p>
        </div>
        <RouterLink class="secondary-link" aria-label="环境通过率" to="/environments">环境汇总</RouterLink>
      </header>

      <form class="filter-bar" @submit.prevent="applyFilters">
        <label class="filter-field" for="module-environment-filter">
          <span>测试环境</span>
          <select id="module-environment-filter" v-model="filters.environment_id" :disabled="environmentLoading">
            <option v-for="environment in environments" :key="environment.id" :value="String(environment.id)">
              {{ environment.env_name }}
            </option>
          </select>
        </label>
        <label class="filter-field" for="module-name-filter">
          <span>名称筛选</span>
          <input id="module-name-filter" v-model.trim="filters.module_name" aria-label="模块名称" type="search" />
        </label>
        <label class="filter-field" for="package-name-filter">
          <span>包名筛选</span>
          <input id="package-name-filter" v-model.trim="filters.package_name" aria-label="用例包名" type="search" />
        </label>
        <label class="filter-field" for="module-test-filter">
          <span>测试人筛选</span>
          <input id="module-test-filter" v-model.trim="filters.module_test" aria-label="模块测试" type="search" />
        </label>
        <label class="filter-field filter-field--small" for="pass-rate-lte-filter">
          <span>上限筛选</span>
          <input id="pass-rate-lte-filter" v-model.trim="filters.pass_rate_lte" aria-label="通过率上限" inputmode="decimal" />
        </label>
        <button class="primary-button" type="submit">查询</button>
        <button class="secondary-button" type="button" @click="resetFilters">重置</button>
      </form>

      <p v-if="errorMessage" class="status-line" role="alert">{{ errorMessage }}</p>

      <div class="table-frame">
        <el-table v-loading="loading" :data="modules" border>
          <el-table-column label="日期" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.completed_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="package_name" label="用例包名" min-width="160" />
          <el-table-column prop="module_name" label="模块名称" min-width="160" />
          <el-table-column label="通过率" min-width="150">
            <template #default="{ row }">
              <RateBadge :value="row.pass_rate" compact />
            </template>
          </el-table-column>
          <el-table-column label="执行时间" min-width="110">
            <template #default="{ row }">
              {{ formatDuration(row.duration_seconds) }}
            </template>
          </el-table-column>
          <el-table-column prop="module_dev" label="模块开发" min-width="120" />
          <el-table-column prop="module_test" label="模块测试" min-width="120" />
          <el-table-column prop="total_count" label="总数" min-width="90" />
          <el-table-column prop="failed_count" label="失败" min-width="90" />
          <el-table-column prop="skipped_count" label="跳过" min-width="90" />
          <el-table-column label="后置能力" min-width="280">
            <template #default="{ row }">
              <ReadOnlyActionButtons :actions="row.actions" />
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
            <RateBadge :value="item.pass_rate" compact />
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
          </dl>
          <ReadOnlyActionButtons :actions="item.actions" />
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
  grid-template-columns: minmax(180px, 1.1fr) repeat(3, minmax(150px, 1fr)) minmax(120px, 0.7fr) auto;
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

.filter-field--small {
  max-width: 140px;
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

.mobile-card-list {
  display: none;
}

.status-line {
  color: var(--color-error);
  font-weight: 700;
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

  .filter-field--small {
    max-width: none;
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
