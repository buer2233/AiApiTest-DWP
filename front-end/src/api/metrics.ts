import { http } from './client'
import type {
  CaseResultFilters,
  CaseStatusUpdatePayload,
  CaseStatusUpdateResult,
  EnvironmentSummary,
  FailedCaseRetryPayload,
  JenkinsTask,
  JenkinsTaskFilters,
  ModuleSnapshotFilterOptions,
  ModuleTrend,
  ModuleSnapshotFilters,
  PaginatedCaseResults,
  PaginatedJenkinsTasks,
  PaginatedModuleSnapshots,
  TestEnvironment,
} from '@/types/metrics'

export async function fetchTestEnvironments(params: { is_active?: boolean } = {}): Promise<TestEnvironment[]> {
  const response = await http.get<{ data: TestEnvironment[] }>('/test-environments', { params })
  return response.data.data
}

export async function fetchEnvironmentSummary(environmentId: number): Promise<EnvironmentSummary> {
  const response = await http.get<{ data: EnvironmentSummary }>(`/test-environments/${environmentId}/summary`)
  return response.data.data
}

export async function fetchModuleSnapshots(params: ModuleSnapshotFilters): Promise<PaginatedModuleSnapshots> {
  const response = await http.get<PaginatedModuleSnapshots>('/module-snapshots', { params })
  return response.data
}

export async function fetchModuleSnapshotFilterOptions(params: { environment_id: number }): Promise<ModuleSnapshotFilterOptions> {
  const response = await http.get<{ data: ModuleSnapshotFilterOptions }>('/module-snapshots/filter-options', { params })
  return response.data.data
}

export async function fetchModuleSnapshotCases(
  snapshotId: number,
  params: CaseResultFilters = {},
): Promise<PaginatedCaseResults> {
  const response = await http.get<PaginatedCaseResults>(`/module-snapshots/${snapshotId}/cases`, { params })
  return response.data
}

export async function updateCaseResultStatus(
  caseResultId: number,
  payload: CaseStatusUpdatePayload,
): Promise<CaseStatusUpdateResult> {
  const response = await http.patch<{ data: CaseStatusUpdateResult }>(`/case-results/${caseResultId}/status`, payload)
  return response.data.data
}

export async function fetchModuleSnapshotTrend(snapshotId: number, days: 7 | 30): Promise<ModuleTrend> {
  const response = await http.get<{ data: ModuleTrend }>(`/module-snapshots/${snapshotId}/trend`, { params: { days } })
  return response.data.data
}

export async function createFailedCaseRetry(
  snapshotId: number,
  payload: FailedCaseRetryPayload,
): Promise<JenkinsTask> {
  const response = await http.post<{ data: JenkinsTask }>(`/module-snapshots/${snapshotId}/failed-case-retries`, payload)
  return response.data.data
}

export async function createModuleRerun(snapshotId: number): Promise<JenkinsTask> {
  const response = await http.post<{ data: JenkinsTask }>(`/module-snapshots/${snapshotId}/module-reruns`, {})
  return response.data.data
}

export async function fetchModuleSnapshotJenkinsTasks(
  snapshotId: number,
  params: JenkinsTaskFilters = {},
): Promise<PaginatedJenkinsTasks> {
  const response = await http.get<PaginatedJenkinsTasks>(`/module-snapshots/${snapshotId}/jenkins-tasks`, { params })
  return response.data
}

export async function cancelJenkinsTask(taskId: number): Promise<JenkinsTask> {
  const response = await http.post<{ data: JenkinsTask }>(`/jenkins-tasks/${taskId}/cancel`, {})
  return response.data.data
}
