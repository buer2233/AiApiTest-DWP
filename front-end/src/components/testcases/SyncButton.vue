<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";

import { useSyncTestCases } from "@/composables/useTestCases";

// 管理员专属：同步用例（确认 → 提交中 → 成功/失败反馈）。
const emit = defineEmits<{ (e: "synced"): void }>();
const { mutateAsync, isPending } = useSyncTestCases();

async function handleSync() {
  try {
    await ElMessageBox.confirm("将重新扫描 api-test 用例并更新清单，是否继续？", "同步用例", {
      type: "warning",
    });
  } catch {
    return; // 用户取消
  }
  try {
    const result = await mutateAsync();
    ElMessage.success(
      `同步完成：扫描 ${result.scanned}，新增 ${result.created}，更新 ${result.updated}，下线 ${result.deactivated}`,
    );
    emit("synced");
  } catch (e: unknown) {
    const err = e as { response?: { data?: { code?: number; message?: string } } };
    const body = err.response?.data;
    if (body?.code === 1202) {
      ElMessage.error("用例根目录不存在或不可读，请检查 API_TEST_ROOT 配置");
    } else if (body?.code === 1201) {
      ElMessage.error("无权限执行同步");
    } else {
      ElMessage.error(body?.message || "同步失败");
    }
  }
}
</script>

<template>
  <el-button type="primary" :loading="isPending" @click="handleSync">同步用例</el-button>
</template>
