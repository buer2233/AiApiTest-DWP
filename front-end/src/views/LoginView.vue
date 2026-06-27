<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import type { FormInstance, FormRules } from "element-plus";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

const formRef = ref<FormInstance>();
const form = reactive({ username: "", password: "" });
const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

const loading = ref(false);
const errorMessage = ref("");
const errorType = ref<"error" | "warning">("error");

async function handleSubmit() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    await auth.login(form.username, form.password);
    router.push({ name: "test-cases" });
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { message?: string } } };
    const status = err.response?.status;
    const message = err.response?.data?.message;
    // 403 为账号状态问题（待审批/已停用），用警告样式区分凭据错误
    errorType.value = status === 403 ? "warning" : "error";
    errorMessage.value = message || "用户名或密码错误";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1 class="auth-title">Hermes 测试平台</h1>
      <p class="auth-subtitle">登录以访问测试用例平台</p>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        :type="errorType"
        show-icon
        :closable="false"
        class="auth-alert"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="auth-submit" @click="handleSubmit">
          登录
        </el-button>
      </el-form>

      <div class="auth-foot">
        还没有账号？<router-link :to="{ name: 'register' }">去注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}
.auth-card {
  width: 400px;
}
.auth-title {
  font-size: 24px;
  color: var(--brand-primary);
  text-align: center;
  margin: 0 0 4px;
}
.auth-subtitle {
  color: var(--text-secondary);
  text-align: center;
  margin: 0 0 20px;
}
.auth-alert {
  margin-bottom: 16px;
}
.auth-submit {
  width: 100%;
}
.auth-foot {
  text-align: center;
  margin-top: 16px;
  color: var(--text-secondary);
}
</style>
