<script setup lang="ts">
import type { TestCase } from "@/types";

defineProps<{ items: TestCase[]; loading: boolean }>();

// severity 级别 → 标签类型（与 UI 原型配色一致；状态色不被品牌色替代）
const severityType: Record<string, string> = {
  blocker: "danger",
  critical: "danger",
  normal: "info",
  minor: "info",
  trivial: "info",
};
</script>

<template>
  <el-table v-loading="loading" :data="items" stripe>
    <el-table-column prop="module_key" label="模块" width="160" />
    <el-table-column label="标题" min-width="180">
      <template #default="{ row }">{{ row.case_title || "—" }}</template>
    </el-table-column>
    <el-table-column prop="node_id" label="node_id" min-width="280" show-overflow-tooltip />
    <el-table-column label="story" width="140">
      <template #default="{ row }">{{ row.story || "—" }}</template>
    </el-table-column>
    <el-table-column label="severity" width="120">
      <template #default="{ row }">
        <el-tag v-if="row.severity" :type="severityType[row.severity] || 'info'" size="small">
          {{ row.severity }}
        </el-tag>
        <span v-else>—</span>
      </template>
    </el-table-column>
    <template #empty>
      <el-empty description="暂无用例，请管理员同步" />
    </template>
  </el-table>
</template>
