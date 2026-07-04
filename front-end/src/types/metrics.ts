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
