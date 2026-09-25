import type { PaginatedResponse } from '@/types/api';
import { httpClient } from '@/services/api/http-client';

import type { ElectoralZoneMesh, MapBounds } from '@/components/maps/ElectoralZoneMeshes';
import type {
  DashboardData,
  MaterialRecord,
  PollingPlaceMapItem,
  PollingPlaceSectionItem,
  RouteDetail,
  RouteInput,
  RouteRecord,
  RouteTemplateDetail,
  RouteTemplateInput,
  RouteTemplateRecord,
  TeamRecord,
} from './types';

const base = '/api/v1/anuncios';

export async function listMaterials(includeInactive = false) {
  const { data } = await httpClient.get<PaginatedResponse<MaterialRecord>>(`${base}/materiais`, {
    params: { page_size: 100, order_by: 'nome', incluir_inativos: includeInactive },
  });
  return data;
}

export async function createMaterial(payload: { nome: string; descricao?: string }) {
  const { data } = await httpClient.post<MaterialRecord>(`${base}/materiais`, payload);
  return data;
}

export async function updateMaterial(
  id: number,
  payload: { nome?: string; descricao?: string; ativo?: boolean },
) {
  const { data } = await httpClient.patch<MaterialRecord>(`${base}/materiais/${id}`, payload);
  return data;
}

export async function deactivateMaterial(id: number) {
  await httpClient.delete(`${base}/materiais/${id}`);
}

export async function listTeams(includeInactive = false) {
  const { data } = await httpClient.get<PaginatedResponse<TeamRecord>>(`${base}/equipes`, {
    params: { page_size: 100, order_by: 'nome', incluir_inativos: includeInactive },
  });
  return data;
}

export interface TeamPayload {
  nome: string;
  descricao?: string;
  lideranca_id?: number;
  territorio_id?: number;
  usuario_ids: number[];
  ativo?: boolean;
}

export async function createTeam(payload: TeamPayload) {
  const { data } = await httpClient.post<TeamRecord>(`${base}/equipes`, payload);
  return data;
}

export async function updateTeam(id: number, payload: Partial<TeamPayload>) {
  const { data } = await httpClient.patch<TeamRecord>(`${base}/equipes/${id}`, payload);
  return data;
}

export async function deactivateTeam(id: number) {
  await httpClient.delete(`${base}/equipes/${id}`);
}

export async function listRoutes(params: Record<string, string | number | undefined>) {
  const { data } = await httpClient.get<PaginatedResponse<RouteRecord>>(`${base}/planejamentos`, {
    params: { ...params, page_size: 100 },
  });
  return data;
}

export async function getRoute(uuid: string) {
  const { data } = await httpClient.get<RouteDetail>(`${base}/planejamentos/${uuid}`);
  return data;
}

export async function createPlanning(payload: RouteInput) {
  const { data } = await httpClient.post<RouteDetail>(`${base}/planejamentos`, payload);
  return data;
}

export async function updateRoute(uuid: string, payload: Partial<RouteInput>) {
  const { data } = await httpClient.patch<RouteDetail>(`${base}/planejamentos/${uuid}`, payload);
  return data;
}

export async function listRouteTemplates(includeInactive = false) {
  const { data } = await httpClient.get<PaginatedResponse<RouteTemplateRecord>>(`${base}/rotas`, {
    params: { page_size: 100, order_by: 'nome', incluir_inativas: includeInactive },
  });
  return data;
}

export async function getRouteTemplate(uuid: string) {
  const { data } = await httpClient.get<RouteTemplateDetail>(`${base}/rotas/${uuid}`);
  return data;
}

export async function createRoute(payload: RouteTemplateInput) {
  const { data } = await httpClient.post<RouteTemplateDetail>(`${base}/rotas`, payload);
  return data;
}

export async function updateRouteTemplate(uuid: string, payload: Partial<RouteTemplateInput>) {
  const { data } = await httpClient.patch<RouteTemplateDetail>(`${base}/rotas/${uuid}`, payload);
  return data;
}

export async function getDashboard(params: Record<string, string | number | undefined>) {
  const { data } = await httpClient.get<DashboardData>(`${base}/dashboard`, { params });
  return data;
}

export async function exportOperationalData(
  filters: Record<string, string | number | undefined>,
  formato: 'csv' | 'xlsx',
) {
  const response = await httpClient.post<Blob>(
    `${base}/operacao/exportacoes`,
    { ...filters, formato },
    { responseType: 'blob', timeout: 60_000 },
  );
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  const now = new Date();
  const date = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-');
  anchor.href = url;
  anchor.download = `operacao-anuncios-${date}.${formato}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function listPollingPlacesForMap(bounds: MapBounds) {
  const { data } = await httpClient.get<PollingPlaceMapItem[]>(`${base}/mapa/locais-votacao`, {
    params: {
      sul: bounds.south,
      oeste: bounds.west,
      norte: bounds.north,
      leste: bounds.east,
    },
  });
  return data;
}

export async function listPollingPlaceSections(pollingPlaceId: number) {
  const { data } = await httpClient.get<PollingPlaceSectionItem[]>(
    `${base}/mapa/locais-votacao/${pollingPlaceId}/secoes`,
  );
  return data;
}

export async function listElectoralZoneMeshes(bounds: MapBounds) {
  const { data } = await httpClient.get<ElectoralZoneMesh[]>(`${base}/mapa/zonas-eleitorais`, {
    params: {
      sul: bounds.south,
      oeste: bounds.west,
      norte: bounds.north,
      leste: bounds.east,
    },
  });
  return data;
}
