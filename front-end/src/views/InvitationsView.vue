<script setup lang="ts">
import { Copy } from '@lucide/vue'
import { onMounted, reactive, shallowRef } from 'vue'

import { createInvitation, fetchInvitations, revokeInvitation } from '@/api/platform'
import AppLayout from '@/components/layout/AppLayout.vue'
import type { InvitationCreateResponse } from '@/api/platform'
import type { InvitationSummary, PaginationMeta, UserRole } from '@/types/api'

const invitations = shallowRef<InvitationSummary[]>([])
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, per_page: 20, total_pages: 0 })
const loading = shallowRef(false)
const dialogOpen = shallowRef(false)
const creating = shallowRef(false)
const revokingId = shallowRef<number | null>(null)
const plainCode = shallowRef('')
const createdInvitation = shallowRef<InvitationCreateResponse | null>(null)
const statusFilter = shallowRef('')
const roleFilter = shallowRef<UserRole | ''>('')
const page = shallowRef(1)

const createForm = reactive({
  role: 'member' as 'admin' | 'member',
  expires_at: '',
})

const statusText: Record<InvitationSummary['status'], string> = {
  unused: '可使用',
  used: '已使用',
  revoked: '已作废',
  expired: '已过期',
}

async function loadInvitations() {
  loading.value = true
  try {
    const response = await fetchInvitations({
      status: statusFilter.value || undefined,
      role: roleFilter.value || undefined,
      page: page.value,
      per_page: 20,
    })
    invitations.value = response.data
    meta.value = response.meta
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  plainCode.value = ''
  createdInvitation.value = null
  createForm.role = 'member'
  createForm.expires_at = ''
  dialogOpen.value = true
}

function closeCreateDialog() {
  dialogOpen.value = false
  // 邀请码明文只允许本次展示，关闭弹窗后立即从前端状态移除。
  plainCode.value = ''
  createdInvitation.value = null
}

async function submitCreateInvitation() {
  creating.value = true
  plainCode.value = ''
  createdInvitation.value = null
  try {
    const response = await createInvitation({
      role: createForm.role,
      expires_at: createForm.expires_at || undefined,
    })
    plainCode.value = response.plain_code
    createdInvitation.value = response
  } finally {
    creating.value = false
  }
}

async function submitRevokeInvitation(invitationId: number) {
  revokingId.value = invitationId
  try {
    const revokedInvitation = await revokeInvitation(invitationId)
    invitations.value = invitations.value.map((item) => (item.id === invitationId ? revokedInvitation : item))
  } finally {
    revokingId.value = null
  }
}

async function applyFilters() {
  page.value = 1
  await loadInvitations()
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || (meta.value.total_pages > 0 && nextPage > meta.value.total_pages)) {
    return
  }
  page.value = nextPage
  await loadInvitations()
}

onMounted(loadInvitations)
</script>

