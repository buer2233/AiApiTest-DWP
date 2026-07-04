import { http } from './client'
import type {
  EnvironmentSummary,
  ModuleSnapshotFilters,
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
