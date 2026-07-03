<script setup lang="ts">
import { ShieldCheck, UsersRound } from '@lucide/vue'
</script>

<template>
  <aside class="role-rail" aria-label="身份权限说明">
    <div class="rail-heading">
      <strong>选择身份</strong>
      <span>不同身份拥有不同权限范围</span>
    </div>

    <article class="role-card role-card-active">
      <ShieldCheck :size="36" aria-hidden="true" />
      <h2>管理人员</h2>
      <ul>
        <li>全局配置</li>
        <li>人员与权限</li>
        <li>环境与策略</li>
        <li>审计与报表</li>
      </ul>
    </article>

    <article class="role-card">
      <UsersRound :size="36" aria-hidden="true" />
      <h2>普通成员</h2>
      <ul>
        <li>执行与调试</li>
        <li>用例与报告</li>
        <li>缺陷与跟踪</li>
        <li>个人设置</li>
      </ul>
    </article>
  </aside>
</template>

<style scoped>
.role-rail {
  display: grid;
  align-content: start;
  gap: 18px;
  padding: 22px 10px;
  border: 1px solid var(--color-hairline);
  border-radius: 12px;
  background: rgba(250, 249, 245, 0.78);
}

.rail-heading {
  display: grid;
  gap: 6px;
  text-align: center;
}

.rail-heading strong {
  color: var(--color-ink);
  font-size: 16px;
}

.rail-heading span {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.45;
}

.role-card {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 24px 18px;
  border: 1px solid #d6ccbf;
  border-radius: 8px;
  color: var(--color-muted);
}

.role-card-active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.role-card h2 {
  margin: 0;
  font-size: 18px;
}

.role-card ul {
  display: grid;
  gap: 6px;
  width: 100%;
  margin: 0;
  padding-left: 18px;
  color: var(--color-body);
  font-size: 14px;
  line-height: 1.45;
}
</style>
