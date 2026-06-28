import axios from 'axios'

export interface ApiResponse<T> {
  data: T
  meta?: PaginationMeta
}

export interface ApiErrorPayload {
  error?: {
    code: string
    message: string
    details?: unknown
  }
}

export interface PaginationMeta {
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const http = axios.create({
  // 使用相对 API 路径，容器化部署时由网关或 Vite proxy 解析到后端服务。
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 15_000,
})

http.interceptors.request.use((config) => {
  const token = window.localStorage.getItem('aiapitest_token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError<ApiErrorPayload>(error) && error.response?.status === 401) {
      window.localStorage.removeItem('aiapitest_token')
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
      if (!['/login', '/register'].includes(window.location.pathname)) {
        const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
        window.location.assign(`/login?redirect=${redirect}`)
      }
    }
    return Promise.reject(error)
  },
)

export function getApiErrorMessage(error: unknown, fallback = '请求失败，请稍后重试') {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    return error.response?.data?.error?.message || fallback
  }
  return fallback
}

export function getApiFieldErrors(error: unknown) {
  const fieldErrors: Record<string, string> = {}
  if (!axios.isAxiosError<ApiErrorPayload>(error)) {
    return fieldErrors
  }
  const details = error.response?.data?.error?.details
  if (!Array.isArray(details)) {
    return fieldErrors
  }
  for (const detail of details) {
    if (detail && typeof detail === 'object' && 'field' in detail && 'message' in detail) {
      const field = String(detail.field)
      const message = Array.isArray(detail.message) ? detail.message.join('；') : String(detail.message)
      fieldErrors[field] = message
    }
  }
  return fieldErrors
}
