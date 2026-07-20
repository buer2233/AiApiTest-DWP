<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, shallowRef } from 'vue'

import EnvironmentCatalogSyncDialog from './EnvironmentCatalogSyncDialog.vue'
import EnvironmentCatalogTable from './EnvironmentCatalogTable.vue'
import EnvironmentEditorDialog from './EnvironmentEditorDialog.vue'
import { useEnvironmentCatalog } from '@/composables/useEnvironmentCatalog'
import type {
  CreateTestEnvironmentPayload,
  EnvironmentCatalogEnvironment,
  UpdateTestEnvironmentPayload,
} from '@/types/environment-catalog'

const {
  environments,
  catalogState,
  currentAttempt,
  loading,
  submitting,
  errorMessage,
  attemptErrorMessage,
  loadCatalog,
  refreshCurrentAttempt,
  createEnvironment,
  editEnvironment,
  deactivateEnvironment,
  restoreEnvironment,
  importFromYaml,
  retryAttempt,
} = useEnvironmentCatalog()

const searchTerm = shallowRef('')
const activeFilter = shallowRef<'all' | 'active' | 'inactive'>('all')
const editorVisible = shallowRef(false)
const syncVisible = shallowRef(false)
const editingEnvironment = shallowRef<EnvironmentCatalogEnvironment | null>(null)

const filteredEnvironments = computed(() => {
  const term = searchTerm.value.trim().toLocaleLowerCase()
  return environments.value.filter((environment) => {
    const matchesTerm = !term || [environment.env_key, environment.env_name, environment.url_name].some((value) => {
      return value.toLocaleLowerCase().includes(term)
    })
    const matchesActive = activeFilter.value === 'all'
      || (activeFilter.value === 'active' && environment.is_active)
      || (activeFilter.value === 'inactive' && !environment.is_active)
    return matchesTerm && matchesActive
  })
})

function openCreate() {
  editingEnvironment.value = null
  editorVisible.value = true
}

function openEdit(environment: EnvironmentCatalogEnvironment) {
  editingEnvironment.value = environment
  editorVisible.value = true
}

async function submitEnvironment(payload: CreateTestEnvironmentPayload | UpdateTestEnvironmentPayload) {
  try {
    if (editingEnvironment.value) {
      await editEnvironment(editingEnvironment.value.id, payload)
    } else {
      await createEnvironment(payload as CreateTestEnvironmentPayload)
    }
    editorVisible.value = false
    syncVisible.value = true
    ElMessage.success('环境已保存，已进入队列。')
  } catch {
    // composable 会保留可展示的 API 错误和用户已输入的表单值。
  }
}

async function toggleEnvironment(environment: EnvironmentCatalogEnvironment) {
  try {
    if (environment.is_active) {
      await ElMessageBox.confirm(
        `停用“${environment.url_name || environment.env_name}”后，成员将不能选择该环境。`,
        '确认停用环境',
        { confirmButtonText: '停用环境', cancelButtonText: '取消', type: 'warning' },
      )
      await deactivateEnvironment(environment.id)
      ElMessage.success('环境已停用，已进入队列。')
    } else {
      await restoreEnvironment(environment.id)
      ElMessage.success('环境已恢复，已进入队列。')
    }
    syncVisible.value = true
  } catch {
    // 取消确认框和 API 失败均不改变当前目录数据。
  }
}

async function importYaml() {
  try {
    await importFromYaml()
    syncVisible.value = true
    ElMessage.success('YAML 导入已进入队列。')
  } catch {
    // composable 负责记录错误，弹窗保持打开以便管理员恢复操作。
  }
}

async function retrySync() {
  try {
    await retryAttempt()
    ElMessage.success('同步重试已进入队列。')
  } catch {
    // 保留同步失败详情和重试按钮。
  }
}

onMounted(loadCatalog)
</script>

