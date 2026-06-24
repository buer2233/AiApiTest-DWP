import { http } from './http';

export type TestRunStatus = 'pending' | 'running' | 'passed' | 'failed' | 'error';
export type FailureStatus = 'failed' | 'broken' | 'skipped' | 'unknown';
export type RetryStatus = 'not-retried' | 'passed' | 'failed';

export interface TestRunSummary {
  total?: number;
  passed?: number;
  failed?: number;
  broken?: number;
  skipped?: number;
  duration_seconds?: number;
}

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

export interface PaginatedResponse<T> {
  count: number;
  results: T[];
}

export interface RetryCountPayload {
  retry_count: number;
}

export interface RetrySelectedPayload extends RetryCountPayload {
  failure_ids: number[];
}

export interface RetryModulePayload extends RetryCountPayload {
  module_path: string;
}

export interface ReportResponse {
  run_id: string;
  report_url: string;
}

export async function listTestRuns(): Promise<PaginatedResponse<TestRun>> {
  const response = await http.get<PaginatedResponse<TestRun>>('/test-runs/');
  return response.data;
}

export async function getFailureCases(testRunId: number): Promise<PaginatedResponse<FailureCase>> {
  const response = await http.get<PaginatedResponse<FailureCase>>(`/test-runs/${testRunId}/failures/`);
  return response.data;
}

export async function retrySelectedFailures(
  testRunId: number,
  payload: RetrySelectedPayload,
): Promise<TestRun> {
  const response = await http.post<TestRun>(`/test-runs/${testRunId}/retry-selected/`, payload);
  return response.data;
}

export async function retryAllFailed(testRunId: number, payload: RetryCountPayload): Promise<TestRun> {
  const response = await http.post<TestRun>(`/test-runs/${testRunId}/retry-all-failed/`, payload);
  return response.data;
}

export async function retryModule(testRunId: number, payload: RetryModulePayload): Promise<TestRun> {
  const response = await http.post<TestRun>(`/test-runs/${testRunId}/retry-module/`, payload);
  return response.data;
}

export async function getReport(testRunId: number): Promise<ReportResponse> {
  const response = await http.get<ReportResponse>(`/test-runs/${testRunId}/report/`);
  return response.data;
}
