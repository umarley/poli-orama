import axios from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';

import { env } from '@/config/env';
import type { AuthenticationResponse } from '@/modules/auth/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import type { Tenant } from '@/stores/session-store';

interface RetryableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export const httpClient = axios.create({
  baseURL: env.apiUrl,
  timeout: 15_000,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const session = useSessionStore.getState();
    if (!session.refreshToken) throw new Error('Sessão sem refresh token.');
    const { data } = await axios.post<AuthenticationResponse>(
      `${env.apiUrl}/api/v1/auth/refresh`,
      { refresh_token: session.refreshToken },
      { timeout: 15_000, headers: { 'Content-Type': 'application/json' } },
    );
    useSessionStore
      .getState()
      .updateAuthentication(data.usuario, data.access_token, data.refresh_token, data.expires_in);
    return data.access_token;
  })().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

httpClient.interceptors.request.use(async (config) => {
  const session = useSessionStore.getState();
  let token = session.accessToken;
  const isAuthenticationRequest =
    config.url?.includes('/auth/login') || config.url?.includes('/auth/refresh');
  if (
    !isAuthenticationRequest &&
    session.refreshToken &&
    session.accessTokenExpiresAt &&
    session.accessTokenExpiresAt <= Date.now() + 10_000
  ) {
    try {
      token = await refreshAccessToken();
    } catch {
      session.clearSession();
      token = null;
    }
  }
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (session.currentCampaign) {
    config.headers['X-Campaign-ID'] = session.currentCampaign.id;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    const normalizedError = normalizeApiError(error);
    const request = axios.isAxiosError(error)
      ? (error.config as RetryableRequest | undefined)
      : null;
    const canRefresh =
      normalizedError.status === 401 &&
      request &&
      !request._retry &&
      !request.url?.includes('/auth/login') &&
      !request.url?.includes('/auth/refresh') &&
      Boolean(useSessionStore.getState().refreshToken);

    if (canRefresh) {
      request._retry = true;
      try {
        const token = await refreshAccessToken();
        request.headers.Authorization = `Bearer ${token}`;
        return await httpClient.request(request);
      } catch {
        useSessionStore.getState().clearSession();
      }
    } else if (normalizedError.status === 401) {
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