<template>
  <section class="catalog-section" aria-labelledby="environment-catalog-title">
    <header class="catalog-heading">
      <div>
        <h2 id="environment-catalog-title" class="serif-title">环境目录</h2>
        <p>目录变更会异步写回 YAML；同步状态与恢复操作在此集中处理。</p>
      </div>
      <div class="catalog-actions">
        <button class="secondary-button" type="button" :disabled="submitting" @click="syncVisible = true">同步测试环境数据</button>
        <button class="primary-button" type="button" :disabled="submitting" @click="openCreate">新建环境</button>
      </div>
    </header>

    <div class="filter-bar">
      <label class="search-field" for="catalog-search">
        <span class="sr-only">按名称或 key 搜索</span>
        <input id="catalog-search" v-model="searchTerm" placeholder="按名称或 key 搜索" autocomplete="off" />
      </label>
      <label class="status-filter" for="catalog-status">
        <span>环境状态</span>
        <select id="catalog-status" v-model="activeFilter">
          <option value="all">全部</option>
          <option value="active">启用</option>
          <option value="inactive">已停用</option>
        </select>
      </label>
      <button class="text-button" type="button" :disabled="loading" @click="loadCatalog">刷新目录</button>
    </div>

    <p v-if="errorMessage" class="catalog-error" role="alert">{{ errorMessage }}</p>
    <EnvironmentCatalogTable
      :environments="filteredEnvironments"
      :catalog-state="catalogState"
      :loading="loading"
      @edit="openEdit"
      @toggle-active="toggleEnvironment"
      @show-sync="syncVisible = true"
    />

    <EnvironmentEditorDialog
      v-model:visible="editorVisible"
      :environment="editingEnvironment"
      :submitting="submitting"
      :error-message="errorMessage"
      @submit="submitEnvironment"
    />
    <EnvironmentCatalogSyncDialog
      v-model:visible="syncVisible"
      :catalog-state="catalogState"
      :attempt="currentAttempt"
      :submitting="submitting"
      :error-message="attemptErrorMessage"
      @import-yaml="importYaml"
      @retry="retrySync"
      @refresh="refreshCurrentAttempt"
    />
  </section>
</template>

<style scoped>
.catalog-section {
  display: grid;
  gap: 16px;
  min-width: 0;
  padding-top: 10px;
}

.catalog-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.catalog-heading h2 {
  margin: 0;
  color: var(--color-ink);
  font-size: 26px;
}

.catalog-heading p {
  margin: 5px 0 0;
  color: var(--color-muted);
  font-size: 14px;
}

.catalog-actions,
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.primary-button,
.secondary-button,
.text-button {
  min-height: 40px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
}

.primary-button,
.secondary-button {
  padding: 0 16px;
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

.text-button {
  padding: 0 6px;
  border: 0;
  background: transparent;
  color: var(--color-body);
  text-decoration: underline;
}

.primary-button:disabled,
.secondary-button:disabled,
.text-button:disabled {
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.primary-button:disabled {
  background: var(--color-disabled-bg);
}

.filter-bar {
  justify-content: flex-end;
}

.search-field input,
.status-filter select {
  min-height: 38px;
  border: 1px solid var(--color-hairline);
  border-radius: 6px;
  background: var(--color-canvas);
  color: var(--color-ink);
  font: inherit;
}

.search-field input {
  width: min(250px, 100%);
  padding: 0 11px;
}

.status-filter {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 700;
}

.status-filter select {
  padding: 0 9px;
}

.catalog-error {
  margin: 0;
  color: var(--color-error);
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 768px) {
  .catalog-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-bar {
    justify-content: flex-start;
  }
}

@media (max-width: 480px) {
  .catalog-actions,
  .filter-bar {
    display: grid;
    grid-template-columns: 1fr;
  }

  .search-field input,
  .status-filter select {
    width: 100%;
  }

  .status-filter {
    display: grid;
  }
}
</style>
