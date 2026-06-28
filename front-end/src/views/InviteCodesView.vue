<script setup lang="ts">
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, shallowRef } from 'vue'

import { createInviteCode, disableInviteCode, listInviteCodes, type InviteCode } from '@/api/inviteCodes'
import { getApiErrorMessage, getApiFieldErrors, type PaginationMeta } from '@/api/http'
import StatusBadge from '@/components/common/StatusBadge.vue'

const filters = reactive({
  keyword: '',
  status: '',
})

const createForm = reactive({
  code: '',
  max_uses: 1,
  expires_at: '',
})

const rows = shallowRef<InviteCode[]>([])
const meta = shallowRef<PaginationMeta>({ total: 0, page: 1, page_size: 20, total_pages: 0 })
const loading = shallowRef(false)
const creating = shallowRef(false)
const disablingId = shallowRef<number | null>(null)
const errorMessage = shallowRef('')
const successMessage = shallowRef('')
const createFieldErrors = reactive<Record<string, string>>({})

const hasRows = computed(() => rows.value.length > 0)

async function loadInviteCodes(page = 1) {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await listInviteCodes({
      ...filters,
      page,
      page_size: meta.value.page_size,
    })
    rows.value = result.data
    meta.value = result.meta
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '邀请码列表加载失败，请重试')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  Object.keys(createFieldErrors).forEach((key) => {
    delete createFieldErrors[key]
  })
  try {
    await createInviteCode({
      code: createForm.code,
      max_uses: Number(createForm.max_uses),
      expires_at: createForm.expires_at || null,
    })
    successMessage.value = '邀请码已创建'
    createForm.code = ''
    createForm.max_uses = 1
    createForm.expires_at = ''
    await loadInviteCodes(1)
  } catch (error) {
    Object.assign(createFieldErrors, getApiFieldErrors(error))
    errorMessage.value = getApiErrorMessage(error, '邀请码创建失败，请检查字段')
  } finally {
    creating.value = false
  }
}

async function handleDisable(row: InviteCode) {
  try {
    await ElMessageBox.confirm(`确认禁用邀请码 ${row.code}？禁用后将不能继续用于注册。`, '禁用邀请码', {
      confirmButtonText: '禁用',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  disablingId.value = row.id
  successMessage.value = ''
  errorMessage.value = ''
  try {
    await disableInviteCode(row.id)
    successMessage.value = '邀请码已禁用'
    await loadInviteCodes(meta.value.page || 1)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '邀请码禁用失败，请刷新后重试')
  } finally {
    disablingId.value = null
  }
}

function handlePageChange(page: number) {
  void loadInviteCodes(page)
}

function handlePageSizeChange(pageSize: number) {
  meta.value = { ...meta.value, page_size: pageSize }
  void loadInviteCodes(1)
}

onMounted(() => {
  void loadInviteCodes()
})
</script>

<template>
  <section class="page-stack">
    <header class="page-header">
      <div>
        <p class="page-header__eyebrow">注册入口</p>
        <h1>邀请码管理</h1>
      </div>
      <el-button :icon="Refresh" @click="loadInviteCodes()">刷新</el-button>
    </header>

    <section class="surface-panel">
      <h2>创建邀请码</h2>
      <el-alert v-if="successMessage" class="section-alert" type="success" show-icon :closable="false">
        {{ successMessage }}
      </el-alert>
      <el-alert v-if="errorMessage" class="section-alert" type="error" show-icon :closable="false" role="alert">
        {{ errorMessage }}
      </el-alert>
      <el-form class="toolbar-grid" @submit.prevent="handleCreate">
        <div class="form-field">
          <label for="invite-code">邀请码</label>
          <el-input id="invite-code" v-model="createForm.code" placeholder="例如 INVITE-ADMIN" />
          <span v-if="createFieldErrors.code" class="field-error">{{ createFieldErrors.code }}</span>
        </div>
        <div class="form-field">
          <label for="invite-max-uses">最大使用次数</label>
          <el-input id="invite-max-uses" v-model="createForm.max_uses" min="1" type="number" />
          <span v-if="createFieldErrors.max_uses" class="field-error">{{ createFieldErrors.max_uses }}</span>
        </div>
        <div class="form-field">
          <label for="invite-expires-at">过期时间</label>
          <el-date-picker id="invite-expires-at" v-model="createForm.expires_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" />
          <span v-if="createFieldErrors.expires_at" class="field-error">{{ createFieldErrors.expires_at }}</span>
        </div>
        <el-button class="toolbar-grid__button" native-type="submit" type="primary" :icon="Plus" :loading="creating">
          创建邀请码
        </el-button>
      </el-form>
    </section>

    <section class="surface-panel">
      <div class="panel-heading">
        <h2>邀请码列表</h2>
        <span>共 {{ meta.total }} 条</span>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" :prefix-icon="Search" clearable placeholder="按邀请码搜索" @keyup.enter="loadInviteCodes(1)" />
        <el-select v-model="filters.status" clearable placeholder="状态">
          <el-option label="可用" value="active" />
          <el-option label="已禁用" value="disabled" />
          <el-option label="已用尽" value="exhausted" />
          <el-option label="已过期" value="expired" />
        </el-select>
        <el-button :icon="Search" @click="loadInviteCodes(1)">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" class="data-table" empty-text="暂无邀请码">
        <el-table-column prop="code" label="邀请码" min-width="160" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column prop="max_uses" label="最大次数" width="100" />
        <el-table-column prop="used_count" label="已用次数" width="100" />
        <el-table-column prop="created_by.username" label="创建人" width="120" />
        <el-table-column prop="expires_at" label="过期时间" min-width="180" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              :disabled="row.status !== 'active'"
              :loading="disablingId === row.id"
              size="small"
              type="danger"
              @click="handleDisable(row)"
            >
              禁用
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && !hasRows" class="empty-line">暂无邀请码</div>
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
