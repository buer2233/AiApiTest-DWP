<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'

import { fetchUsers } from '@/api/platform'
import AppLayout from '@/components/layout/AppLayout.vue'
import type { PaginationMeta, UserRole, UserSummary } from '@/types/api'

const users = shallowRef<UserSummary[]>([])
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, per_page: 20, total_pages: 0 })
const loading = shallowRef(false)
const roleFilter = shallowRef<UserRole | ''>('')
const page = shallowRef(1)

async function loadUsers() {
  loading.value = true
  try {
    const response = await fetchUsers({
      role: roleFilter.value || undefined,
      page: page.value,
      per_page: 20,
    })
    users.value = response.data
    meta.value = response.meta
  } finally {
    loading.value = false
  }
}

async function applyRoleFilter() {
  page.value = 1
  await loadUsers()
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || (meta.value.total_pages > 0 && nextPage > meta.value.total_pages)) {
    return
  }
  page.value = nextPage
  await loadUsers()
}

onMounted(loadUsers)
</script>

<template>
  <AppLayout>
    <section class="page-panel">
      <header class="page-heading">
        <div>
          <h1 class="serif-title">用户与权限</h1>
          <p>管理人员可查看平台用户和角色范围。</p>
        </div>
      </header>

      <div class="filter-bar">
        <label class="filter-field" for="user-role-filter">
          <span>角色筛选</span>
          <select id="user-role-filter" v-model="roleFilter" aria-label="角色筛选" @change="applyRoleFilter">
            <option value="">全部角色</option>
            <option value="admin">管理人员</option>
            <option value="member">普通成员</option>
          </select>
        </label>
      </div>

      <el-table v-loading="loading" :data="users" border>
        <el-table-column prop="username" label="账号" min-width="160" />
        <el-table-column prop="display_name" label="展示名" min-width="160" />
        <el-table-column label="角色" min-width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role === 'admin' ? '管理人员' : '普通成员' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录时间" min-width="180" />
      </el-table>
      <footer class="pagination-line">
        <span>共 {{ meta.total }} 条，当前第 {{ meta.page }} 页</span>
        <div class="pagination-actions">
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
  padding: 24px;
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  background: rgba(250, 249, 245, 0.86);
}

.page-heading {
  display: flex;
  justify-content: space-between;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-field {
  display: grid;
  gap: 6px;
  min-width: 180px;
  color: var(--color-body);
  font-size: 13px;
  font-weight: 600;
}

.filter-field select {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-ink);
}

h1 {
  margin: 0 0 8px;
  font-size: 32px;
}

p,
.pagination-line {
  margin: 0;
  color: var(--color-muted);
}

.pagination-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pagination-actions {
  display: flex;
  gap: 8px;
}

.pagination-actions button {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
  color: var(--color-body);
}

.pagination-actions button:disabled {
  color: var(--color-muted);
  opacity: 0.54;
}
</style>
