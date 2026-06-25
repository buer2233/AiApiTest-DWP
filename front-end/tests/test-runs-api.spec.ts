/**
 * 测试任务 API 封装测试。
 * 覆盖长耗时重试接口的 Axios 配置，避免真实 pytest 重试被普通短超时请求中断。
 */

import { describe, expect, it, vi } from 'vitest';

import {
  retryAllFailed,
  retryModule,
  retrySelectedFailures,
  TEST_RUN_COMMAND_TIMEOUT_MS,
} from '@/api/testRuns';
import { http } from '@/api/http';

vi.mock('@/api/http', () => ({
  http: {
    post: vi.fn(),
  },
}));

describe('test run API client', () => {
  it('uses an extended timeout for selected failure retries', async () => {
    /** 选择失败用例重试会真实执行 pytest，不能使用普通 15 秒超时。 */
    vi.mocked(http.post).mockResolvedValue({ data: { id: 1 } });

    await retrySelectedFailures(1, { failure_ids: [501], retry_count: 0 });

    expect(http.post).toHaveBeenCalledWith(
      '/test-runs/1/retry-selected/',
      { failure_ids: [501], retry_count: 0 },
      { timeout: TEST_RUN_COMMAND_TIMEOUT_MS },
    );
  });

  it('uses an extended timeout for all-failed and module retries', async () => {
    /** 一键失败重试和模块重试同样属于长耗时执行任务。 */
    vi.mocked(http.post).mockResolvedValue({ data: { id: 2 } });

    await retryAllFailed(1, { retry_count: 0 });
    await retryModule(1, { module_path: 'test_case/test_gbif_case', retry_count: 0 });

    expect(http.post).toHaveBeenCalledWith(
      '/test-runs/1/retry-all-failed/',
      { retry_count: 0 },
      { timeout: TEST_RUN_COMMAND_TIMEOUT_MS },
    );
    expect(http.post).toHaveBeenCalledWith(
      '/test-runs/1/retry-module/',
      { module_path: 'test_case/test_gbif_case', retry_count: 0 },
      { timeout: TEST_RUN_COMMAND_TIMEOUT_MS },
    );
  });
});
