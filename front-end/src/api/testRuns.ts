/**
 * 测试任务 API 封装模块。
 * 本模块对接后端 `/api/test-runs/`，提供任务列表、失败用例、重试和 Allure 报告入口能力。
 */

import { http } from './http';

/** pytest/Jenkins 重试类请求可能运行较久，前端需要给足执行窗口。 */
export const TEST_RUN_COMMAND_TIMEOUT_MS = 120000;

/** 长耗时测试任务请求的 Axios 配置。 */
const testRunCommandConfig = {
  timeout: TEST_RUN_COMMAND_TIMEOUT_MS,
};

/** 测试任务执行状态。 */
export type TestRunStatus = 'pending' | 'running' | 'passed' | 'failed' | 'error';
/** 失败用例状态，保持与后端 FailureCase.Status 一致。 */
export type FailureStatus = 'failed' | 'broken' | 'skipped' | 'unknown';
/** 失败用例最近一次重试状态。 */
export type RetryStatus = 'not-retried' | 'passed' | 'failed';

/** api-test 执行 summary 中前端关心的聚合指标。 */
export interface TestRunSummary {
  total?: number;
  passed?: number;
  failed?: number;
  broken?: number;
  skipped?: number;
  duration_seconds?: number;
}

/**
 * 测试任务列表项。
 * 部分展示字段如 module_name、owner、pass_rate 允许为空，便于后续平台扩展聚合数据。
 */
export interface TestRun {
  id: number;
  run_id: string;
  case_path: string;
  module_name?: string;
  owner?: string;
  automation_owner?: string;
  pass_rate?: number;
  failure_count: number;
  status: TestRunStatus;
  retry_mode: string;
  retry_count: number;
  trigger_source: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number;
  summary?: TestRunSummary;
}

/** 失败用例详情，用于失败用例弹窗展示和选择重试。 */
export interface FailureCase {
  id: number;
  test_run: number;
  node_id: string;
  case_name: string;
  module_path: string;
  description: string;
  error_type: string;
  assertion_message: string;
  status: FailureStatus;
  retry_status: RetryStatus;
}

/** 后端列表接口统一返回结构。 */
export interface PaginatedResponse<T> {
  count: number;
  results: T[];
}

/** 仅包含重试次数的请求体。 */
export interface RetryCountPayload {
  retry_count: number;
}

/** 选择失败用例重试请求体。 */
export interface RetrySelectedPayload extends RetryCountPayload {
  failure_ids: number[];
}

/** 模块重试请求体。 */
export interface RetryModulePayload extends RetryCountPayload {
  module_path: string;
}

/** 报告入口响应结构。 */
export interface ReportResponse {
  run_id: string;
  report_url: string;
}

export async function listTestRuns(): Promise<PaginatedResponse<TestRun>> {
  /** 查询测试任务列表。 */
  const response = await http.get<PaginatedResponse<TestRun>>('/test-runs/');
  return response.data;
}

export async function getFailureCases(testRunId: number): Promise<PaginatedResponse<FailureCase>> {
  /** 查询指定测试任务下的失败用例。 */
  const response = await http.get<PaginatedResponse<FailureCase>>(`/test-runs/${testRunId}/failures/`);
  return response.data;
}

export async function retrySelectedFailures(
  testRunId: number,
  payload: RetrySelectedPayload,
): Promise<TestRun> {
  /** 按选择的失败用例发起重试。 */
  const response = await http.post<TestRun>(
    `/test-runs/${testRunId}/retry-selected/`,
    payload,
    testRunCommandConfig,
  );
  return response.data;
}

export async function retryAllFailed(testRunId: number, payload: RetryCountPayload): Promise<TestRun> {
  /** 一键重试指定任务下所有失败用例。 */
  const response = await http.post<TestRun>(
    `/test-runs/${testRunId}/retry-all-failed/`,
    payload,
    testRunCommandConfig,
  );
  return response.data;
}

export async function retryModule(testRunId: number, payload: RetryModulePayload): Promise<TestRun> {
  /** 按模块路径重新执行测试任务。 */
  const response = await http.post<TestRun>(
    `/test-runs/${testRunId}/retry-module/`,
    payload,
    testRunCommandConfig,
  );
  return response.data;
}

export async function getReport(testRunId: number): Promise<ReportResponse> {
  /** 查询后端受控 Allure 报告入口。 */
  const response = await http.get<ReportResponse>(`/test-runs/${testRunId}/report/`);
  return response.data;
}
