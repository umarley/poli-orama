import { httpClient } from '@/services/api/http-client';
import type {
  Demand,
  DemandCatalog,
  DemandCatalogKey,
  DemandDetail,
  DemandFilters,
  DemandClassification,
  DemandInput,
  DemandResponsible,
  DemandSummary,
} from './types';

const base = '/api/v1/demandas';

export async function listDemandCatalog(key: DemandCatalogKey) {
  return (await httpClient.get<DemandCatalog[]>(`${base}/catalogos/${key}`)).data;
}
export async function listDemands(filters: DemandFilters = {}) {
  return (await httpClient.get<Demand[]>(base, { params: filters })).data;
}
export async function createDemand(payload: DemandInput) {
  return (await httpClient.post<Demand>(base, payload)).data;
}
export async function getDemand(id: number) {
  return (await httpClient.get<DemandDetail>(`${base}/${id}`)).data;
}
export async function updateDemand(id: number, payload: Record<string, unknown>) {
  return (await httpClient.patch<Demand>(`${base}/${id}`, payload)).data;
}
export async function changeDemandStatus(
  id: number,
  payload: { status_demanda_id: number; resultado_atendimento_id?: number; observacao: string },
) {
  return (await httpClient.post<Demand>(`${base}/${id}/status`, payload)).data;
}
export async function addDemandAttendance(id: number, payload: Record<string, unknown>) {
  return (await httpClient.post(`${base}/${id}/atendimentos`, payload)).data;
}
export async function listDemandResponsibles() {
  return (await httpClient.get<DemandResponsible[]>(`${base}/responsaveis`)).data;
}
export async function getDemandSummary() {
  return (await httpClient.get<DemandSummary>(`${base}/resumo`)).data;
}
export async function classifyDemand(descricao: string) {
  return (await httpClient.post<DemandClassification>(`${base}/classificar`, { descricao })).data;
}
export async function downloadDemands(
  filters: DemandFilters,
  finalidade = 'Acompanhamento operacional de demandas',
) {
  const { data } = await httpClient.get<Blob>(`${base}/exportar.csv`, {
    params: { ...filters, finalidade },
    responseType: 'blob',
  });
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'demandas.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}
