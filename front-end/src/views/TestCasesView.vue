<script setup lang="ts">
import { Refresh, Search, Upload } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, shallowRef } from 'vue'

import { getApiErrorMessage, type PaginationMeta } from '@/api/http'
import { listTestCases, syncTestCases, type TestCaseItem } from '@/api/testCases'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const filters = reactive({
  keyword: '',
  package_name: '',
  module_name: '',
})

const rows = shallowRef<TestCaseItem[]>([])
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, page_size: 20, total_pages: 0 })
const loading = shallowRef(false)
const syncing = shallowRef(false)
const errorMessage = shallowRef('')
const syncMessage = shallowRef('')

const hasRows = computed(() => rows.value.length > 0)
const emptyText = computed(() => (filters.keyword || filters.package_name || filters.module_name ? '没有匹配的测试用例' : '暂无测试用例'))

async function loadTestCases(page = 1) {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await listTestCases({
      ...filters,
      page,
      page_size: meta.value.page_size,
    })
    rows.value = result.data
    meta.value = result.meta
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '测试用例加载失败，请重试')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  void loadTestCases(page)
}

function handlePageSizeChange(pageSize: number) {
  meta.value = { ...meta.value, page_size: pageSize }
  void loadTestCases(1)
}

async function handleSync() {
  syncing.value = true
  syncMessage.value = ''
  errorMessage.value = ''
  try {
    const result = await syncTestCases()
    syncMessage.value = `同步完成：新增 ${result.created}，更新 ${result.updated}，总数 ${result.total}`
    await loadTestCases(1)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '同步失败，请稍后重试')
  } finally {
    syncing.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.package_name = ''
  filters.module_name = ''
  void loadTestCases(1)
}

onMounted(() => {
  void loadTestCases()
})
</script>

<template>
  <section class="page-stack">
    <header class="page-header">
      <div>
        <p class="page-header__eyebrow">测试资产</p>
        <h1>测试用例展示</h1>
      </div>
      <div class="page-header__actions">
        <el-button :icon="Refresh" @click="loadTestCases()">刷新</el-button>
        <el-button v-if="auth.isAdmin" :icon="Upload" type="primary" :loading="syncing" @click="handleSync">同步用例</el-button>
      </div>
    </header>

    <section class="surface-panel">
      <div class="panel-heading">
        <h2>筛选</h2>
        <span>共 {{ meta.total }} 条</span>
      </div>
      <el-alert v-if="syncMessage" class="section-alert" type="success" show-icon :closable="false">
        {{ syncMessage }}
      </el-alert>
      <el-alert v-if="errorMessage" class="section-alert" type="error" show-icon :closable="false" role="alert">
        {{ errorMessage }}
      </el-alert>
      <div class="filter-row filter-row--wide">
        <el-input v-model="filters.keyword" :prefix-icon="Search" clearable placeholder="搜索 node id、函数名、标题或描述" @keyup.enter="loadTestCases(1)" />
        <el-input v-model="filters.package_name" clearable placeholder="包名" @keyup.enter="loadTestCases(1)" />
        <el-input v-model="filters.module_name" clearable placeholder="模块" @keyup.enter="loadTestCases(1)" />
        <el-button :icon="Search" type="primary" @click="loadTestCases(1)">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section class="surface-panel surface-panel--table">
      <el-table v-loading="loading" :data="rows" class="data-table" :empty-text="emptyText">
        <el-table-column prop="function_name" label="函数名" min-width="180" fixed="left" />
        <el-table-column prop="module_name" label="模块" min-width="140" />
        <el-table-column prop="package_name" label="包名" min-width="160" />
        <el-table-column prop="class_name" label="类名" min-width="150" />
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="description" label="描述" min-width="220" />
        <el-table-column prop="node_id" label="Node ID" min-width="360" show-overflow-tooltip />
        <el-table-column prop="file_path" label="文件路径" min-width="320" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StatusBadge :status="row.sync_status" />
          </template>
        </el-table-column>
        <el-table-column prop="last_synced_at" label="更新时间" min-width="190" />
      </el-table>
      <div v-if="!loading && !hasRows" class="empty-line">{{ emptyText }}</div>
      <div class="pagination-row">
        <el-pagination
          :current-page="meta.page"
          :page-size="meta.page_size"
          :page-sizes="[10, 20, 50]"
          :total="meta.total"
          layout="total, sizes, prev, pager, next"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>
  </section>
</template>
