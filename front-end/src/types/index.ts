// 与后端 §7 API 契约对应的前端类型定义。
export type UserRole = "admin" | "member";
export type UserStatus = "pending" | "active" | "disabled";

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  date_joined?: string;
  last_login?: string | null;
}

export interface ApiSuccess<T> {
  code: 0;
  message: string;
  data: T;
}

export interface ApiErrorBody {
  code: number;
  message: string;
  errors?: Record<string, unknown>;
}

export interface LoginResult {
  token: string;
  user: User;
}

export interface TestCase {
  id: number;
  module_key: string;
  module_name: string;
  case_path: string;
  node_id: string;
  function_name: string;
  class_name: string | null;
  case_title: string;
  story: string;
  severity: string;
  is_active: boolean;
  synced_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface SyncResult {
  scanned: number;
  created: number;
  updated: number;
  deactivated: number;
  synced_at: string;
}
