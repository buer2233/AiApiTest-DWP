<script setup lang="ts">
import {
  DataLine,
  DocumentChecked,
  FolderOpened,
  Link,
  Menu as MenuIcon,
  Refresh,
  SwitchButton,
} from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';

import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const router = useRouter();

async function handleLogout() {
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
          <el-icon><DataLine /></el-icon>
          <span>模块通过率</span>
        </el-menu-item>
        <el-menu-item index="failures">
          <el-icon><DocumentChecked /></el-icon>
          <span>失败用例</span>
        </el-menu-item>
        <el-menu-item index="jenkins">
          <el-icon><Link /></el-icon>
          <span>Jenkins 任务</span>
        </el-menu-item>
        <el-menu-item index="reports">
          <el-icon><FolderOpened /></el-icon>
          <span>Allure 报告</span>
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
        <section class="toolbar-band">
          <div>
            <p class="eyebrow">Platform shell</p>
            <h1>接口自动化执行概览</h1>
          </div>
          <div class="toolbar-actions">
            <el-button :icon="Refresh" type="primary">一键失败重试</el-button>
            <el-button plain>Jenkins 任务</el-button>
          </div>
        </section>

        <section class="filter-strip">
          <el-input placeholder="用例包名 / 模块名" />
          <el-select placeholder="执行状态" value="">
            <el-option label="全部" value="" />
            <el-option label="通过" value="passed" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-button plain>查询</el-button>
        </section>

        <section class="stage-card">
          <div class="stage-card-copy">
            <span class="badge">Stage 8</span>
            <h2>登录态与基础布局已就绪</h2>
            <p>
              Stage 9 会在这里接入模块通过率表格、失败用例弹窗、选择重试和报告入口。
            </p>
          </div>
          <div class="metric-grid">
            <div>
              <span>用户角色</span>
              <strong>{{ auth.user?.role }}</strong>
            </div>
            <div>
              <span>认证状态</span>
              <strong>Token</strong>
            </div>
            <div>
              <span>下一阶段</span>
              <strong>模块通过率</strong>
            </div>
          </div>
        </section>
      </el-main>
    </el-container>
  </el-container>
</template>
