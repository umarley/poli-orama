import { httpClient } from '@/services/api/http-client';
import type { PaginatedResponse } from '@/types/api';

import type { Plan, PlanUsage, TenantConfiguration, TenantInput, TenantRecord } from './types';

export async function listPlans(): Promise<Plan[]> {
  const { data } = await httpClient.get<Plan[]>('/api/public/planos');
  return data;
}

export async function listTenants(filters: {
  query?: string;
  status?: string;
  plano_id?: number;
}): Promise<PaginatedResponse<TenantRecord>> {
  const { data } = await httpClient.get<PaginatedResponse<TenantRecord>>('/api/v1/tenants', {
    params: { ...filters, page_size: 100, order_by: 'nome' },
  });
  return data;
}

export async function createTenant(payload: TenantInput): Promise<TenantRecord> {
  const { data } = await httpClient.post<TenantRecord>('/api/v1/tenants', payload);
  return data;
}

export async function updateTenant(id: number, payload: TenantInput): Promise<TenantRecord> {
  const { data } = await httpClient.patch<TenantRecord>(`/api/v1/tenants/${id}`, payload);
  return data;
}

export async function activateTenant(id: number): Promise<TenantRecord> {
  const { data } = await httpClient.post<TenantRecord>(`/api/v1/tenants/${id}/ativar`);
  return data;
}

export async function getCurrentTenant(): Promise<TenantRecord> {
  const { data } = await httpClient.get<TenantRecord>('/api/v1/me/tenant');
  return data;
}

export async function getTenantConfiguration(): Promise<TenantConfiguration> {
  const { data } = await httpClient.get<TenantConfiguration>('/api/v1/me/tenant/configuracao');
  return data;
}

export async function updateTenantConfiguration(
  payload: Partial<TenantConfiguration>,
): Promise<TenantConfiguration> {
  const { data } = await httpClient.patch<TenantConfiguration>(
    '/api/v1/me/tenant/configuracao',
    payload,
  );
  return data;
}

export async function uploadTenantLogo(file: File): Promise<TenantConfiguration> {
  const body = new FormData();
  body.append('arquivo', file);
  const { data } = await httpClient.post<TenantConfiguration>(
    '/api/v1/me/tenant/configuracao/logo',
    body,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

export async function getTenantLogoBlob(url: string): Promise<Blob> {
  const { data } = await httpClient.get<Blob>(url, { responseType: 'blob' });
  return data;
}

export async function getPlanUsage(): Promise<PlanUsage> {
  const { data } = await httpClient.get<PlanUsage>('/api/v1/me/tenant/assinatura');
  return data;
}
