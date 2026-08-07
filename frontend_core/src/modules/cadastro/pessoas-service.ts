import { httpClient } from '@/services/api/http-client';
import type { PaginatedResponse } from '@/types/api';

import type {
  BuscaRapidaItem,
  Comunidade,
  ComunidadePessoa,
  EstadoCivil,
  Hierarquia,
  IndicacaoGraph,
  IndicacaoGraphFilters,
  Lideranca,
  LiderancaInput,
  NucleoFamiliar,
  NucleoPessoa,
  PessoaCreateInput,
  PessoaDetalhe,
  PessoaDocumento,
  PessoaFilters,
  PessoaListItem,
  PessoaRedeSocial,
  ParentescoOption,
  PapelComunidade,
  PessoaContato,
  PessoaTipo,
  TipoDocumento,
  TipoContato,
  Eleitor,
  TagCadastro,
  TagPessoa,
  Religiao,
  RedeSocial,
  ValidacaoCadastro,
  PessoaMergeInput,
  PessoaMergePreview,
  PessoaMergeResponse,
  StatusDuplicidade,
  SuspeitaDuplicidade,
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

export async function calcularCompletudePessoa(id: number) {
  const { data } = await httpClient.post<PessoaDetalhe>(
    `${base}/pessoas/${id}/calcular-completude`,
  );
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

export async function criarIndicacao(
  pessoaIndicanteId: number,
  payload: {
    pessoa_indicada_id: number;
    origem?: string | null;
    contexto?: string | null;
    data_indicacao: string;
  },
) {
  await httpClient.post(`${base}/pessoas/${pessoaIndicanteId}/indicacoes`, payload);
}

export async function listarTiposPessoa() {
  const { data } = await httpClient.get<PessoaTipo[]>(`${base}/pessoas/tipos`);
  return data;
}

export async function substituirTiposPessoa(pessoaId: number, tipoIds: number[]) {
  const { data } = await httpClient.put<PessoaTipo[]>(`${base}/pessoas/${pessoaId}/tipos`, {
    tipo_ids: tipoIds,
  });
  return data;
}

export async function listarEstadosCivis() {
  const { data } = await httpClient.get<EstadoCivil[]>(`${base}/estados-civis`);
  return data;
}

export async function listarReligioes() {
  const { data } = await httpClient.get<Religiao[]>(`${base}/religioes`);
  return data;
}

export async function criarRedeSocial(
  pessoaId: number,
  payload: {
    rede: RedeSocial;
    usuario_perfil?: string | null;
    url?: string | null;
    seguidores?: number | null;
  },
) {
  const { data } = await httpClient.post<PessoaRedeSocial>(
    `${base}/pessoas/${pessoaId}/redes-sociais`,
    payload,
  );
  return data;
}

export async function atualizarRedeSocial(
  pessoaId: number,
  redeSocialId: number,
  payload: {
    rede: RedeSocial;
    usuario_perfil?: string | null;
    url?: string | null;
    seguidores?: number | null;
  },
) {
  const { data } = await httpClient.patch<PessoaRedeSocial>(
    `${base}/pessoas/${pessoaId}/redes-sociais/${redeSocialId}`,
    payload,
  );
  return data;
}

export async function atualizarDocumento(
  pessoaId: number,
  documentoId: number,
  payload: Record<string, unknown>,
) {
  await httpClient.patch(`${base}/pessoas/${pessoaId}/documentos/${documentoId}`, payload);
}

export async function criarDocumento(
  pessoaId: number,
  payload: {
    tipo_documento: TipoDocumento;
    numero: string;
    orgao_emissor?: string | null;
    uf_emissor?: string | null;
  },
) {
  const { data } = await httpClient.post<PessoaDocumento>(
    `${base}/pessoas/${pessoaId}/documentos`,
    payload,
  );
  return data;
}

export async function atualizarContato(
  pessoaId: number,
  contatoId: number,
  payload: Record<string, unknown>,
) {
  await httpClient.patch(`${base}/pessoas/${pessoaId}/contatos/${contatoId}`, payload);
}

export async function criarContato(
  pessoaId: number,
  payload: {
    tipo_contato: TipoContato;
    valor: string;
    principal?: boolean;
    observacao?: string | null;
  },
) {
  const { data } = await httpClient.post<PessoaContato>(
    `${base}/pessoas/${pessoaId}/contatos`,
    payload,
  );
  return data;
}

export async function definirEleitor(
  pessoaId: number,
  payload: {
    titulo_eleitor?: string | null;
    zona_eleitoral_id?: number | null;
    secao_eleitoral_id?: number | null;
    local_votacao_id?: number | null;
    codigo_municipio_ibge?: number | null;
    situacao_titulo?: Eleitor['situacao_titulo'];
  },
) {
  const { data } = await httpClient.put<Eleitor>(`${base}/pessoas/${pessoaId}/eleitor`, payload);
  return data;
}

export async function atualizarEndereco(
  pessoaId: number,
  enderecoId: number,
  payload: Record<string, unknown>,
) {
  await httpClient.patch(`${base}/pessoas/${pessoaId}/enderecos/${enderecoId}`, payload);
}

export interface LiderancaFilters {
  query?: string;
  coordenador_id?: number;
  territorio_id?: number;
  tipo_lideranca?: Lideranca['tipo_lideranca'];
}

export async function listarLiderancas(filters: LiderancaFilters = {}) {
  const { data } = await httpClient.get<Lideranca[]>(`${base}/liderancas`, { params: filters });
  return data;
}

export async function excluirLideranca(id: number) {
  await httpClient.delete(`${base}/liderancas/${id}`);
}

export async function definirLideranca(pessoaId: number, payload: LiderancaInput) {
  const { data } = await httpClient.put<Lideranca>(
    `${base}/pessoas/${pessoaId}/lideranca`,
    payload,
  );
  return data;
}

export interface HierarquiaFilters {
  pessoa_query?: string;
  lideranca_superior_id?: number;
  papel_subordinado?: Hierarquia['papel_subordinado'];
}

export async function listarHierarquia(filters: HierarquiaFilters = {}) {
  const { data } = await httpClient.get<Hierarquia[]>(`${base}/hierarquia`, { params: filters });
  return data;
}

export async function criarHierarquia(payload: Omit<Hierarquia, 'id' | 'tenant_id' | 'criado_em'>) {
  const { data } = await httpClient.post<Hierarquia>(`${base}/hierarquia`, payload);
  return data;
}

export async function alterarStatusHierarquia(id: number, ativo: boolean) {
  const { data } = await httpClient.patch<Hierarquia>(`${base}/hierarquia/${id}/status`, {
    ativo,
  });
  return data;
}

export async function excluirHierarquia(id: number) {
  await httpClient.delete(`${base}/hierarquia/${id}`);
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

export async function listarPessoasTag(tagId: number) {
  const { data } = await httpClient.get<TagPessoa[]>(`${base}/tags/${tagId}/pessoas`);
  return data;
}

export async function removerPessoaTag(tagId: number, pessoaId: number) {
  await httpClient.delete(`${base}/tags/${tagId}/pessoas/${pessoaId}`);
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

export async function atualizarComunidade(
  id: number,
  payload: Omit<Comunidade, 'id' | 'tenant_id' | 'criado_em' | 'atualizado_em'>,
) {
  const { data } = await httpClient.patch<Comunidade>(`${base}/comunidades/${id}`, payload);
  return data;
}

export async function vincularComunidade(comunidadeId: number, pessoaId: number, papel?: string) {
  await httpClient.post(`${base}/comunidades/${comunidadeId}/pessoas`, {
    pessoa_id: pessoaId,
    papel,
  });
}

export async function listarPessoasComunidade(comunidadeId: number) {
  const { data } = await httpClient.get<ComunidadePessoa[]>(
    `${base}/comunidades/${comunidadeId}/pessoas`,
  );
  return data;
}

export async function removerPessoaComunidade(comunidadeId: number, pessoaId: number) {
  await httpClient.delete(`${base}/comunidades/${comunidadeId}/pessoas/${pessoaId}`);
}

export async function listarPapeisComunidade() {
  const { data } = await httpClient.get<PapelComunidade[]>(`${base}/comunidades-papeis`);
  return data;
}

export async function listarNucleos() {
  const { data } = await httpClient.get<NucleoFamiliar[]>(`${base}/nucleos-familiares`);
  return data;
}

export async function criarNucleo(
  payload: Omit<
    NucleoFamiliar,
    | 'id'
    | 'tenant_id'
    | 'pessoa_referencia_nome'
    | 'quantidade_membros'
    | 'criado_em'
    | 'atualizado_em'
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

export async function listarPessoasNucleo(nucleoId: number) {
  const { data } = await httpClient.get<NucleoPessoa[]>(
    `${base}/nucleos-familiares/${nucleoId}/pessoas`,
  );
  return data;
}

export async function removerPessoaNucleo(nucleoId: number, pessoaId: number) {
  await httpClient.delete(`${base}/nucleos-familiares/${nucleoId}/pessoas/${pessoaId}`);
}

export async function listarParentescos() {
  const { data } = await httpClient.get<ParentescoOption[]>(
    `${base}/nucleos-familiares-parentescos`,
  );
  return data;
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

export async function listarDuplicidades(status?: StatusDuplicidade) {
  const { data } = await httpClient.get<SuspeitaDuplicidade[]>(`${base}/duplicidades`, {
    params: { status },
  });
  return data;
}

export async function obterPreviewMerge(duplicateId: number) {
  const { data } = await httpClient.get<PessoaMergePreview>(
    `${base}/duplicidades/${duplicateId}/merge-preview`,
  );
  return data;
}

export async function resolverDuplicidade(
  duplicateId: number,
  decisao: 'duplicado' | 'falso_positivo' | 'pendente',
) {
  const { data } = await httpClient.patch<SuspeitaDuplicidade>(
    `${base}/duplicidades/${duplicateId}`,
    { decisao },
  );
  return data;
}

export async function mesclarDuplicidade(duplicateId: number, payload: PessoaMergeInput) {
  const { data } = await httpClient.post<PessoaMergeResponse>(
    `${base}/duplicidades/${duplicateId}/merge`,
    payload,
  );
  return data;
}

export async function obterGrafoIndicacoes(filters: IndicacaoGraphFilters) {
  const { data } = await httpClient.get<IndicacaoGraph>(`${base}/indicacoes/grafo`, {
    params: { ...filters, limite: 300 },
  });
  return data;
}
