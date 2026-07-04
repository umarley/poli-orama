export type DemandCatalogKey = 'categorias' | 'status' | 'prioridades' | 'origens' | 'resultados';

export interface DemandCatalog {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
  ordem?: number | null;
  final?: boolean | null;
  peso?: number | null;
}

export interface Demand {
  id: number;
  protocolo: string | null;
  titulo: string | null;
  descricao: string;
  pessoa_solicitante_id: number | null;
  solicitante_nome: string | null;
  lideranca_indicacao_id: number | null;
  evento_id: number | null;
  territorio_id: number | null;
  territorio_nome: string | null;
  categoria_demanda_id: number | null;
  categoria_nome: string | null;
  prioridade_demanda_id: number | null;
  prioridade_nome: string | null;
  status_demanda_id: number;
  status_codigo: string;
  status_nome: string;
  origem_demanda_id: number | null;
  origem_nome: string | null;
  responsavel_atendimento_id: number | null;
  responsavel_nome: string | null;
  resultado_atendimento_id: number | null;
  resultado_nome: string | null;
  prazo: string | null;
  vencida: boolean;
  classificacao_automatica: boolean;
  classificacao_detalhes: Record<string, unknown>;
  criado_em: string;
  atualizado_em: string;
}

export interface DemandDetail extends Demand {
  atendimentos: Array<Record<string, unknown>>;
  movimentacoes: Array<Record<string, unknown>>;
  anexos: Array<Record<string, unknown>>;
  alertas: Array<Record<string, unknown>>;
}

export interface DemandResponsible {
  id: number;
  nome: string;
  tipo: 'usuario' | 'pessoa' | 'setor' | 'area';
  ativo: boolean;
}

export interface DemandFilters {
  status?: number;
  categoria?: number;
  responsavel?: number;
  territorio?: number;
  origem?: number;
  lider?: number;
  inicio?: string;
  fim?: string;
}

export interface DemandInput {
  titulo?: string;
  descricao: string;
  pessoa_solicitante_id?: number;
  lideranca_indicacao_id?: number;
  evento_id?: number;
  territorio_id?: number;
  categoria_demanda_id?: number;
  prioridade_demanda_id?: number;
  origem_demanda_id?: number;
  prazo?: string;
}

export interface DemandSummary {
  total: number;
  vencidas: number;
  por_status: Array<{ chave: string; total: number }>;
  por_categoria: Array<{ chave: string; total: number }>;
  por_territorio: Array<{ chave: string; total: number }>;
  por_responsavel: Array<{ chave: string; total: number }>;
}

export interface DemandClassification {
  categoria_demanda_id: number | null;
  categoria_codigo: string | null;
  prioridade_demanda_id: number | null;
  prioridade_codigo: string | null;
  detalhes: Record<string, unknown>;
}
