import axios from 'axios';

import { env } from '@/config/env';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

export const httpClient = axios.create({
  baseURL: env.apiUrl,
  timeout: 15_000,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
});

httpClient.interceptors.request.use((config) => {
  const token = useSessionStore.getState().accessToken;
  const tenant = useSessionStore.getState().tenant;
  const currentCampaign = useSessionStore.getState().currentCampaign;

  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (tenant) config.headers['X-Tenant-ID'] = tenant.id;
  if (currentCampaign) config.headers['X-Campaign-ID'] = currentCampaign.id;

  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const normalizedError = normalizeApiError(error);

    if (normalizedError.status === 401) {
      useSessionStore.getState().clearSession();
    }

    return Promise.reject(normalizedError);
  },
);
