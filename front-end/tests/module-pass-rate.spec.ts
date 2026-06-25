/**
 * 模块通过率页面测试。
 * 覆盖模块列表展示、客户端筛选、模块重试和 Allure 报告入口。
 */

import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi } from 'vitest';

import {
  getReport,
  listTestRuns,
  retryModule,
  type PaginatedResponse,
  type TestRun,
} from '@/api/testRuns';
import ModulePassRateView from '@/views/ModulePassRateView.vue';
import { elementPlusStubs } from './element-plus-stubs';

vi.mock('@/api/testRuns', () => ({
  listTestRuns: vi.fn(),
  getFailureCases: vi.fn(),
  getReport: vi.fn(),
  retryAllFailed: vi.fn(),
  retryModule: vi.fn(),
  retrySelectedFailures: vi.fn(),
}));

/** 后端测试任务列表的模拟响应。 */
const runsResponse: PaginatedResponse<TestRun> = {
  count: 2,
  results: [
    {
      id: 101,
      run_id: 'run-module-users',
      case_path: 'test_case/test_user_case',
      module_name: '用户接口',
      owner: '平台组',
      automation_owner: 'Auto QA',
      pass_rate: 76,
      failure_count: 3,
      status: 'failed',
      retry_mode: 'none',
      retry_count: 0,
      trigger_source: 'jenkins',
      started_at: '2026-06-24T09:00:00+08:00',
      finished_at: '2026-06-24T09:03:20+08:00',
      duration_seconds: 200,
      summary: {
        total: 25,
        passed: 19,
        failed: 3,
        broken: 3,
      },
    },
    {
      id: 102,
      run_id: 'run-module-order',
      case_path: 'test_case/test_order_case',
      module_name: '订单接口',
      owner: '交易组',
      automation_owner: 'Auto QA',
      pass_rate: 100,
      failure_count: 0,
      status: 'passed',
      retry_mode: 'none',
      retry_count: 0,
      trigger_source: 'api',
      started_at: '2026-06-24T10:00:00+08:00',
      finished_at: '2026-06-24T10:01:00+08:00',
      duration_seconds: 60,
      summary: {
        total: 12,
        passed: 12,
        failed: 0,
        broken: 0,
      },
    },
  ],
};

function mountView() {
  /** 挂载模块通过率页面，并使用轻量 Element Plus stub。 */
  setActivePinia(createPinia());
  return mount(ModulePassRateView, {
    global: {
      stubs: {
        ...elementPlusStubs,
        Teleport: true,
        Transition: false,
      },
    },
  });
}

describe('module pass rate page', () => {
  it('renders filters, module table fields, and retry entries for failed modules', async () => {
    /** 页面应展示筛选区、表格字段、失败重试、模块重试和报告/Jenkins 入口。 */
    vi.mocked(listTestRuns).mockResolvedValue(runsResponse);

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).toContain('模块通过率');
    expect(wrapper.text()).toContain('日期');
    expect(wrapper.text()).toContain('用例包名');
    expect(wrapper.text()).toContain('模块名');
    expect(wrapper.text()).toContain('负责人');
    expect(wrapper.text()).toContain('自动化负责人');
    expect(wrapper.text()).toContain('通过率');
    expect(wrapper.text()).toContain('运行时间');
    expect(wrapper.text()).toContain('用户接口');
    expect(wrapper.text()).toContain('test_case/test_user_case');
    expect(wrapper.text()).toContain('76%');
    expect(wrapper.text()).toContain('失败重试');
    expect(wrapper.text()).toContain('模块重试');
    expect(wrapper.text()).toContain('Jenkins 任务');
    expect(wrapper.text()).toContain('Allure 报告');
    expect(wrapper.text()).toContain('订单接口');
    expect(wrapper.text()).toContain('100%');
  });

  it('filters modules by keyword on the client after loading runs', async () => {
    /** 查询按钮提交关键字后，页面只展示匹配模块。 */
    vi.mocked(listTestRuns).mockResolvedValue(runsResponse);

    const wrapper = mountView();
    await flushPromises();
    await wrapper.find('[data-test="module-keyword"]').setValue('订单');
    await wrapper.find('[data-test="query-modules"]').trigger('click');

    expect(wrapper.text()).toContain('订单接口');
    expect(wrapper.text()).not.toContain('用户接口');
  });

  it('calls retry-module API with the selected module path', async () => {
    /** 点击模块重试时，应把当前任务 ID 和 case_path 传给后端。 */
    vi.mocked(listTestRuns).mockResolvedValue(runsResponse);
    vi.mocked(retryModule).mockResolvedValue({ id: 201, run_id: 'retry-users' } as never);

    const wrapper = mountView();
    await flushPromises();
    await wrapper.find('[data-test="retry-module-101"]').trigger('click');

    expect(retryModule).toHaveBeenCalledWith(101, {
      module_path: 'test_case/test_user_case',
      retry_count: 0,
    });
  });

  it('opens backend controlled Allure report URL from the module actions', async () => {
    /** Allure 报告入口必须打开后端返回的受控 URL，而不是服务器本地路径。 */
    vi.mocked(listTestRuns).mockResolvedValue(runsResponse);
    vi.mocked(getReport).mockResolvedValue({
      run_id: 'run-module-users',
      report_url: '/reports/run-module-users/',
    });
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    const wrapper = mountView();
    await flushPromises();
    await wrapper.find('[data-test="open-report-101"]').trigger('click');

    expect(getReport).toHaveBeenCalledWith(101);
    expect(openSpy).toHaveBeenCalledWith('/reports/run-module-users/', '_blank', 'noopener');
  });
});
