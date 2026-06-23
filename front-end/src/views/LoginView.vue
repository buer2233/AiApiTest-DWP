<script setup lang="ts">
import { Lock, User } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const loading = ref(false);

const form = reactive({
  username: '',
  password: '',
});

const redirectPath = computed(() => {
  const redirect = route.query.redirect;
  return typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/platform';
});

async function submitLogin() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码');
    return;
  }

  loading.value = true;

  try {
    await auth.login(form.username.trim(), form.password);
    await router.replace(redirectPath.value);
  } catch {
    ElMessage.error('登录失败，请检查账号或服务状态');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-copy">
      <div class="brand-mark" aria-hidden="true">✦</div>
      <p class="eyebrow">AI API Test Platform</p>
      <h1>进入自动化测试工作台</h1>
      <p class="lead">
        统一查看测试任务、失败用例、Jenkins 触发和 Allure 报告入口。当前阶段先建立登录与平台布局。
      </p>
      <div class="dark-product-panel">
        <div class="panel-header">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div class="panel-line">
          <span class="line-key">case_path</span>
          <span>test_case/test_*_case</span>
        </div>
        <div class="panel-line">
          <span class="line-key">retry_mode</span>
          <span>selected · all-failed · module</span>
        </div>
        <div class="panel-line success">
          <span class="line-key">status</span>
          <span>ready for platform shell</span>
        </div>
      </div>
    </section>

    <section class="login-panel" aria-label="登录表单">
      <div class="panel-title">
        <span class="badge">Stage 8</span>
        <h2>登录</h2>
      </div>
      <el-form class="login-form" @submit.prevent="submitLogin">
        <el-form-item>
          <el-input
            v-model="form.username"
            :prefix-icon="User"
            autocomplete="username"
            placeholder="用户名"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            :prefix-icon="Lock"
            autocomplete="current-password"
            placeholder="密码"
            show-password
            size="large"
            type="password"
            @keyup.enter="submitLogin"
          />
        </el-form-item>
        <el-button class="login-button" :loading="loading" native-type="submit" type="primary">
          登录平台
        </el-button>
      </el-form>
    </section>
  </main>
</template>
