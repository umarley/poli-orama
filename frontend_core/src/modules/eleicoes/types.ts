export type ElectionType = 'municipal' | 'estadual' | 'federal' | 'suplementar' | 'outra';

export interface OfficialElection {
  id: number;
  uuid_publico: string;
  ano: number;
  tipo: ElectionType;
  turno: 1 | 2;
  data_eleicao: string;
  codigo_uf_ibge: number | null;
  estado_nome: string | null;
  estado_uf: string | null;
  codigo_municipio_ibge: number | null;
  municipio_nome: string | null;
  descricao: string | null;
  ativo: boolean;
  criado_por: number | null;
  criado_em: string;
  atualizado_em: string;
}

export interface OfficialElectionInput {
  ano: number;
  tipo: ElectionType;
  turno: 1 | 2;
  data_eleicao: string;
  codigo_uf_ibge?: number | null;
  codigo_municipio_ibge?: number | null;
  descricao?: string;
  ativo?: boolean;
}

export interface Campaign {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  eleicao_id: number;
  nome: string;
  cargo_pleiteado_id: number | null;
  cargo_pleiteado: string;
  ativa: boolean;
  eleicao_ano: number;
  eleicao_tipo: ElectionType;
  eleicao_turno: 1 | 2;
  eleicao_data: string;
  eleicao_descricao: string | null;
  data_ativacao: string | null;
  data_encerramento: string | null;
  criado_por: number | null;
  criado_em: string;
  atualizado_em: string;
}

export interface CampaignInput {
  eleicao_id: number;
  nome: string;
  cargo_pleiteado_id: number;
  ativa?: boolean;
}

export interface ContestedOffice {
  id: number;
  codigo: string;
  nome: string;
  tipo_eleicao: 'municipal' | 'federal';
  ordem: number;
}

export interface CampaignClosure {
  id: number;
  tenant_id: number;
  campanha_eleicao_id: number;
  campanha_nome: string;
  cargo_pleiteado: string;
  eleicao_descricao: string | null;
  job_processamento_id: number | null;
  votos_obtidos: number;
  total_votos_validos: number | null;
  eleito: boolean;
  colocacao: number | null;
  resultado_oficial_em: string | null;
  fonte_resultado: string | null;
  observacao: string | null;
  status: 'enfileirado' | 'processando' | 'concluido' | 'falha';
  erro: string | null;
  solicitado_por: number | null;
  solicitado_em: string;
  iniciado_em: string | null;
  concluido_em: string | null;
  atualizado_em: string;
}

export interface CampaignClosureInput {
  votos_obtidos: number;
  total_votos_validos?: number;
  eleito: boolean;
  colocacao?: number;
  resultado_oficial_em?: string;
  fonte_resultado?: string;
  observacao?: string;
}
