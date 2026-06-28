import { http, type ApiResponse, type PaginationMeta } from './http'

export interface TestCaseItem {
  id: number
  node_id: string
  package_name: string
  module_name: string
  file_path: string
  class_name: string
  function_name: string
  title: string
  description: string
  sync_status: 'synced' | 'missing'
  last_synced_at: string
}

export interface TestCaseListParams {
  keyword?: string
  package_name?: string
  module_name?: string
  page?: number
  page_size?: number
}

export interface TestCaseSyncResult {
  created: number
  updated: number
  missing: number
  total: number
}

export async function listTestCases(params: TestCaseListParams = {}) {
  const response = await http.get<ApiResponse<TestCaseItem[]>>('/api/v1/test-cases', { params })
  return {
    data: response.data.data,
    meta: response.data.meta as PaginationMeta,
  }
}

export async function syncTestCases() {
  const response = await http.post<ApiResponse<TestCaseSyncResult>>('/api/v1/test-cases/sync')
  return response.data.data
}
