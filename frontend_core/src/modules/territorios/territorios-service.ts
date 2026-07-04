import { httpClient } from '@/services/api/http-client';

import type {
  Bairro,
  Estado,
  LocalVotacao,
  MapMarker,
  Municipio,
  SecaoEleitoral,
  Territorio,
  TerritorioInput,
  TerritorioTreeNode,
  TipoTerritorio,
  ZonaEleitoral,
} from './types';

const base = '/api/v1';

export async function listarEstados() {
  const { data } = await httpClient.get<Estado[]>(`${base}/global/estados`);
  return data;
}

export async function listarMunicipios(estadoId?: number, nome?: string) {
  const { data } = await httpClient.get<Municipio[]>(`${base}/global/municipios`, {
    params: { estado_id: estadoId, nome },
  });
  return data;
}

export async function listarBairros(municipioId: number, nome?: string) {
  const { data } = await httpClient.get<Bairro[]>(`${base}/global/bairros`, {
    params: { municipio_id: municipioId, nome },
  });
  return data;
}

export async function listarZonas(estadoId?: number, municipioId?: number) {
  const { data } = await httpClient.get<ZonaEleitoral[]>(
    `${base}/global/zonas-eleitorais`,
    { params: { estado_id: estadoId, municipio_id: municipioId } },
  );
  return data;
}

export async function listarLocaisVotacao(params: {
  municipio_id?: number;
  bairro_id?: number;
  zona_eleitoral_id?: number;
  nome?: string;
}) {
  const { data } = await httpClient.get<LocalVotacao[]>(
    `${base}/global/locais-votacao`,
    { params },
  );
  return data;
}

export async function listarSecoes(zonaEleitoralId: number, localVotacaoId?: number) {
  const { data } = await httpClient.get<SecaoEleitoral[]>(
    `${base}/global/secoes-eleitorais`,
    { params: { zona_eleitoral_id: zonaEleitoralId, local_votacao_id: localVotacaoId } },
  );
  return data;
}

export async function listarTiposTerritorio(incluirInativos = false) {
  const { data } = await httpClient.get<TipoTerritorio[]>(`${base}/territorios/tipos`, {
    params: { incluir_inativos: incluirInativos },
  });
  return data;
}

export async function criarTipoTerritorio(payload: {
  codigo: string;
  nome: string;
  descricao?: string;
}) {
  const { data } = await httpClient.post<TipoTerritorio>(
    `${base}/territorios/tipos`,
    payload,
  );
  return data;
}

export async function listarTerritorios(incluirInativos = false) {
  const { data } = await httpClient.get<Territorio[]>(`${base}/territorios`, {
    params: { incluir_inativos: incluirInativos },
  });
  return data;
}

export async function listarArvoreTerritorial() {
  const { data } = await httpClient.get<TerritorioTreeNode[]>(
    `${base}/territorios/arvore`,
  );
  return data;
}

export async function criarTerritorio(payload: TerritorioInput) {
  const { data } = await httpClient.post<Territorio>(`${base}/territorios`, payload);
  return data;
}

export async function atualizarTerritorio(id: number, payload: Partial<TerritorioInput>) {
  const { data } = await httpClient.patch<Territorio>(
    `${base}/territorios/${id}`,
    payload,
  );
  return data;
}

export async function inativarTerritorio(id: number) {
  await httpClient.delete(`${base}/territorios/${id}`);
}

export async function vincularLideranca(
  territorioId: number,
  liderancaId: number,
  responsabilidade: 'principal' | 'apoio' | 'compartilhada',
) {
  await httpClient.post(`${base}/territorios/${territorioId}/liderancas`, {
    lideranca_id: liderancaId,
    responsabilidade,
  });
}

export async function obterMarcadores(territorioId?: number) {
  const { data } = await httpClient.get<MapMarker[]>(
    `${base}/territorios/mapa/marcadores`,
    { params: { territorio_id: territorioId } },
  );
  return data;
}
