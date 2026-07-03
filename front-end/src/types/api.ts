export type UserRole = 'admin' | 'member'

export interface UserSummary {
  id: number
  username: string
  display_name: string
  role: UserRole
  permissions: string[]
  created_at?: string
  last_login_at?: string | null
}

export interface PaginationMeta {
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface InvitationSummary {
  id: number
  role: UserRole
  status: 'unused' | 'used' | 'revoked' | 'expired'
  expires_at: string
  created_by: string
  used_by: string | null
  used_at: string | null
  revoked_at: string | null
  created_at: string
}

export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    details: unknown[]
  }
}
