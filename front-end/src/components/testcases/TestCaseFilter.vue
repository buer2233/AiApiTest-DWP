<script setup lang="ts">
// 用例筛选条：模块下拉 + 关键词搜索。props 进、events 出。
defineProps<{ moduleOptions: string[] }>();

const emit = defineEmits<{
  (e: "change", payload: { moduleKey: string; keyword: string }): void;
}>();

import { ref } from "vue";

const moduleKey = ref("");
const keyword = ref("");

function apply() {
  emit("change", { moduleKey: moduleKey.value, keyword: keyword.value });
}

function reset() {
  moduleKey.value = "";
  keyword.value = "";
  emit("change", { moduleKey: "", keyword: "" });
}
</script>

<template>
  <div class="filter-bar">
    <el-select
      v-model="moduleKey"
      placeholder="全部模块"
      clearable
      class="filter-module"
      @change="apply"
    >
      <el-option v-for="m in moduleOptions" :key="m" :label="m" :value="m" />
    </el-select>
    <el-input
      v-model="keyword"
      placeholder="搜索 node_id / 标题 / 函数名"
      clearable
      class="filter-keyword"
      @keyup.enter="apply"
    />
    <el-button type="primary" @click="apply">搜索</el-button>
    <el-button @click="reset">重置</el-button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.filter-module {
  width: 200px;
}
.filter-keyword {
  width: 320px;
}
</style>
