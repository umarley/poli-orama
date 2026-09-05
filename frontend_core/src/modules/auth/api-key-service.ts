import { httpClient } from '@/services/api/http-client';
import type { PaginatedResponse } from '@/types/api';

import type { ApiKeyCreated, ApiKeyInput, ApiKeyRecord } from './api-key-types';

export async function listApiKeys(filters: {
  query?: string;
  tenant_id?: number;
}): Promise<PaginatedResponse<ApiKeyRecord>> {
  const { data } = await httpClient.get<PaginatedResponse<ApiKeyRecord>>('/api/v1/admin/api-keys', {
    params: { ...filters, page_size: 100, order_by: 'id' },
  });
  return data;
}

export async function createApiKey(payload: ApiKeyInput): Promise<ApiKeyCreated> {
  const { data } = await httpClient.post<ApiKeyCreated>('/api/v1/admin/api-keys', payload);
  return data;
}

export async function revokeApiKey(id: number): Promise<ApiKeyRecord> {
  const { data } = await httpClient.post<ApiKeyRecord>(`/api/v1/admin/api-keys/${id}/revogar`);
  return data;
}
