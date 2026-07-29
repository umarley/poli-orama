import { httpClient } from '@/services/api/http-client';

import type {
  Campaign,
  CampaignClosure,
  CampaignClosureInput,
  CampaignInput,
  ContestedOffice,
  ElectionType,
  OfficialElection,
  OfficialElectionInput,
} from './types';

const base = '/api/v1/eleicoes';

export async function listOfficialElections(includeInactive = false) {
  const { data } = await httpClient.get<OfficialElection[]>(base, {
    params: { incluir_inativas: includeInactive },
  });
  return data;
}

export async function createOfficialElection(payload: OfficialElectionInput) {
  const { data } = await httpClient.post<OfficialElection>(base, payload);
  return data;
}

export async function updateOfficialElection(id: number, payload: Partial<OfficialElectionInput>) {
  const { data } = await httpClient.patch<OfficialElection>(`${base}/${id}`, payload);
  return data;
}

export async function listContestedOffices(type: ElectionType) {
  const { data } = await httpClient.get<ContestedOffice[]>(`${base}/cargos`, {
    params: { tipo: type },
  });
  return data;
}

export async function listCampaigns() {
  const { data } = await httpClient.get<Campaign[]>(`${base}/campanhas`);
  return data;
}

export async function getCurrentCampaign() {
  const { data } = await httpClient.get<Campaign | null>(`${base}/campanhas/atual`);
  return data;
}

export async function createCampaign(payload: CampaignInput) {
  const { data } = await httpClient.post<Campaign>(`${base}/campanhas`, payload);
  return data;
}

export async function updateCampaign(
  id: number,
  payload: Pick<CampaignInput, 'nome' | 'cargo_pleiteado_id'>,
) {
  const { data } = await httpClient.patch<Campaign>(`${base}/campanhas/${id}`, payload);
  return data;
}

export async function activateCampaign(id: number) {
  const { data } = await httpClient.post<Campaign>(`${base}/campanhas/${id}/ativar`);
  return data;
}

export async function getActiveCampaignClosure() {
  const { data } = await httpClient.get<CampaignClosure | null>(
    `${base}/campanha-ativa/encerramento`,
  );
  return data;
}

export async function requestActiveCampaignClosure(payload: CampaignClosureInput) {
  const { data } = await httpClient.post<CampaignClosure>(
    `${base}/campanha-ativa/encerramento`,
    payload,
  );
  return data;
}

export async function retryActiveCampaignClosure() {
  const { data } = await httpClient.post<CampaignClosure>(
    `${base}/campanha-ativa/encerramento/reprocessar`,
  );
  return data;
}
