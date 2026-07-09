import { beforeEach, describe, expect, it, vi } from 'vitest'

import { http } from '@/api/client'
import {
  cancelJenkinsTask,
  createFailedCaseRetry,
  createModuleRerun,
  fetchModuleSnapshotJenkinsTasks,
  syncJenkinsTask,
} from '@/api/metrics'

vi.mock('@/api/client', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockedHttp = vi.mocked(http)

describe('Stage6 P5 metrics Jenkins API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedHttp.get.mockResolvedValue({ data: { data: [], meta: { total: 0, page: 1, per_page: 20, total_pages: 0 } } })
    mockedHttp.post.mockResolvedValue({
      data: {
        data: {
          id: 301,
          task_type: 'failed_rerun',
          status: 'queued',
          actions: { cancel: true, view_report: false, view_jenkins_task: false },
        },
      },
    })
  })

  it('失败重试使用冻结的 module snapshot 子资源路径和 retry_scope payload', async () => {
    await createFailedCaseRetry(101, { retry_scope: 'selected_failed', case_result_ids: [501, 502] })

    expect(mockedHttp.post).toHaveBeenCalledWith('/module-snapshots/101/failed-case-retries', {
      retry_scope: 'selected_failed',
      case_result_ids: [501, 502],
    })
  })

  it('模块重试、任务列表和取消任务只调用 DRF API，不直接拼 Jenkins URL', async () => {
    await createModuleRerun(101)
    await fetchModuleSnapshotJenkinsTasks(101, { date: 'today', page: 2, per_page: 20 })
    await cancelJenkinsTask(301)
    await syncJenkinsTask(301)

    expect(mockedHttp.post).toHaveBeenCalledWith('/module-snapshots/101/module-reruns', {})
    expect(mockedHttp.get).toHaveBeenCalledWith('/module-snapshots/101/jenkins-tasks', {
      params: { date: 'today', page: 2, per_page: 20 },
    })
    expect(mockedHttp.post).toHaveBeenCalledWith('/jenkins-tasks/301/cancel', {})
    expect(mockedHttp.post).toHaveBeenCalledWith('/jenkins-tasks/301/sync', {})
  })
})
