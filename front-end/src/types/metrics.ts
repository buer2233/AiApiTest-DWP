import type { PaginationMeta } from './api'

export type RateValue = number | string

export interface TestEnvironment {
  id: number
  env_key: string
  env_name: string
  base_url: string
}

export interface EnvironmentSummary {
  environment: TestEnvironment
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | string | null
  total_count: number
  failed_count: number
  passed_count: number
  skipped_count: number
  pass_rate: RateValue
  actions: {
    generate_report: boolean
  }
}

export interface ModuleSnapshotActions {
  failed_rerun: boolean
  module_rerun: boolean
  trend_7d: boolean
  trend_30d: boolean
  jenkins_tasks: boolean
}

export interface ModuleSnapshot {
  id: number
  completed_at: string
  package_name: string
  module_name: string
  module_dev: string
  module_test: string
  total_count: number
  failed_count: number
  pass_rate: RateValue
  skipped_count: number
  duration_seconds: number | string | null
  actions: ModuleSnapshotActions
}

export type CaseDisplayStatus = 'failed' | 'passed' | 'skipped'

export interface CaseResultActions {
  can_update_status: boolean
  can_retry: boolean
}

export interface CaseResult {
  id: number
  node_id: string
  case_name: string
  case_summary: string
  error_type: string
  assertion_text: string
  execution_status: string
  display_status: CaseDisplayStatus
  error_message_summary: string
  error_message_detail: string | null
  confirmation_result: string
  actions: CaseResultActions
}

export interface CaseResultFilters {
  status?: CaseDisplayStatus
  case_name?: string
  node_id?: string
  error_type?: string
  page?: number
  per_page?: number
}

export interface PaginatedCaseResults {
  data: CaseResult[]
  meta: PaginationMeta
}

export interface CaseStatusUpdatePayload {
  display_status: CaseDisplayStatus
  reason: string
}

export interface CaseStatusUpdateResult {
  case_result: {
    id: number
    display_status: CaseDisplayStatus
    confirmation_result: string
  }
  module_summary: {
    snapshot_id: number
    total_count: number
    failed_count: number
    passed_count: number
    skipped_count: number
    pass_rate: RateValue
  }
  environment_summary: {
    environment_id: number
    total_count: number
    failed_count: number
    pass_rate: RateValue
  }
  audit_id: number
}

export interface ModuleTrendPoint {
  run_date: string
  run_type: string
  total_count: number
  failed_count: number
  skipped_count: number
  pass_rate: RateValue
  duration_seconds: number | string | null
}

export interface ModuleTrend {
  module: {
    snapshot_id: number
    module_name: string
    package_name: string
    environment_name: string
  }
  days: 7 | 30
  series: ModuleTrendPoint[]
}

export interface ModuleSnapshotFilters {
  environment_id: number
  module_name?: string
  package_name?: string
  module_test?: string
  pass_rate_lte?: string
  sort?: string
  page?: number
  per_page?: number
}

export interface PaginatedModuleSnapshots {
  data: ModuleSnapshot[]
  meta: PaginationMeta
}
