import { beforeEach, describe, expect, it, vi } from 'vitest'

import { http } from '@/api/client'
import {
  createTestEnvironment,
  deactivateTestEnvironment,
  fetchEnvironmentCatalog,
  fetchEnvironmentCatalogSyncAttempt,
  retryEnvironmentCatalogSyncAttempt,
  syncTestEnvironmentsFromYaml,
  updateTestEnvironment,
} from '@/api/environment-catalog'

vi.mock('@/api/client', () => ({
  http: {
    delete: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
  },
}))

const mockedHttp = vi.mocked(http)

describe('Stage13 环境目录浏览器 API 契约', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedHttp.get.mockResolvedValue({ data: { data: [], catalog_state: {} } })
    mockedHttp.post.mockResolvedValue({ data: { data: {} } })
    mockedHttp.patch.mockResolvedValue({ data: { data: {} } })
    mockedHttp.delete.mockResolvedValue({ data: { data: {} } })
  })

  it('读取目录时请求冻结集合资源并保留启停筛选', async () => {
    await fetchEnvironmentCatalog({ is_active: false })

    expect(mockedHttp.get).toHaveBeenCalledWith('/test-environments', {
      params: { is_active: false },
    })
  })

  it('新增、编辑和停用都使用冻结的异步写入资源', async () => {
    const createPayload = {
      env_key: 'stage13-qa',
      url_name: 'Stage13 QA',
      base_url: 'https://stage13-qa.example.invalid/api',
      url_desc: '自动化回归测试环境',
    }

    await createTestEnvironment(createPayload)
    await updateTestEnvironment(7, { url_name: 'Stage13 QA v2' })
    await deactivateTestEnvironment(7)

    expect(mockedHttp.post).toHaveBeenCalledWith('/test-environments', createPayload)
    expect(mockedHttp.patch).toHaveBeenCalledWith('/test-environments/7', { url_name: 'Stage13 QA v2' })
    expect(mockedHttp.delete).toHaveBeenCalledWith('/test-environments/7')
  })

  it('导入、查询和重试同步请求时不会暴露内部回调资源', async () => {
    await syncTestEnvironmentsFromYaml()
    await fetchEnvironmentCatalogSyncAttempt(13)
    await retryEnvironmentCatalogSyncAttempt(13)

    expect(mockedHttp.post).toHaveBeenCalledWith('/test-environments/sync-from-yaml', {})
    expect(mockedHttp.get).toHaveBeenCalledWith('/environment-catalog-sync-attempts/13')
    expect(mockedHttp.post).toHaveBeenCalledWith('/environment-catalog-sync-attempts/13/retry', {})
  })
})
