import { httpClient } from '@/services/api/http-client';

import type { CampaignContract, ContractInput, PersonOption } from './types';

const base = '/api/v1/contratos';

export async function listContracts(params?: {
  q?: string;
  tipo_contratado?: string;
  situacao?: string;
}) {
  return (await httpClient.get<CampaignContract[]>(base, { params })).data;
}

export async function searchContractPeople(query: string) {
  return (await httpClient.get<PersonOption[]>(`${base}/pessoas`, { params: { q: query } })).data;
}

export async function createContract(payload: ContractInput) {
  return (await httpClient.post<CampaignContract>(base, payload)).data;
}

export async function updateContract(id: number, payload: Partial<ContractInput>) {
  return (await httpClient.patch<CampaignContract>(`${base}/${id}`, payload)).data;
}

export async function deleteContract(id: number) {
  await httpClient.delete(`${base}/${id}`);
}
