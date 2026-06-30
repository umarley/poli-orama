import axios from 'axios';

import { env } from '@/config/env';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import type { Tenant } from '@/stores/session-store';

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
  const user = useSessionStore.getState().user;

  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (tenant) config.headers['X-Tenant-ID'] = tenant.id;
  if (user) {
    config.headers['X-User-ID'] = user.id === 'usr-demo' ? '1' : user.id;
    config.headers['X-User-Role'] = user.role;
  }
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
    if (normalizedError.code === 'tenant_inactive') {
      const current = useSessionStore.getState().tenant;
      const details = normalizedError.details as { tenant_status?: Tenant['status'] } | undefined;
      if (current && details?.tenant_status) {
        useSessionStore.getState().setTenant({ ...current, status: details.tenant_status });
      }
    }

    return Promise.reject(normalizedError);
  },
);
