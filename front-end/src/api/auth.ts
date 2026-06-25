/**
 * 认证 API 封装模块。
 * 本模块对接后端 `/api/auth/` 接口，提供登录、登出和当前用户查询能力。
 */

import { http } from './http';

/** 平台用户角色。 */
export type UserRole = 'admin' | 'member';

/** 前端展示和权限判断需要的用户基础信息。 */
export interface PlatformUser {
  id: number;
  username: string;
  role: UserRole;
}

/** 登录接口响应结构。 */
export interface LoginResponse {
  token: string;
  user: PlatformUser;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  /**
   * 调用后端登录接口。
   * Args:
   *   username: 登录用户名。
   *   password: 登录密码。
   * Returns:
   *   Promise<LoginResponse>: DRF Token 和当前用户信息。
   */
  const response = await http.post<LoginResponse>('/auth/login/', {
    username,
    password,
  });

  return response.data;
}

export async function logout(): Promise<void> {
  /** 调用后端登出接口，使当前 Token 失效。 */
  await http.post('/auth/logout/');
}

export async function getCurrentUser(): Promise<PlatformUser> {
  /** 查询当前 Token 对应的用户信息。 */
  const response = await http.get<PlatformUser>('/auth/me/');
  return response.data;
}
