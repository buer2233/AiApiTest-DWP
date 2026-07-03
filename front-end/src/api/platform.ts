import { http } from './client'
import type { InvitationSummary, PaginationMeta, UserRole, UserSummary } from '@/types/api'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  invitation_code: string
  username: string
  display_name?: string
  password: string
  confirm_password: string
}

export interface InvitationCreateRequest {
  role: UserRole
  expires_at?: string
}

export interface InvitationCreateResponse extends InvitationSummary {
  plain_code: string
}

export async function login(payload: LoginRequest): Promise<UserSummary> {
  const response = await http.post<{ data: UserSummary }>('/auth/login', payload)
  return response.data.data
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout')
}

export async function fetchMe(): Promise<UserSummary> {
  const response = await http.get<{ data: UserSummary }>('/auth/me')
  return response.data.data
}

export async function register(payload: RegisterRequest): Promise<UserSummary> {
  const response = await http.post<{ data: UserSummary }>('/auth/register', payload)
  return response.data.data
}

export async function fetchUsers(params: { role?: UserRole; page?: number; per_page?: number } = {}) {
  const response = await http.get<{ data: UserSummary[]; meta: PaginationMeta }>('/users', { params })
  return response.data
}

export async function fetchInvitations(params: { status?: string; role?: UserRole; page?: number; per_page?: number } = {}) {
  const response = await http.get<{ data: InvitationSummary[]; meta: PaginationMeta }>('/invitations', { params })
  return response.data
}

export async function createInvitation(payload: InvitationCreateRequest): Promise<InvitationCreateResponse> {
  const response = await http.post<{ data: InvitationCreateResponse }>('/invitations', payload)
  return response.data.data
}

export async function revokeInvitation(invitationId: number): Promise<InvitationSummary> {
  const response = await http.post<{ data: InvitationSummary }>(`/invitations/${invitationId}/revoke`)
  return response.data.data
}
