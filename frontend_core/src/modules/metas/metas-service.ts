import { httpClient } from '@/services/api/http-client';

import type {
  Goal,
  GoalDetail,
  GoalInput,
  GoalPeriod,
  GoalStatus,
  GoalSummary,
  GoalTracking,
  GoalType,
  LeadershipRanking,
  TargetOption,
  TargetType,
} from './types';

const base = '/api/v1/metas';

export async function listarMetas(filters?: {
  territorio_id?: number;
  lideranca_id?: number;
  periodo_id?: number;
  status?: GoalStatus;
}) {
  const { data } = await httpClient.get<Goal[]>(base, { params: filters });
  return data;
}

export async function obterMeta(id: number) {
  const { data } = await httpClient.get<GoalDetail>(`${base}/${id}`);
  return data;
}

export async function criarMeta(payload: GoalInput) {
  const { data } = await httpClient.post<GoalDetail>(base, payload);
  return data;
}

export async function atualizarMeta(id: number, payload: Partial<GoalInput>) {
  const { data } = await httpClient.patch<GoalDetail>(`${base}/${id}`, payload);
  return data;
}

export async function cancelarMeta(id: number) {
  await httpClient.delete(`${base}/${id}`);
}

export async function registrarAcompanhamento(
  id: number,
  payload: {
    data_referencia: string;
    quantidade_projetada?: number;
    quantidade_confirmada?: number;
    observacao?: string;
  },
) {
  const { data } = await httpClient.post<GoalTracking>(
    `${base}/${id}/acompanhamentos`,
    payload,
  );
  return data;
}

export async function obterResumoMetas(filters?: {
  territorio_id?: number;
  lideranca_id?: number;
  periodo_id?: number;
  status?: GoalStatus;
}) {
  const { data } = await httpClient.get<GoalSummary>(`${base}/resumo`, {
    params: filters,
  });
  return data;
}

export async function listarRanking() {
  const { data } = await httpClient.get<LeadershipRanking[]>(`${base}/ranking`);
  return data;
}

export async function recalcularRanking() {
  const { data } = await httpClient.post<LeadershipRanking[]>(
    `${base}/ranking/recalcular`,
  );
  return data;
}

export async function listarTiposMeta(incluirInativos = false) {
  const { data } = await httpClient.get<GoalType[]>(`${base}/tipos`, {
    params: { incluir_inativos: incluirInativos },
  });
  return data;
}

export async function criarTipoMeta(payload: {
  codigo: string;
  nome: string;
  descricao?: string;
}) {
  const { data } = await httpClient.post<GoalType>(`${base}/tipos`, payload);
  return data;
}

export async function listarPeriodos(incluirInativos = false) {
  const { data } = await httpClient.get<GoalPeriod[]>(`${base}/periodos`, {
    params: { incluir_inativos: incluirInativos },
  });
  return data;
}

export async function criarPeriodo(payload: {
  nome: string;
  data_inicio: string;
  data_fim: string;
  ciclo?: string;
}) {
  const { data } = await httpClient.post<GoalPeriod>(`${base}/periodos`, payload);
  return data;
}

export async function listarOpcoesAlvo(tipo: TargetType, query?: string) {
  const { data } = await httpClient.get<TargetOption[]>(`${base}/alvos/opcoes`, {
    params: { tipo, query },
  });
  return data;
}
