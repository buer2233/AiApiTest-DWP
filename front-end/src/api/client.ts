import axios, { AxiosError } from 'axios'

import type { ApiErrorPayload } from '@/types/api'

export const API_BASE_PATH = '/api/v1'
export const API_TIMEOUT_MS = 10000

export const http = axios.create({
  baseURL: API_BASE_PATH,
  withCredentials: true,
  timeout: API_TIMEOUT_MS,
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
