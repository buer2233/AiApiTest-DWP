<script setup lang="ts">
import { DocumentChecked, Link, Refresh, Search } from '@element-plus/icons-vue';
import { computed, reactive, ref, watch } from 'vue';

import {
  getFailureCases,
  getReport,
  retryAllFailed,
  retrySelectedFailures,
  type FailureCase,
} from '@/api/testRuns';

const props = defineProps<{
  modelValue: boolean;
  testRunId: number | null;
  reportTitle?: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  retried: [];
}>();

const loading = ref(false);
const failures = ref<FailureCase[]>([]);
const selectedIds = ref<number[]>([]);
const activeFilters = reactive({
  keyword: '',
  errorType: '',
  status: '',
});
const draftFilters = reactive({
  keyword: '',
  errorType: '',
  status: '',
});

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const filteredFailures = computed(() => {
  const keyword = activeFilters.keyword.trim().toLowerCase();
  const errorType = activeFilters.errorType.trim().toLowerCase();
  return failures.value.filter((failure) => {
    const matchesKeyword =
      !keyword ||
      failure.case_name.toLowerCase().includes(keyword) ||
      failure.description.toLowerCase().includes(keyword);
    const matchesError = !errorType || failure.error_type.toLowerCase().includes(errorType);
    const matchesStatus = !activeFilters.status || failure.status === activeFilters.status;
    return matchesKeyword && matchesError && matchesStatus;
  });
});

async function loadFailures() {
  if (!props.testRunId) {
    failures.value = [];
    return;
  }
  loading.value = true;
  try {
    const response = await getFailureCases(props.testRunId);
    failures.value = response.results;
  } finally {
    loading.value = false;
  }
}

function queryFailures() {
  activeFilters.keyword = draftFilters.keyword;
  activeFilters.errorType = draftFilters.errorType;
  activeFilters.status = draftFilters.status;
}

async function retrySelected() {
  if (!props.testRunId || selectedIds.value.length === 0) {
    return;
  }
  await retrySelectedFailures(props.testRunId, {
    failure_ids: selectedIds.value,
    retry_count: 0,
  });
  emit('retried');
}

async function retryAll() {
  if (!props.testRunId) {
    return;
  }
  await retryAllFailed(props.testRunId, { retry_count: 0 });
  emit('retried');
}

async function openReport() {
  if (!props.testRunId) {
    return;
  }
  const report = await getReport(props.testRunId);
  window.open(report.report_url, '_blank', 'noopener');
}

function toggleSelection(id: number, checked: boolean) {
  if (checked && !selectedIds.value.includes(id)) {
    selectedIds.value = [...selectedIds.value, id];
  }
  if (!checked) {
    selectedIds.value = selectedIds.value.filter((selectedId) => selectedId !== id);
  }
}

watch(
  () => [props.modelValue, props.testRunId] as const,
  ([isVisible]) => {
    if (isVisible) {
      selectedIds.value = [];
      void loadFailures();
    }
  },
  { immediate: true },
);
</script>

<template>
  <el-dialog v-model="visible" class="failure-dialog" width="86%" :title="`失败用例 - ${reportTitle || ''}`">
    <section class="failure-dialog-toolbar">
      <el-input
        v-model="draftFilters.keyword"
        data-test="failure-keyword"
        placeholder="用例名 / 描述"
        :prefix-icon="Search"
      />
      <el-input v-model="draftFilters.errorType" data-test="failure-error-type" placeholder="错误类型" />
      <el-select v-model="draftFilters.status" placeholder="执行状态">
        <el-option label="全部" value="" />
        <el-option label="失败" value="failed" />
        <el-option label="中断" value="broken" />
        <el-option label="跳过" value="skipped" />
      </el-select>
      <el-button data-test="query-failures" plain @click="queryFailures">查询</el-button>
      <el-button data-test="open-report" :icon="Link" plain @click="openReport">Allure 报告</el-button>
      <el-button data-test="retry-selected" :icon="Refresh" type="primary" @click="retrySelected">
        失败重试
      </el-button>
      <el-button data-test="retry-all-failed" :icon="DocumentChecked" plain @click="retryAll">
        一键失败重试
      </el-button>
    </section>

    <el-table :data="filteredFailures" :loading="loading" class="failure-table" row-key="id">
      <el-table-column width="52">
        <template #default="{ row }">
          <el-checkbox
            :data-test="`select-failure-${row.id}`"
            :model-value="selectedIds.includes(row.id)"
            @update:model-value="(value: boolean) => toggleSelection(row.id, Boolean(value))"
          />
        </template>
      </el-table-column>
      <el-table-column label="用例名" prop="case_name" min-width="180" />
      <el-table-column label="用例描述" prop="description" min-width="220" show-overflow-tooltip />
      <el-table-column label="错误类型" prop="error_type" min-width="150" />
      <el-table-column label="断言" prop="assertion_message" min-width="220" show-overflow-tooltip />
      <el-table-column label="执行状态" prop="status" min-width="110" />
      <el-table-column label="错误信息" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ row.node_id }}</template>
      </el-table-column>
      <el-table-column label="确认结果" prop="retry_status" min-width="120" />
    </el-table>
  </el-dialog>
</template>
