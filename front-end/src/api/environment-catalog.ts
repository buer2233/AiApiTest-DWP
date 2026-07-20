import { http } from './client'
import type {
  CreateTestEnvironmentPayload,
  EnvironmentCatalogListResponse,
  EnvironmentCatalogSyncAttempt,
  EnvironmentCatalogWriteResult,
  UpdateTestEnvironmentPayload,
} from '@/types/environment-catalog'

export async function fetchEnvironmentCatalog(params: { is_active?: boolean } = {}): Promise<EnvironmentCatalogListResponse> {
  const response = await http.get<EnvironmentCatalogListResponse>('/test-environments', { params })
  return response.data
}

export async function createTestEnvironment(payload: CreateTestEnvironmentPayload): Promise<EnvironmentCatalogWriteResult> {
  const response = await http.post<{ data: EnvironmentCatalogWriteResult }>('/test-environments', payload)
  return response.data.data
}

export async function updateTestEnvironment(
  environmentId: number,
  payload: UpdateTestEnvironmentPayload,
): Promise<EnvironmentCatalogWriteResult> {
  const response = await http.patch<{ data: EnvironmentCatalogWriteResult }>(`/test-environments/${environmentId}`, payload)
  return response.data.data
}

export async function deactivateTestEnvironment(environmentId: number): Promise<EnvironmentCatalogWriteResult> {
  const response = await http.delete<{ data: EnvironmentCatalogWriteResult }>(`/test-environments/${environmentId}`)
  return response.data.data
}

export async function syncTestEnvironmentsFromYaml(): Promise<EnvironmentCatalogSyncAttempt> {
  const response = await http.post<{ data: EnvironmentCatalogSyncAttempt }>('/test-environments/sync-from-yaml', {})
  return response.data.data
}

export async function fetchEnvironmentCatalogSyncAttempt(attemptId: number): Promise<EnvironmentCatalogSyncAttempt> {
  const response = await http.get<{ data: EnvironmentCatalogSyncAttempt }>(`/environment-catalog-sync-attempts/${attemptId}`)
  return response.data.data
}

export async function retryEnvironmentCatalogSyncAttempt(attemptId: number): Promise<EnvironmentCatalogSyncAttempt> {
  const response = await http.post<{ data: EnvironmentCatalogSyncAttempt }>(`/environment-catalog-sync-attempts/${attemptId}/retry`, {})
  return response.data.data
}
