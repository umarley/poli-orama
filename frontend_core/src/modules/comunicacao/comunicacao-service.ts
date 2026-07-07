import { httpClient } from '@/services/api/http-client';

import type { CatalogoComunicacao, InteracaoInput, InteracaoPessoa } from './types';

const base = '/api/v1/comunicacao';

export async function listarTiposInteracao() {
  const { data } = await httpClient.get<CatalogoComunicacao[]>(`${base}/tipos-interacao`);
  return data;
}

export async function listarCanaisComunicacao() {
  const { data } = await httpClient.get<CatalogoComunicacao[]>(`${base}/canais`);
  return data;
}

export async function listarInteracoesPessoa(pessoaId: number) {
  const { data } = await httpClient.get<InteracaoPessoa[]>(
    `${base}/pessoas/${pessoaId}/interacoes`,
  );
  return data;
}

export async function registrarInteracaoPessoa(pessoaId: number, payload: InteracaoInput) {
  const { data } = await httpClient.post<InteracaoPessoa>(
    `${base}/pessoas/${pessoaId}/interacoes`,
    payload,
  );
  return data;
}
