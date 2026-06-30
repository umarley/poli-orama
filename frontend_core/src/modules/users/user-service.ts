import { httpClient } from '@/services/api/http-client';
import type { PaginatedResponse } from '@/types/api';

import type {
  ProfileRecord,
  TerritorialAccessInput,
  UserCreateInput,
  UserRecord,
  UserUpdateInput,
} from './types';

export async function listUsers(filters: {
  query?: string;
  status?: string;
}): Promise<PaginatedResponse<UserRecord>> {
  const { data } = await httpClient.get<PaginatedResponse<UserRecord>>('/api/v1/users', {
    params: { ...filters, page_size: 100, order_by: 'nome' },
  });
  return data;
}

export async function listProfiles(): Promise<ProfileRecord[]> {
  const { data } = await httpClient.get<ProfileRecord[]>('/api/v1/users/profiles');
  return data;
}

export async function createUser(payload: UserCreateInput): Promise<UserRecord> {
  const { data } = await httpClient.post<UserRecord>('/api/v1/users', payload);
  return data;
}

export async function updateUser(id: number, payload: UserUpdateInput): Promise<UserRecord> {
  const { data } = await httpClient.patch<UserRecord>(`/api/v1/users/${id}`, payload);
  return data;
}

export async function deleteUser(id: number): Promise<void> {
  await httpClient.delete(`/api/v1/users/${id}`);
}

export async function resetUserPassword(id: number): Promise<string> {
  const { data } = await httpClient.post<{ senha_temporaria: string }>(
    `/api/v1/users/${id}/reset-password`,
    {},
  );
  return data.senha_temporaria;
}

export async function replaceTerritorialAccess(
  id: number,
  accesses: TerritorialAccessInput[],
): Promise<UserRecord['acessos_territoriais']> {
  const { data } = await httpClient.put<UserRecord['acessos_territoriais']>(
    `/api/v1/users/${id}/territorial-access`,
    { acessos: accesses },
  );
  return data;
}
