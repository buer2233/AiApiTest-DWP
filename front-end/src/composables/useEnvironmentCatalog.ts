import { computed, onScopeDispose, shallowRef } from 'vue'

import {
  createTestEnvironment,
  deactivateTestEnvironment,
  fetchEnvironmentCatalog,
  fetchEnvironmentCatalogSyncAttempt,
  retryEnvironmentCatalogSyncAttempt,
  syncTestEnvironmentsFromYaml,
  updateTestEnvironment,
} from '@/api/environment-catalog'
import { toApiError } from '@/api/client'
import type {
  CreateTestEnvironmentPayload,
  EnvironmentCatalogEnvironment,
  EnvironmentCatalogState,
  EnvironmentCatalogSyncAttempt,
  EnvironmentCatalogWriteResult,
  UpdateTestEnvironmentPayload,
} from '@/types/environment-catalog'

const ACTIVE_SYNC_STATUSES = new Set(['pending', 'queued', 'running'])
const POLL_INTERVAL_MS = 3000

export function useEnvironmentCatalog() {
  const environments = shallowRef<EnvironmentCatalogEnvironment[]>([])
  const catalogState = shallowRef<EnvironmentCatalogState | null>(null)
  const currentAttempt = shallowRef<EnvironmentCatalogSyncAttempt | null>(null)
  const loading = shallowRef(false)
  const submitting = shallowRef(false)
  const errorMessage = shallowRef('')
  const attemptErrorMessage = shallowRef('')
  let pollTimer: ReturnType<typeof setTimeout> | null = null

  const hasActiveAttempt = computed(() => {
    return currentAttempt.value ? ACTIVE_SYNC_STATUSES.has(currentAttempt.value.status) : false
  })

  function replaceEnvironment(nextEnvironment: EnvironmentCatalogEnvironment) {
    const existingIndex = environments.value.findIndex((environment) => environment.id === nextEnvironment.id)
    if (existingIndex === -1) {
      environments.value = [nextEnvironment, ...environments.value]
      return
    }
    environments.value = environments.value.map((environment) => {
      return environment.id === nextEnvironment.id ? nextEnvironment : environment
    })
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  function schedulePolling() {
    stopPolling()
    if (!currentAttempt.value || !ACTIVE_SYNC_STATUSES.has(currentAttempt.value.status)) {
      return
    }
    pollTimer = setTimeout(() => {
      void refreshCurrentAttempt()
    }, POLL_INTERVAL_MS)
  }

  function trackAttempt(attempt: EnvironmentCatalogSyncAttempt) {
    currentAttempt.value = attempt
    attemptErrorMessage.value = ''
    if (catalogState.value) {
      catalogState.value = {
        ...catalogState.value,
        status: attempt.status,
        last_error_code: attempt.error_code,
        last_error_summary: attempt.error_summary,
      }
    }
    schedulePolling()
  }

  async function loadCatalog() {
    loading.value = true
    errorMessage.value = ''
    try {
      const response = await fetchEnvironmentCatalog()
      environments.value = response.data
      catalogState.value = response.catalog_state
    } catch (error) {
      errorMessage.value = toApiError(error).message
    } finally {
      loading.value = false
    }
  }

  async function refreshCurrentAttempt() {
    if (!currentAttempt.value) {
      return
    }
    try {
      const attempt = await fetchEnvironmentCatalogSyncAttempt(currentAttempt.value.id)
      currentAttempt.value = attempt
      attemptErrorMessage.value = ''
      if (ACTIVE_SYNC_STATUSES.has(attempt.status)) {
        schedulePolling()
      } else {
        stopPolling()
        void loadCatalog()
      }
    } catch (error) {
      // 轮询失败时保留已知状态，避免把已进入队列的用户反馈抹掉。
      attemptErrorMessage.value = toApiError(error).message
    }
  }

  async function applyWrite(write: Promise<EnvironmentCatalogWriteResult>) {
    submitting.value = true
    errorMessage.value = ''
    try {
      const result = await write
      replaceEnvironment(result.environment)
      trackAttempt(result.sync_attempt)
      return result
    } catch (error) {
      errorMessage.value = toApiError(error).message
      throw error
    } finally {
      submitting.value = false
    }
  }

  function createEnvironment(payload: CreateTestEnvironmentPayload) {
    return applyWrite(createTestEnvironment(payload))
  }

  function editEnvironment(environmentId: number, payload: UpdateTestEnvironmentPayload) {
    return applyWrite(updateTestEnvironment(environmentId, payload))
  }

  function deactivateEnvironment(environmentId: number) {
    return applyWrite(deactivateTestEnvironment(environmentId))
  }

  function restoreEnvironment(environmentId: number) {
    return editEnvironment(environmentId, { is_active: true })
  }

  async function importFromYaml() {
    submitting.value = true
    errorMessage.value = ''
    try {
      const attempt = await syncTestEnvironmentsFromYaml()
      trackAttempt(attempt)
      return attempt
    } catch (error) {
      errorMessage.value = toApiError(error).message
      throw error
    } finally {
      submitting.value = false
    }
  }

  async function retryAttempt() {
    if (!currentAttempt.value) {
      return
    }
    submitting.value = true
    attemptErrorMessage.value = ''
    try {
      const attempt = await retryEnvironmentCatalogSyncAttempt(currentAttempt.value.id)
      trackAttempt(attempt)
    } catch (error) {
      attemptErrorMessage.value = toApiError(error).message
      throw error
    } finally {
      submitting.value = false
    }
  }

  onScopeDispose(stopPolling)

  return {
    environments,
    catalogState,
    currentAttempt,
    loading,
    submitting,
    errorMessage,
    attemptErrorMessage,
    hasActiveAttempt,
    loadCatalog,
    refreshCurrentAttempt,
    createEnvironment,
    editEnvironment,
    deactivateEnvironment,
    restoreEnvironment,
    importFromYaml,
    retryAttempt,
  }
}
