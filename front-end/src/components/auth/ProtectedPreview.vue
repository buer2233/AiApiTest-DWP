<script setup lang="ts">
import { Gauge, LockKeyhole, ShieldAlert } from '@lucide/vue'

defineProps<{
  unlocked: boolean
}>()
</script>

<template>
  <section class="protected-preview" aria-label="受保护路由预览">
    <div class="locked-summary">
      <ShieldAlert :size="70" aria-hidden="true" />
      <strong v-if="!unlocked">401</strong>
      <strong v-else class="unlocked-code">200</strong>
      <span>{{ unlocked ? '平台访问已解锁' : '受保护路由' }}</span>
      <p>{{ unlocked ? '已检测到有效 authToken Cookie，可以查看平台数据。' : '未检测到有效的 authToken Cookie，请先完成登录或注册以访问平台功能。' }}</p>
    </div>

    <nav class="preview-nav" aria-label="锁定菜单">
      <a class="preview-nav-item preview-nav-item-active"><Gauge :size="16" />概览</a>
      <a class="preview-nav-item"><LockKeyhole :size="16" />接口管理</a>
      <a class="preview-nav-item"><LockKeyhole :size="16" />用例管理</a>
      <a class="preview-nav-item"><LockKeyhole :size="16" />测试执行</a>
      <a class="preview-nav-item"><LockKeyhole :size="16" />报告中心</a>
    </nav>

    <div class="preview-main">
      <div class="metric-grid">
        <div class="metric-card" v-for="item in ['通过率', '执行用例', '失败用例', '接口数量']" :key="item">
          <span>{{ item }}</span>
          <strong>{{ unlocked ? '0' : '--' }}</strong>
          <LockKeyhole v-if="!unlocked" :size="16" aria-hidden="true" />
        </div>
      </div>
      <div class="task-table">
        <div class="table-heading">近期执行任务</div>
        <div class="table-row table-head">
          <span>任务名称</span>
          <span>环境</span>
          <span>执行人</span>
          <span>状态</span>
        </div>
        <div class="empty-lock">
          <LockKeyhole :size="34" aria-hidden="true" />
          <span>{{ unlocked ? '暂无执行数据' : '登录后查看数据' }}</span>
        </div>
      </div>
    </div>

    <aside class="cookie-panel">
      <h2>authToken Cookie</h2>
      <div class="cookie-box">
        <code>Cookie: authToken=******...</code>
        <span>
          状态:
          <b :class="unlocked ? 'state-ok' : 'state-error'">{{ unlocked ? '已检测到有效 Cookie' : '未检测到有效 Cookie' }}</b>
        </span>
      </div>
      <h3>路由守卫状态</h3>
      <ul>
        <li><i :class="unlocked ? 'dot-ok' : 'dot-error'"></i>全局守卫 {{ unlocked ? '已通过' : '未通过' }}</li>
        <li><i :class="unlocked ? 'dot-ok' : 'dot-error'"></i>权限校验 {{ unlocked ? '已通过' : '未通过' }}</li>
        <li><i :class="unlocked ? 'dot-ok' : 'dot-error'"></i>角色校验 {{ unlocked ? '已通过' : '未通过' }}</li>
      </ul>
    </aside>
  </section>
</template>

<style scoped>
.protected-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 18px;
  min-height: 290px;
  padding: 22px;
  border-radius: 8px;
  background: var(--color-surface-dark);
  color: var(--color-on-dark);
}

.locked-summary,
.preview-nav,
.preview-main,
.cookie-panel {
  min-width: 0;
}

.locked-summary {
  display: grid;
  flex: 1 1 220px;
  align-content: center;
  justify-items: center;
  gap: 10px;
  color: #d9826c;
  text-align: center;
}

.locked-summary strong {
  font-size: 42px;
}

.locked-summary span {
  color: var(--color-on-dark);
  font-size: 18px;
  font-weight: 700;
}

.locked-summary p {
  max-width: 210px;
  margin: 0;
  color: #c5c0b8;
  font-size: 14px;
  line-height: 1.6;
}

.unlocked-code {
  color: var(--color-success);
}

.preview-nav {
  display: grid;
  flex: 0 1 160px;
  align-content: start;
  gap: 8px;
  padding: 8px 0;
}

.preview-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 0 12px;
  border-radius: 8px;
  color: #b9b4ab;
  text-decoration: none;
}

.preview-nav-item-active {
  background: var(--color-surface-dark-elevated);
  color: #f3d7a3;
}

.preview-main {
  display: grid;
  flex: 2 1 420px;
  gap: 18px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 10px;
  min-height: 80px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  background: var(--color-surface-dark-elevated);
  color: #c5c0b8;
}

.metric-card strong {
  color: var(--color-on-dark);
  font-size: 20px;
}

.task-table {
  min-height: 150px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  background: rgba(37, 35, 32, 0.66);
}

.table-heading {
  padding: 14px;
  color: #c5c0b8;
}

.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  padding: 10px 14px;
  color: #a09d96;
  font-size: 13px;
}

.empty-lock {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 26px;
  color: #a09d96;
}

.cookie-panel {
  display: grid;
  flex: 1 1 280px;
  align-content: start;
  gap: 14px;
  padding-left: 18px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.cookie-panel h2,
.cookie-panel h3 {
  margin: 0;
  font-size: 16px;
}

.cookie-box {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: #c5c0b8;
}

.cookie-box code {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 13px;
}

.state-error {
  color: #ee836f;
}

.state-ok {
  color: var(--color-success);
}

.cookie-panel ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: #c5c0b8;
  font-size: 14px;
}

.dot-error,
.dot-ok {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 8px;
  border-radius: 50%;
}

.dot-error {
  background: var(--color-error);
}

.dot-ok {
  background: var(--color-success);
}

@media (max-width: 1320px) {
  .cookie-panel {
    flex-basis: 100%;
    padding-left: 0;
    padding-top: 18px;
    border-left: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
}

@media (max-width: 720px) {
  .locked-summary,
  .preview-nav,
  .preview-main,
  .cookie-panel {
    flex-basis: 100%;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
