import axios from 'axios';

import { useAuthStore } from '@/stores/auth';

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 15000,
});

http.interceptors.request.use((config) => {
  const auth = useAuthStore();

  if (auth.token) {
    config.headers.Authorization = `Token ${auth.token}`;
  }

  return config;
});
