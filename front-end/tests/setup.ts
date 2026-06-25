/**
 * Vitest 全局测试初始化。
 * 每个测试前后清理浏览器存储和 mock，避免登录态、sessionStorage 或 spy 泄漏到其他测试。
 */

import { afterEach, beforeEach, vi } from 'vitest';

beforeEach(() => {
  // 前端登录态依赖 localStorage，测试间必须清空以保证路由守卫断言稳定。
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  // 恢复所有 mock，避免 API mock 或 window.open spy 影响后续用例。
  localStorage.clear();
  sessionStorage.clear();
  vi.restoreAllMocks();
});
