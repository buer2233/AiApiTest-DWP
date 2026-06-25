<!--
  失败用例弹窗组件。
  负责查询失败用例、筛选失败列表、选择用例重试、一键失败重试和打开 Allure 报告。
-->

<script setup lang="ts">
import { DocumentChecked, Link, Refresh, Search } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, reactive, ref, watch } from 'vue';

import {
  getFailureCases,
  getReport,
  retryAllFailed,
  retrySelectedFailures,
  type FailureCase,
} from '@/api/testRuns';

const props = defineProps<{
  /** 弹窗显示状态，配合 v-model 使用。 */
  modelValue: boolean;
  /** 当前测试任务 ID，为 null 时不加载失败用例。 */
  testRunId: number | null;
  /** 弹窗标题中的模块/报告名称。 */
  reportTitle?: string;
}>();

const emit = defineEmits<{
  /** 同步 v-model 显示状态。 */
  'update:modelValue': [value: boolean];
  /** 重试成功触发，通知父组件刷新任务列表。 */
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
  /**
   * 将父组件 v-model 转换为 Element Plus Dialog 需要的可写 computed。
   * setter 通过 update:modelValue 把关闭动作同步回父组件。
   */
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const filteredFailures = computed(() => {
  /** 根据已提交筛选条件派生失败用例列表。 */
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
  /** 根据当前 testRunId 加载失败用例。 */
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
  /** 提交筛选条件，避免输入框每次输入都重新过滤。 */
  activeFilters.keyword = draftFilters.keyword;
  activeFilters.errorType = draftFilters.errorType;
  activeFilters.status = draftFilters.status;
}

async function retrySelected() {
  /** 对勾选的失败用例发起重试。 */
  if (!props.testRunId || selectedIds.value.length === 0) {
    return;
  }
  try {
    await retrySelectedFailures(props.testRunId, {
      failure_ids: selectedIds.value,
      retry_count: 0,
    });
    ElMessage.success('失败用例重试已提交');
    emit('retried');
  } catch {
    ElMessage.error('失败用例重试提交失败，请稍后重试');
  }
}

async function retryAll() {
  /** 对当前测试任务下所有失败用例发起重试。 */
  if (!props.testRunId) {
    return;
  }
  try {
    await retryAllFailed(props.testRunId, { retry_count: 0 });
    ElMessage.success('一键失败重试已提交');
    emit('retried');
  } catch {
    ElMessage.error('一键失败重试提交失败，请稍后重试');
  }
}

async function openReport() {
  /** 打开当前测试任务的 Allure 报告入口。 */
  if (!props.testRunId) {
    return;
  }
  const report = await getReport(props.testRunId);
  window.open(report.report_url, '_blank', 'noopener');
}

function toggleSelection(id: number, checked: boolean) {
  /** 切换失败用例选择状态。 */
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
      // 每次打开弹窗都重置选择并重新加载，避免沿用上一个任务的选择状态。
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
