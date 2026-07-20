export type EnvironmentCatalogStatus = 'pending' | 'queued' | 'running' | 'synced' | 'failed' | 'conflict' | string

export interface EnvironmentCatalogEnvironment {
  id: number
  env_key: string
  env_name: string
  url_name: string
  base_url: string
  url_desc: string
  is_active: boolean
}

export interface EnvironmentCatalogState {
  status: EnvironmentCatalogStatus
  yaml_blob_sha: string | null
  last_commit_sha: string | null
  last_synced_at: string | null
  last_error_code: string | null
  last_error_summary: string | null
}

export interface EnvironmentCatalogSyncAttempt {
  id: number
  request_id: string
  direction: string
  status: EnvironmentCatalogStatus
  expected_yaml_blob_sha: string | null
  observed_yaml_blob_sha: string | null
  queue_id: string | null
  build_number: number | null
  jenkins_build_url: string | null
  job_full_name: string | null
  commit_sha: string | null
  requested_by: string | null
  error_code: string | null
  error_summary: string | null
  created_at: string
  finished_at: string | null
}

export interface EnvironmentCatalogListResponse {
  data: EnvironmentCatalogEnvironment[]
  catalog_state: EnvironmentCatalogState
}

export interface EnvironmentCatalogWriteResult {
  environment: EnvironmentCatalogEnvironment
  sync_attempt: EnvironmentCatalogSyncAttempt
}

export interface CreateTestEnvironmentPayload {
  env_key: string
  url_name: string
  base_url: string
  url_desc: string
}

export interface UpdateTestEnvironmentPayload {
  url_name?: string
  base_url?: string
  url_desc?: string
  is_active?: boolean
}
