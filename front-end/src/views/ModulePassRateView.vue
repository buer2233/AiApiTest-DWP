<script setup lang="ts">
import { Link, Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, reactive, ref } from 'vue';

import {
  getReport,
  listTestRuns,
  retryModule,
  type TestRun,
} from '@/api/testRuns';
import FailureCasesDialog from '@/components/FailureCasesDialog.vue';
import ModuleRunTable from '@/components/ModuleRunTable.vue';
import RunFilters from '@/components/RunFilters.vue';

const loading = ref(false);
const runs = ref<TestRun[]>([]);
const selectedRun = ref<TestRun | null>(null);
const failureDialogVisible = ref(false);
const activeFilters = reactive({
  keyword: '',
  status: '',
  source: '',
});

const filteredRuns = computed(() => {
  const keyword = activeFilters.keyword.trim().toLowerCase();
  return runs.value.filter((run) => {
    const name = getModuleName(run).toLowerCase();
    const matchesKeyword = !keyword || name.includes(keyword) || run.case_path.toLowerCase().includes(keyword);
    const matchesStatus = !activeFilters.status || run.status === activeFilters.status;
    const matchesSource = !activeFilters.source || run.trigger_source === activeFilters.source;
    return matchesKeyword && matchesStatus && matchesSource;
  });
});

const failedCount = computed(() => runs.value.filter((run) => run.status === 'failed').length);
const averagePassRate = computed(() => {
  if (!runs.value.length) {
    return 0;
  }
  const total = runs.value.reduce((sum, run) => sum + getPassRate(run), 0);
  return Math.round(total / runs.value.length);
});

function getModuleName(run: TestRun) {
  if (run.module_name) {
    return run.module_name;
  }
  return run.case_path.split('/').filter(Boolean).at(-1) ?? run.case_path;
}

function getPassRate(run: TestRun) {
  if (typeof run.pass_rate === 'number') {
    return run.pass_rate;
  }
  const total = run.summary?.total ?? 0;
  const passed = run.summary?.passed ?? 0;
  return total > 0 ? Math.round((passed / total) * 100) : run.status === 'passed' ? 100 : 0;
}

async function loadRuns() {
  loading.value = true;
  try {
    const response = await listTestRuns();
    runs.value = response.results;
  } finally {
    loading.value = false;
  }
}

function applyFilters(filters: { keyword: string; status: string; source: string }) {
  activeFilters.keyword = filters.keyword;
  activeFilters.status = filters.status;
  activeFilters.source = filters.source;
}

function viewFailures(run: TestRun) {
  selectedRun.value = run;
  failureDialogVisible.value = true;
}

async function handleRetryModule(run: TestRun) {
  await retryModule(run.id, {
    module_path: run.case_path,
    retry_count: 0,
  });
}

async function openReport(run: TestRun) {
  const report = await getReport(run.id);
  window.open(report.report_url, '_blank', 'noopener');
}

function openJenkins(run: TestRun) {
  window.open(`/jenkins/builds?run_id=${encodeURIComponent(run.run_id)}`, '_blank', 'noopener');
}

onMounted(() => {
  void loadRuns();
});
</script>

<template>
  <div class="module-page">
    <section class="module-hero">
      <div>
        <p class="eyebrow">Module Pass Rate</p>
        <h1>模块通过率</h1>
        <p class="module-lead">按测试模块查看通过率、失败用例和重试入口。</p>
      </div>
      <div class="module-hero-actions">
        <el-button :icon="Refresh" type="primary">一键失败重试</el-button>
        <el-button :icon="Link" plain>Jenkins 任务</el-button>
      </div>
    </section>

    <section class="module-metrics">
      <div>
        <span>模块数</span>
        <strong>{{ runs.length }}</strong>
      </div>
      <div>
        <span>失败模块</span>
        <strong>{{ failedCount }}</strong>
      </div>
      <div>
        <span>平均通过率</span>
        <strong>{{ averagePassRate }}%</strong>
      </div>
    </section>

    <RunFilters @query="applyFilters" />

    <section class="module-tabs">
      <button class="category-tab is-active" type="button">模块</button>
      <button class="category-tab" type="button">用例包</button>
      <button class="category-tab" type="button">Jenkins</button>
    </section>

    <ModuleRunTable
      :loading="loading"
      :runs="filteredRuns"
      @open-jenkins="openJenkins"
      @open-report="openReport"
      @retry-module="handleRetryModule"
      @view-failures="viewFailures"
    />

    <FailureCasesDialog
      v-model="failureDialogVisible"
      :report-title="selectedRun ? getModuleName(selectedRun) : ''"
      :test-run-id="selectedRun?.id ?? null"
      @retried="loadRuns"
    />
  </div>
</template>
