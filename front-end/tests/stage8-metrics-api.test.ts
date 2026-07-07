import { beforeEach, describe, expect, it, vi } from 'vitest'

import { http } from '@/api/client'
import {
  fetchModuleSnapshotFilterOptions,
  fetchModuleSnapshotJenkinsTasks,
  fetchModuleSnapshots,
} from '@/api/metrics'

vi.mock('@/api/client', () => ({
  http: {
    get: vi.fn(),
  },
}))

const mockedHttp = vi.mocked(http)

describe('Stage8 metrics API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedHttp.get.mockResolvedValue({
      data: {
        data: {
          module_names: [],
          package_names: [],
          module_devs: [],
          module_tests: [],
        },
      },
    })
  })

  it('获取模块筛选选项时调用冻结的 filter-options 子资源', async () => {
    await fetchModuleSnapshotFilterOptions({ environment_id: 1 })

    expect(mockedHttp.get).toHaveBeenCalledWith('/module-snapshots/filter-options', {
      params: { environment_id: 1 },
    })
  })

  it('模块快照查询支持逗号分隔多选筛选并停止发送 pass_rate_lte', async () => {
    mockedHttp.get.mockResolvedValueOnce({
      data: { data: [], meta: { total: 0, page: 1, per_page: 20, total_pages: 0 } },
    })

    await fetchModuleSnapshots({
      environment_id: 1,
      module_name: '物种查询模块,库存模块',
      package_name: 'test_gbif_case,test_inventory_case',
      module_dev: '张三,赵六',
      module_test: '李四',
      page: 1,
      per_page: 20,
    })

    expect(mockedHttp.get).toHaveBeenCalledWith('/module-snapshots', {
      params: {
        environment_id: 1,
        module_name: '物种查询模块,库存模块',
        package_name: 'test_gbif_case,test_inventory_case',
        module_dev: '张三,赵六',
        module_test: '李四',
        page: 1,
        per_page: 20,
      },
    })
  })

  it('Jenkins 任务列表支持 task_type 筛选参数', async () => {
    mockedHttp.get.mockResolvedValueOnce({
      data: { data: [], meta: { total: 0, page: 1, per_page: 20, total_pages: 0 } },
    })

    await fetchModuleSnapshotJenkinsTasks(101, {
      date: '2026-07-06',
      status: 'running',
      task_type: 'module_rerun',
      page: 1,
      per_page: 20,
    })

    expect(mockedHttp.get).toHaveBeenCalledWith('/module-snapshots/101/jenkins-tasks', {
      params: {
        date: '2026-07-06',
        status: 'running',
        task_type: 'module_rerun',
        page: 1,
        per_page: 20,
      },
    })
  })
})
