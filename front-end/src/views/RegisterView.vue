<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";

import { register } from "@/api/auth";

const router = useRouter();
const formRef = ref<FormInstance>();
const form = reactive({ username: "", email: "", password: "", password_confirm: "" });

const rules: FormRules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, max: 150, message: "用户名长度 3-150", trigger: "blur" },
  ],
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    { type: "email", message: "邮箱格式不正确", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 8, message: "密码至少 8 位", trigger: "blur" },
  ],
  password_confirm: [
    { required: true, message: "请再次输入密码", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) callback(new Error("两次密码不一致"));
        else callback();
      },
      trigger: "blur",
    },
  ],
};

const loading = ref(false);
const fieldErrors = reactive<Record<string, string>>({});

async function handleSubmit() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;
  loading.value = true;
  Object.keys(fieldErrors).forEach((k) => delete fieldErrors[k]);
  try {
    await register({ ...form });
    ElMessage.success("注册成功，待管理员审批");
    router.push({ name: "login" });
  } catch (e: unknown) {
    const err = e as { response?: { data?: { code?: number; message?: string } } };
    const body = err.response?.data;
    // 后端业务码映射到字段级错误
    if (body?.code === 1001) fieldErrors.username = "用户名已被占用";
    else if (body?.code === 1002) fieldErrors.email = "邮箱已被占用";
    else if (body?.code === 1003) fieldErrors.password_confirm = "两次密码不一致";
    else ElMessage.error(body?.message || "注册失败，请检查输入");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1 class="auth-title">注册新账号</h1>
      <p class="auth-subtitle">注册后需管理员审批方可登录</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item label="用户名" prop="username" :error="fieldErrors.username">
          <el-input v-model="form.username" placeholder="3-150 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email" :error="fieldErrors.email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="password_confirm" :error="fieldErrors.password_confirm">
          <el-input
            v-model="form.password_confirm"
            type="password"
            show-password
            placeholder="再次输入密码"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="auth-submit" @click="handleSubmit">
          注册
        </el-button>
      </el-form>

      <div class="auth-foot">
        已有账号？<router-link :to="{ name: 'login' }">去登录</router-link>
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
.auth-submit {
  width: 100%;
}
.auth-foot {
  text-align: center;
  margin-top: 16px;
  color: var(--text-secondary);
}
</style>
