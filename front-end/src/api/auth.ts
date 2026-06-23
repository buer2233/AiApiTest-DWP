import { http } from './http';

export type UserRole = 'admin' | 'member';

export interface PlatformUser {
  id: number;
  username: string;
  role: UserRole;
}

export interface LoginResponse {
  token: string;
  user: PlatformUser;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await http.post<LoginResponse>('/auth/login/', {
    username,
    password,
  });

  return response.data;
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout/');
}

export async function getCurrentUser(): Promise<PlatformUser> {
  const response = await http.get<PlatformUser>('/auth/me/');
  return response.data;
}
