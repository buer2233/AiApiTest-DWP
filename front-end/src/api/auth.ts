import http from "./http";
import type { ApiSuccess, LoginResult, User } from "@/types";

// 认证相关 API（对应后端 /api/auth/*）。

export async function login(username: string, password: string): Promise<LoginResult> {
  const { data } = await http.post<ApiSuccess<LoginResult>>("/api/auth/login/", {
    username,
    password,
  });
  return data.data;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await http.post<ApiSuccess<User>>("/api/auth/register/", payload);
  return data.data;
}

export async function logout(): Promise<void> {
  await http.post("/api/auth/logout/");
}

export async function fetchMe(): Promise<User> {
  const { data } = await http.get<ApiSuccess<User>>("/api/auth/me/");
  return data.data;
}
