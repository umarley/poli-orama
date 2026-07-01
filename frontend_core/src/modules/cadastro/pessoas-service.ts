import { httpClient } from '@/services/api/http-client';
import type { PaginatedResponse } from '@/types/api';

import type {
  BuscaRapidaItem,
  Comunidade,
  Hierarquia,
  IndicacaoGraph,
  IndicacaoGraphFilters,
  Lideranca,
  NucleoFamiliar,
  PessoaCreateInput,
  PessoaDetalhe,
  PessoaFilters,
  PessoaListItem,
  PessoaTipo,
  TagCadastro,
  ValidacaoCadastro,
} from './types';

const base = '/api/v1/cadastro';

export async function listarPessoas(filters: PessoaFilters) {
  const { data } = await httpClient.get<PaginatedResponse<PessoaListItem>>(`${base}/pessoas`, {
    params: filters,
  });
  return data;
}

export async function obterPessoa(id: number) {
  const { data } = await httpClient.get<PessoaDetalhe>(`${base}/pessoas/${id}`);
  return data;
}

export async function criarPessoa(payload: PessoaCreateInput) {
  const { data } = await httpClient.post<PessoaDetalhe>(`${base}/pessoas`, payload);
  return data;
}

export async function atualizarPessoa(id: number, payload: Partial<PessoaCreateInput>) {
  const { data } = await httpClient.patch<PessoaDetalhe>(`${base}/pessoas/${id}`, payload);
  return data;
}

export async function inativarPessoa(id: number) {
  await httpClient.delete(`${base}/pessoas/${id}`);
}

export async function buscarPessoas(query: string) {
  const { data } = await httpClient.get<BuscaRapidaItem[]>(`${base}/pessoas/busca-rapida`, {
    params: { query, limit: 8 },
  });
  return data;
}

export async function listarTiposPessoa() {
  const { data } = await httpClient.get<PessoaTipo[]>(`${base}/pessoas/tipos`);
  return data;
}

export async function atualizarDocumento(
  pessoaId: number,
  documentoId: number,
  payload: Record<string, unknown>,
) {
  await httpClient.patch(`${base}/pessoas/${pessoaId}/documentos/${documentoId}`, payload);
}

export async function atualizarContato(
  pessoaId: number,
  contatoId: number,
  payload: Record<string, unknown>,
) {
  await httpClient.patch(`${base}/pessoas/${pessoaId}/contatos/${contatoId}`, payload);
}

export async function atualizarEndereco(
  pessoaId: number,
  enderecoId: number,
  payload: Record<string, unknown>,
) {
  await httpClient.patch(`${base}/pessoas/${pessoaId}/enderecos/${enderecoId}`, payload);
}

export async function listarLiderancas() {
  const { data } = await httpClient.get<Lideranca[]>(`${base}/liderancas`);
  return data;
}

export async function listarHierarquia() {
  const { data } = await httpClient.get<Hierarquia[]>(`${base}/hierarquia`);
  return data;
}

export async function criarHierarquia(payload: Omit<Hierarquia, 'id' | 'tenant_id' | 'criado_em'>) {
  const { data } = await httpClient.post<Hierarquia>(`${base}/hierarquia`, payload);
  return data;
}

export async function listarTags() {
  const { data } = await httpClient.get<TagCadastro[]>(`${base}/tags`);
  return data;
}

export async function criarTag(
  payload: Omit<TagCadastro, 'id' | 'tenant_id' | 'ativo' | 'criado_em'>,
) {
  const { data } = await httpClient.post<TagCadastro>(`${base}/tags`, payload);
  return data;
}

export async function atualizarTag(id: number, payload: Partial<TagCadastro>) {
  const { data } = await httpClient.patch<TagCadastro>(`${base}/tags/${id}`, payload);
  return data;
}

export async function vincularTag(tagId: number, pessoaId: number) {
  await httpClient.post(`${base}/tags/${tagId}/pessoas`, { pessoa_id: pessoaId });
}

export async function listarComunidades() {
  const { data } = await httpClient.get<Comunidade[]>(`${base}/comunidades`);
  return data;
}

export async function criarComunidade(
  payload: Omit<Comunidade, 'id' | 'tenant_id' | 'criado_em' | 'atualizado_em'>,
) {
  const { data } = await httpClient.post<Comunidade>(`${base}/comunidades`, payload);
  return data;
}

export async function vincularComunidade(comunidadeId: number, pessoaId: number, papel?: string) {
  await httpClient.post(`${base}/comunidades/${comunidadeId}/pessoas`, {
    pessoa_id: pessoaId,
    papel,
  });
}

export async function listarNucleos() {
  const { data } = await httpClient.get<NucleoFamiliar[]>(`${base}/nucleos-familiares`);
  return data;
}

export async function criarNucleo(
  payload: Omit<
    NucleoFamiliar,
    'id' | 'tenant_id' | 'quantidade_membros' | 'criado_em' | 'atualizado_em'
  >,
) {
  const { data } = await httpClient.post<NucleoFamiliar>(`${base}/nucleos-familiares`, payload);
  return data;
}

export async function vincularNucleo(
  nucleoId: number,
  pessoaId: number,
  parentesco?: string,
  observacao?: string,
) {
  await httpClient.post(`${base}/nucleos-familiares/${nucleoId}/pessoas`, {
    pessoa_id: pessoaId,
    parentesco,
    observacao,
  });
}

export async function listarValidacoes(status?: string) {
  const { data } = await httpClient.get<ValidacaoCadastro[]>(`${base}/validacoes`, {
    params: { status },
  });
  return data;
}

export async function resolverValidacao(
  id: number,
  status: 'aprovado' | 'rejeitado' | 'em_revisao',
  observacao?: string,
) {
  const { data } = await httpClient.patch<ValidacaoCadastro>(`${base}/validacoes/${id}`, {
    status,
    observacao,
  });
  return data;
}

export async function obterGrafoIndicacoes(filters: IndicacaoGraphFilters) {
  const { data } = await httpClient.get<IndicacaoGraph>(`${base}/indicacoes/grafo`, {
    params: { ...filters, limite: 300 },
  });
  return data;
}
