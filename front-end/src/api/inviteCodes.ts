import { http, type ApiResponse, type PaginationMeta } from './http'

export interface InviteCode {
  id: number
  code: string
  status: 'active' | 'disabled' | 'exhausted' | 'expired'
  max_uses: number
  used_count: number
  expires_at: string | null
  created_by: {
    id: number
    username: string
  }
  created_at: string
}

export interface InviteCodeCreatePayload {
  code: string
  max_uses: number
  expires_at?: string | null
}

export interface InviteCodeListParams {
  keyword?: string
  status?: string
  page?: number
  page_size?: number
}

export async function listInviteCodes(params: InviteCodeListParams = {}) {
  const response = await http.get<ApiResponse<InviteCode[]>>('/api/v1/invite-codes', { params })
  return {
    data: response.data.data,
    meta: response.data.meta as PaginationMeta,
  }
}

export async function createInviteCode(payload: InviteCodeCreatePayload) {
  const response = await http.post<ApiResponse<InviteCode>>('/api/v1/invite-codes', payload)
  return response.data.data
}

export async function disableInviteCode(id: number) {
  const response = await http.post<ApiResponse<InviteCode>>(`/api/v1/invite-codes/${id}/disable`)
  return response.data.data
}
