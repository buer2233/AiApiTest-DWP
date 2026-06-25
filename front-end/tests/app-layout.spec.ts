/**
 * 平台主布局测试。
 * 覆盖左侧菜单点击反馈，避免导航项看起来可点击但没有任何响应。
 */

import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { createRouter, createMemoryHistory } from 'vue-router';

import AppLayout from '@/layouts/AppLayout.vue';
import { useAuthStore } from '@/stores/auth';

const messageMocks = vi.hoisted(() => ({
  info: vi.fn(),
}));

vi.mock('element-plus', async (importOriginal) => {
  /** 保留 Element Plus 真实导出，只替换消息组件，便于断言菜单点击反馈。 */
  const actual = await importOriginal<typeof import('element-plus')>();
  return {
    ...actual,
    ElMessage: {
      info: messageMocks.info,
    },
  };
});

vi.mock('@/views/ModulePassRateView.vue', () => ({
  default: {
    name: 'ModulePassRateView',
    template: '<section data-test="module-view">模块通过率内容</section>',
  },
}));

const layoutStubs = {
  ElAside: {
    template: '<aside><slot /></aside>',
  },
  ElButton: {
    emits: ['click'],
    template: '<button type="button" @click="$emit(\'click\', $event)"><slot /></button>',
  },
  ElContainer: {
    template: '<section><slot /></section>',
  },
  ElHeader: {
    template: '<header><slot /></header>',
  },
  ElIcon: {
    template: '<span><slot /></span>',
  },
  ElMain: {
    template: '<main><slot /></main>',
  },
  ElMenu: defineComponent({
    name: 'ElMenu',
    setup(_, { slots }) {
      /** 菜单容器只负责渲染菜单项，点击反馈由菜单项自身事件覆盖。 */
      return () => h('nav', slots.default?.());
    },
  }),
  ElMenuItem: defineComponent({
    name: 'ElMenuItem',
    props: ['index'],
    setup(_, { slots }) {
      /** 菜单项 stub 只做容器，点击由组件内真实按钮负责。 */
      return () => h('div', slots.default?.());
    },
  }),
};

function mountLayout() {
  /** 挂载平台主布局，并准备一个已登录管理员会话。 */
  setActivePinia(createPinia());
  const auth = useAuthStore();
  auth.setSession({
    token: 'layout-token',
    user: {
      id: 1,
      username: 'admin',
      role: 'admin',
    },
  });

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/login', component: { template: '<div>login</div>' } },
    ],
  });

  return mount(AppLayout, {
    global: {
      plugins: [router],
      stubs: layoutStubs,
    },
  });
}

describe('platform app layout', () => {
  it('shows feedback when each sidebar menu item is clicked', async () => {
    /** 左侧菜单项必须对点击有反馈，不能静默无响应。 */
    messageMocks.info.mockClear();

    const wrapper = mountLayout();
    await wrapper.find('[data-test="sidebar-runs"]').trigger('click');
    await wrapper.find('[data-test="sidebar-failures"]').trigger('click');
    await wrapper.find('[data-test="sidebar-jenkins"]').trigger('click');
    await wrapper.find('[data-test="sidebar-reports"]').trigger('click');

    expect(messageMocks.info).toHaveBeenCalledWith('当前已在模块通过率');
    expect(messageMocks.info).toHaveBeenCalledWith('请在失败模块行点击失败重试查看失败用例');
    expect(messageMocks.info).toHaveBeenCalledWith('请通过表格行中的更多菜单打开 Jenkins 任务');
    expect(messageMocks.info).toHaveBeenCalledWith('请通过表格行中的更多菜单或失败弹窗打开 Allure 报告');
  });
});
