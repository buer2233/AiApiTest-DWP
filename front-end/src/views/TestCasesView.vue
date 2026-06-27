<script setup lang="ts">
import { computed, ref } from "vue";

import AppLayout from "@/layouts/AppLayout.vue";
import TestCaseFilter from "@/components/testcases/TestCaseFilter.vue";
import TestCaseTable from "@/components/testcases/TestCaseTable.vue";
import SyncButton from "@/components/testcases/SyncButton.vue";
import { useAuthStore } from "@/stores/auth";
import { useTestCaseList } from "@/composables/useTestCases";
import type { ListParams } from "@/api/testcases";

// 用例展示容器：组合筛选、表格、分页与管理员同步。
const auth = useAuthStore();

const params = ref<ListParams>({ page: 1, page_size: 20 });
const { data, isLoading, isError, refetch } = useTestCaseList(params);

const items = computed(() => data.value?.results ?? []);
const total = computed(() => data.value?.count ?? 0);

// 模块下拉选项：从当前结果聚合（第一版简化）
const moduleOptions = computed(() => [...new Set(items.value.map((i) => i.module_key))]);

function onFilterChange(payload: { moduleKey: string; keyword: string }) {
  params.value = {
    page: 1,
    page_size: params.value.page_size,
    module_key: payload.moduleKey || undefined,
    keyword: payload.keyword || undefined,
  };
}

function onPageChange(page: number) {
  params.value = { ...params.value, page };
}

function onSizeChange(size: number) {
  params.value = { ...params.value, page: 1, page_size: size };
}
</script>

<template>
  <app-layout>
    <div class="page-head">
      <h1 class="page-title">测试用例</h1>
      <sync-button v-if="auth.isAdmin" @synced="refetch" />
    </div>

    <test-case-filter :module-options="moduleOptions" @change="onFilterChange" />

    <el-alert v-if="isError" type="error" :closable="false" show-icon class="page-error">
      <template #title>
        加载失败，请重试
        <el-button text type="primary" @click="() => refetch()">重试</el-button>
      </template>
    </el-alert>

    <test-case-table :items="items" :loading="isLoading" />

    <div class="pager">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="total"
        :current-page="params.page"
        :page-size="params.page_size"
        :page-sizes="[20, 50, 100]"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </app-layout>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-title {
  font-size: 24px;
  margin: 0;
}
.page-error {
  margin-bottom: 16px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
