import { httpClient } from '@/services/api/http-client';

import type {
  AuthenticationResponse,
  AuthUser,
  LoginInput,
  MfaSetup,
  TenantSwitchInput,
  UserSession,
} from './types';

export async function login(payload: LoginInput): Promise<AuthenticationResponse> {
  const { data } = await httpClient.post<AuthenticationResponse>('/api/v1/auth/login', payload);
  return data;
}

export async function logout(): Promise<void> {
  await httpClient.post('/api/v1/auth/logout');
}

export async function switchTenant(payload: TenantSwitchInput): Promise<AuthenticationResponse> {
  const { data } = await httpClient.post<AuthenticationResponse>(
    '/api/v1/auth/switch-tenant',
    payload,
  );
  return data;
}

export async function getCurrentUser(): Promise<AuthUser> {
  const { data } = await httpClient.get<AuthUser>('/api/v1/auth/me');
  return data;
}

export async function changePassword(senha_atual: string, nova_senha: string): Promise<void> {
  await httpClient.post('/api/v1/auth/change-password', { senha_atual, nova_senha });
}

export async function setupMfa(senha: string): Promise<MfaSetup> {
  const { data } = await httpClient.post<MfaSetup>('/api/v1/auth/mfa/setup', { senha });
  return data;
}

export async function confirmMfa(codigo: string): Promise<void> {
  await httpClient.post('/api/v1/auth/mfa/confirm', { codigo });
}

export async function disableMfa(senha: string, codigo: string): Promise<void> {
  await httpClient.post('/api/v1/auth/mfa/disable', { senha, codigo });
}

export async function listSessions(): Promise<UserSession[]> {
  const { data } = await httpClient.get<UserSession[]>('/api/v1/auth/sessions');
  return data;
}

export async function revokeSession(id: number): Promise<boolean> {
  const { data } = await httpClient.delete<{ current_session: boolean }>(
    `/api/v1/auth/sessions/${id}`,
  );
  return data.current_session;
}
