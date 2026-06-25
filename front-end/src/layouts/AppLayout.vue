<!--
  平台主布局组件。
  负责展示左侧菜单、顶部用户区域和测试平台主工作区。
-->

<script setup lang="ts">
import {
  DataLine,
  DocumentChecked,
  FolderOpened,
  Link,
  Menu as MenuIcon,
  SwitchButton,
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';

import ModulePassRateView from '@/views/ModulePassRateView.vue';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const router = useRouter();

const sidebarMessages: Record<string, string> = {
  runs: '当前已在模块通过率',
  failures: '请在失败模块行点击失败重试查看失败用例',
  jenkins: '请通过表格行中的更多菜单打开 Jenkins 任务',
  reports: '请通过表格行中的更多菜单或失败弹窗打开 Allure 报告',
};

function showSidebarGuide(index: string) {
  /** 左侧菜单当前作为单页工作台导航，引导用户到已实现的具体操作入口。 */
  ElMessage.info(sidebarMessages[index] ?? '当前功能正在规划中');
}

async function handleLogout() {
  /**
   * 处理用户退出。
   * 先通知后端删除 Token，再跳转回登录页，避免旧登录态继续访问平台接口。
   */
  await auth.logout();
  await router.replace('/login');
}
</script>

<template>
  <el-container class="platform-shell">
    <el-aside class="platform-sidebar" width="248px">
      <div class="sidebar-brand">
        <span class="brand-symbol">✦</span>
        <span>AiApiTest</span>
      </div>

      <el-menu class="sidebar-menu" default-active="runs">
        <el-menu-item index="runs">
          <button class="sidebar-menu-action" type="button" data-test="sidebar-runs" @click.stop="showSidebarGuide('runs')">
            <el-icon><DataLine /></el-icon>
            <span>模块通过率</span>
          </button>
        </el-menu-item>
        <el-menu-item index="failures">
          <button class="sidebar-menu-action" type="button" data-test="sidebar-failures" @click.stop="showSidebarGuide('failures')">
            <el-icon><DocumentChecked /></el-icon>
            <span>失败用例</span>
          </button>
        </el-menu-item>
        <el-menu-item index="jenkins">
          <button class="sidebar-menu-action" type="button" data-test="sidebar-jenkins" @click.stop="showSidebarGuide('jenkins')">
            <el-icon><Link /></el-icon>
            <span>Jenkins 任务</span>
          </button>
        </el-menu-item>
        <el-menu-item index="reports">
          <button class="sidebar-menu-action" type="button" data-test="sidebar-reports" @click.stop="showSidebarGuide('reports')">
            <el-icon><FolderOpened /></el-icon>
            <span>Allure 报告</span>
          </button>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="platform-header">
        <div class="header-title">
          <el-icon><MenuIcon /></el-icon>
          <span>测试平台工作台</span>
        </div>
        <div class="header-actions">
          <span class="role-chip">{{ auth.user?.role === 'admin' ? '管理员' : '普通用户' }}</span>
          <span class="username">{{ auth.user?.username }}</span>
          <el-button :icon="SwitchButton" plain @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="platform-main">
        <ModulePassRateView />
      </el-main>
    </el-container>
  </el-container>
</template>