<template>
  <AppLayout>
    <section class="page-panel">
      <header class="page-heading">
        <div>
          <h1 class="serif-title">邀请码</h1>
          <p>邀请码明文只在创建成功后展示一次，列表不展示历史明文。</p>
        </div>
        <button class="primary-button" type="button" @click="openCreateDialog">生成邀请码</button>
      </header>

      <div class="filter-bar">
        <label class="filter-field" for="invitation-status-filter">
          <span>状态筛选</span>
          <select id="invitation-status-filter" v-model="statusFilter" aria-label="状态筛选" @change="applyFilters">
            <option value="">全部状态</option>
            <option value="unused">可使用</option>
            <option value="used">已使用</option>
            <option value="revoked">已作废</option>
            <option value="expired">已过期</option>
          </select>
        </label>
        <label class="filter-field" for="invitation-role-filter">
          <span>目标角色筛选</span>
          <select id="invitation-role-filter" v-model="roleFilter" aria-label="目标角色筛选" @change="applyFilters">
            <option value="">全部角色</option>
            <option value="admin">管理人员</option>
            <option value="member">普通成员</option>
          </select>
        </label>
      </div>

      <el-table v-loading="loading" :data="invitations" border>
        <el-table-column label="状态" min-width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'unused' ? 'success' : row.status === 'expired' ? 'warning' : 'info'">
              {{ statusText[row.status as InvitationSummary['status']] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="目标角色" min-width="120" />
        <el-table-column prop="created_by" label="创建人" min-width="140" />
        <el-table-column prop="used_by" label="使用人" min-width="140" />
        <el-table-column prop="expires_at" label="过期时间" min-width="190" />
        <el-table-column label="操作" min-width="140">
          <template #default="{ row }">
            <button
              v-if="row.status === 'unused'"
              class="danger-button"
              type="button"
              :aria-label="`作废邀请码 ${row.id}`"
              :disabled="revokingId === row.id"
              @click="submitRevokeInvitation(row.id)"
            >
              {{ revokingId === row.id ? '作废中...' : '作废' }}
            </button>
            <span v-else class="muted-action">不可作废</span>
          </template>
        </el-table-column>
      </el-table>
      <footer class="pagination-line">
        <span>共 {{ meta.total }} 条，当前第 {{ meta.page }} 页</span>
        <div class="pagination-actions">
          <button type="button" :disabled="meta.page <= 1" @click="changePage(meta.page - 1)">上一页</button>
          <button type="button" :disabled="meta.total_pages === 0 || meta.page >= meta.total_pages" @click="changePage(meta.page + 1)">下一页</button>
        </div>
      </footer>
    </section>

    <div v-if="dialogOpen" class="dialog-mask" role="dialog" aria-modal="true" aria-label="生成邀请码">
      <section class="dialog-card">
        <h2>生成邀请码</h2>
        <p>可选择授权角色；不填写过期时间时默认 7 天后过期。</p>
        <label class="filter-field" for="create-invitation-role">
          <span>目标角色</span>
          <select id="create-invitation-role" v-model="createForm.role" aria-label="目标角色">
            <option value="member">普通成员</option>
            <option value="admin">管理人员</option>
          </select>
        </label>
        <label class="filter-field" for="create-invitation-expires">
          <span>过期时间</span>
          <input id="create-invitation-expires" v-model="createForm.expires_at" aria-label="过期时间" type="datetime-local" />
        </label>
        <button class="primary-button" type="button" :disabled="creating" @click="submitCreateInvitation">
          {{ creating ? '创建中...' : '创建邀请码' }}
        </button>
        <div v-if="plainCode" class="plain-code-box" role="status">
          <span>仅本次展示</span>
          <span v-if="createdInvitation">目标角色：{{ createdInvitation.role }}</span>
          <span v-if="createdInvitation">过期时间：{{ createForm.expires_at || createdInvitation.expires_at }}</span>
          <code>{{ plainCode }}</code>
          <button type="button"><Copy :size="16" aria-hidden="true" />复制</button>
        </div>
        <button class="ghost-button" type="button" @click="closeCreateDialog">关闭</button>
      </section>
    </div>
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
  align-items: center;
  justify-content: space-between;
  gap: 18px;
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

.filter-field select,
.filter-field input {
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

.primary-button,
.ghost-button,
.danger-button {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  font-weight: 700;
}

.primary-button {
  border: 0;
  background: var(--color-primary);
  color: #fff;
}

.ghost-button {
  border: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  color: var(--color-body);
}

.danger-button {
  border: 1px solid rgba(198, 69, 69, 0.24);
  background: rgba(198, 69, 69, 0.08);
  color: var(--color-error);
}

.danger-button:disabled {
  color: var(--color-muted);
}

.muted-action {
  color: var(--color-muted);
  font-size: 13px;
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

.dialog-mask {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(20, 20, 19, 0.48);
  z-index: 20;
}

.dialog-card {
  display: grid;
  gap: 16px;
  width: min(520px, 100%);
  padding: 28px;
  border-radius: 12px;
  background: var(--color-canvas);
}

.dialog-card h2 {
  margin: 0;
}

.plain-code-box {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(93, 184, 114, 0.28);
  border-radius: 8px;
  background: rgba(93, 184, 114, 0.1);
}

.plain-code-box code {
  color: #2d7c43;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-weight: 700;
}

.plain-code-box button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  min-height: 36px;
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  background: var(--color-canvas);
}
</style>
