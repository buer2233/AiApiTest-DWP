import { mount, flushPromises } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import {
  getFailureCases,
  getReport,
  retryAllFailed,
  retrySelectedFailures,
  type FailureCase,
  type PaginatedResponse,
} from '@/api/testRuns';
import FailureCasesDialog from '@/components/FailureCasesDialog.vue';
import { elementPlusStubs } from './element-plus-stubs';

vi.mock('@/api/testRuns', () => ({
  getFailureCases: vi.fn(),
  getReport: vi.fn(),
  listTestRuns: vi.fn(),
  retryAllFailed: vi.fn(),
  retryModule: vi.fn(),
  retrySelectedFailures: vi.fn(),
}));

const failuresResponse: PaginatedResponse<FailureCase> = {
  count: 2,
  results: [
    {
      id: 501,
      test_run: 101,
      node_id: 'test_case/test_user_case/test_user_api.py::test_create_user',
      case_name: 'test_create_user',
      module_path: 'test_case/test_user_case',
      description: '创建用户失败时返回错误码',
      error_type: 'AssertionError',
      assertion_message: 'expected 201 got 500',
      status: 'failed',
      retry_status: 'not-retried',
    },
    {
      id: 502,
      test_run: 101,
      node_id: 'test_case/test_user_case/test_user_api.py::test_query_user',
      case_name: 'test_query_user',
      module_path: 'test_case/test_user_case',
      description: '查询用户响应缺少字段',
      error_type: 'KeyError',
      assertion_message: 'missing field: data.id',
      status: 'broken',
      retry_status: 'failed',
    },
  ],
};

function mountDialog() {
  return mount(FailureCasesDialog, {
    props: {
      modelValue: true,
      testRunId: 101,
      reportTitle: '用户接口',
    },
    global: {
      stubs: {
        ...elementPlusStubs,
        Teleport: true,
        Transition: false,
      },
    },
  });
}

describe('failure cases dialog', () => {
  it('renders failure filters and failure case table fields', async () => {
    vi.mocked(getFailureCases).mockResolvedValue(failuresResponse);

    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.text()).toContain('失败用例');
    expect(wrapper.text()).toContain('用例名');
    expect(wrapper.text()).toContain('错误类型');
    expect(wrapper.text()).toContain('执行状态');
    expect(wrapper.text()).toContain('用例描述');
    expect(wrapper.text()).toContain('断言');
    expect(wrapper.text()).toContain('错误信息');
    expect(wrapper.text()).toContain('确认结果');
    expect(wrapper.text()).toContain('test_create_user');
    expect(wrapper.text()).toContain('AssertionError');
    expect(wrapper.text()).toContain('expected 201 got 500');
  });

  it('filters failure cases by case name and error type', async () => {
    vi.mocked(getFailureCases).mockResolvedValue(failuresResponse);

    const wrapper = mountDialog();
    await flushPromises();
    await wrapper.find('[data-test="failure-keyword"]').setValue('query');
    await wrapper.find('[data-test="failure-error-type"]').setValue('KeyError');
    await wrapper.find('[data-test="query-failures"]').trigger('click');

    expect(wrapper.text()).toContain('test_query_user');
    expect(wrapper.text()).not.toContain('test_create_user');
  });

  it('retries selected failure cases and all failed cases', async () => {
    vi.mocked(getFailureCases).mockResolvedValue(failuresResponse);
    vi.mocked(retrySelectedFailures).mockResolvedValue({ id: 301, run_id: 'retry-selected' } as never);
    vi.mocked(retryAllFailed).mockResolvedValue({ id: 302, run_id: 'retry-all' } as never);

    const wrapper = mountDialog();
    await flushPromises();
    await wrapper.find('[data-test="select-failure-501"]').setValue(true);
    await wrapper.find('[data-test="retry-selected"]').trigger('click');
    await wrapper.find('[data-test="retry-all-failed"]').trigger('click');

    expect(retrySelectedFailures).toHaveBeenCalledWith(101, {
      failure_ids: [501],
      retry_count: 0,
    });
    expect(retryAllFailed).toHaveBeenCalledWith(101, {
      retry_count: 0,
    });
  });

  it('opens the Allure report entry returned by backend', async () => {
    vi.mocked(getFailureCases).mockResolvedValue(failuresResponse);
    vi.mocked(getReport).mockResolvedValue({
      run_id: 'run-module-users',
      report_url: '/reports/run-module-users/',
    });
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    const wrapper = mountDialog();
    await flushPromises();
    await wrapper.find('[data-test="open-report"]').trigger('click');

    expect(getReport).toHaveBeenCalledWith(101);
    expect(openSpy).toHaveBeenCalledWith('/reports/run-module-users/', '_blank', 'noopener');
  });
});
