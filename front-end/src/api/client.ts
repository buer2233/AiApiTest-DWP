import axios, { AxiosError } from 'axios'

import { resolveApiTimeoutMs } from './env'
import type { ApiErrorPayload } from '@/types/api'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  withCredentials: true,
  timeout: resolveApiTimeoutMs(import.meta.env.VITE_API_TIMEOUT_MS),
})

export class ApiClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

export function toApiError(error: unknown): ApiClientError {
  if (error instanceof ApiClientError) {
    return error
  }
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorPayload>
    const payload = axiosError.response?.data?.error
    return new ApiClientError(
      payload?.code || 'network_error',
      payload?.message || '请求失败，请稍后重试。',
      axiosError.response?.status || 0,
    )
  }
  return new ApiClientError('unknown_error', '请求失败，请稍后重试。', 0)
}
