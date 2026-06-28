import { http, type ApiResponse } from './http'

export interface PlatformUser {
  id: number
  username: string
  email: string
  role: 'admin' | 'member'
  status: 'active' | 'pending' | 'disabled'
}

export interface LoginPayload {
  account: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
  password_confirm: string
  invite_code: string
}

export interface LoginResult {
  token: string
  user: PlatformUser
}

export async function login(payload: LoginPayload) {
  const response = await http.post<ApiResponse<LoginResult>>('/api/v1/auth/login', payload)
  return response.data.data
}

export async function register(payload: RegisterPayload) {
  const response = await http.post<ApiResponse<PlatformUser>>('/api/v1/auth/register', payload)
  return response.data.data
}

export async function fetchMe() {
  const response = await http.get<ApiResponse<PlatformUser>>('/api/v1/auth/me')
  return response.data.data
}

export async function logout() {
  await http.post('/api/v1/auth/logout')
}
