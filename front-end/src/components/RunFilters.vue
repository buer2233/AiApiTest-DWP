<script setup lang="ts">
import { Search } from '@element-plus/icons-vue';
import { reactive } from 'vue';

const emit = defineEmits<{
  query: [filters: { keyword: string; status: string; source: string }];
}>();

const filters = reactive({
  keyword: '',
  status: '',
  source: '',
});

function submit() {
  emit('query', { ...filters });
}
</script>

<template>
  <section class="run-filters">
    <el-input
      v-model="filters.keyword"
      data-test="module-keyword"
      placeholder="用例包名 / 模块名"
      :prefix-icon="Search"
    />
    <el-select v-model="filters.status" placeholder="执行状态">
      <el-option label="全部状态" value="" />
      <el-option label="通过" value="passed" />
      <el-option label="失败" value="failed" />
      <el-option label="运行中" value="running" />
      <el-option label="异常" value="error" />
    </el-select>
    <el-select v-model="filters.source" placeholder="来源">
      <el-option label="全部来源" value="" />
      <el-option label="Jenkins" value="jenkins" />
      <el-option label="API" value="api" />
      <el-option label="手动" value="manual" />
    </el-select>
    <el-button data-test="query-modules" type="primary" @click="submit">查询</el-button>
  </section>
</template>
