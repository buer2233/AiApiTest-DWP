<!--
  模块运行表格组件。
  负责展示测试任务列表，并把失败重试、模块重试、报告和 Jenkins 操作事件上抛给父组件。
-->

<script setup lang="ts">
import { MoreFilled, Refresh, Warning } from '@element-plus/icons-vue';

import type { TestRun } from '@/api/testRuns';

defineProps<{
  /** 表格展示的测试任务列表。 */
  runs: TestRun[];
  /** 表格加载状态。 */
  loading?: boolean;
}>();

const emit = defineEmits<{
  /** 查看指定任务失败用例。 */
  viewFailures: [run: TestRun];
  /** 按模块路径重试指定任务。 */
  retryModule: [run: TestRun];
  /** 打开指定任务的 Allure 报告。 */
  openReport: [run: TestRun];
  /** 打开指定任务关联的 Jenkins 入口。 */
  openJenkins: [run: TestRun];
}>();

function moduleName(run: TestRun) {
  /** 获取模块展示名称，优先使用后端聚合字段，否则从路径末段推导。 */
  if (run.module_name) {
    return run.module_name;
  }
  return run.case_path.split('/').filter(Boolean).at(-1) ?? run.case_path;
}

function passRate(run: TestRun) {
  /** 获取通过率，兼容显式 pass_rate 和 summary 统计。 */
  if (typeof run.pass_rate === 'number') {
    return run.pass_rate;
  }
  const total = run.summary?.total ?? 0;
  const passed = run.summary?.passed ?? 0;
  return total > 0 ? Math.round((passed / total) * 100) : run.status === 'passed' ? 100 : 0;
}

function duration(run: TestRun) {
  /** 格式化运行耗时。 */
  const seconds = run.duration_seconds ?? run.summary?.duration_seconds;
  if (typeof seconds === 'number') {
    return `${seconds}s`;
  }
  return '-';
}

function runDate(run: TestRun) {
  /** 从 started_at 中提取日期，缺失时显示占位符。 */
  if (!run.started_at) {
    return '-';
  }
  return run.started_at.slice(0, 10);
}
</script>

<template>
  <div class="module-table-wrap">
    <el-table :data="runs" :loading="loading" class="module-table" row-key="id">
      <el-table-column label="日期" min-width="120">
        <template #default="{ row }">{{ runDate(row) }}</template>
      </el-table-column>
      <el-table-column label="用例包名" prop="case_path" min-width="220" show-overflow-tooltip />
      <el-table-column label="模块名" min-width="150">
        <template #default="{ row }">
          <button class="text-link-button" type="button" @click="emit('viewFailures', row)">
            {{ moduleName(row) }}
          </button>
        </template>
      </el-table-column>
      <el-table-column label="负责人" min-width="120">
        <template #default="{ row }">{{ row.owner || '平台组' }}</template>
      </el-table-column>
      <el-table-column label="自动化负责人" min-width="140">
        <template #default="{ row }">{{ row.automation_owner || 'Auto QA' }}</template>
      </el-table-column>
      <el-table-column label="通过率" min-width="140">
        <template #default="{ row }">
          <span :class="['pass-rate-pill', passRate(row) < 100 ? 'is-risk' : 'is-good']">
            {{ passRate(row) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column label="运行时间" min-width="110">
        <template #default="{ row }">{{ duration(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="260">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button
              v-if="passRate(row) < 100"
              :data-test="`view-failures-${row.id}`"
              :icon="Warning"
              size="small"
              type="primary"
              @click="emit('viewFailures', row)"
            >
              失败重试
            </el-button>
            <el-button
              :data-test="`retry-module-${row.id}`"
              :icon="Refresh"
              plain
              size="small"
              @click="emit('retryModule', row)"
            >
              模块重试
            </el-button>
            <el-dropdown trigger="click">
              <el-button :icon="MoreFilled" circle plain size="small" aria-label="更多" />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="emit('openJenkins', row)">Jenkins 任务</el-dropdown-item>
                  <el-dropdown-item :data-test="`open-report-${row.id}`" @click="emit('openReport', row)">
                    Allure 报告
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
