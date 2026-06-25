/**
 * Axios HTTP 客户端模块。
 * 本模块统一设置后端 API baseURL、超时时间和 DRF Token 认证请求头。
 */

import axios from 'axios';

import { useAuthStore } from '@/stores/auth';

/**
 * 平台 API 客户端。
 * Vite 开发环境默认通过 `/api` 代理到 DRF 后端，生产环境可通过 VITE_API_BASE_URL 覆盖。
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 15000,
});

http.interceptors.request.use((config) => {
  // 每次请求前读取 Pinia 登录态，确保刷新 token 后请求头使用最新值。
  const auth = useAuthStore();

  if (auth.token) {
    config.headers.Authorization = `Token ${auth.token}`;
  }

  return config;
});
