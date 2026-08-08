export type GoalStatus = 'ativa' | 'concluida' | 'cancelada' | 'em_risco' | 'suspensa';
export type TargetType =
  | 'lideranca'
  | 'territorio'
  | 'equipe'
  | 'comunidade'
  | 'nucleo_familiar'
  | 'pessoa';

export interface GoalType {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

export interface GoalPeriod {
  id: number;
  tenant_id: number;
  nome: string;
  data_inicio: string;
  data_fim: string;
  ciclo: string | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface GoalTarget {
  id: number;
  tenant_id: number;
  meta_voto_id: number;
  tipo_alvo: TargetType;
  alvo_id: number;
  quantidade_atribuida: number | null;
  nome_alvo: string | null;
  criado_em: string;
}

export interface GoalTracking {
  id: number;
  tenant_id: number;
  meta_voto_id: number;
  data_referencia: string;
  quantidade_projetada: number | null;
  quantidade_confirmada: number | null;
  quantidade_eleitores_vinculados: number;
  percentual_atingido: string;
  situacao_risco: 'normal' | 'atencao' | 'risco' | 'critico';
  observacao: string | null;
  criado_por: number | null;
  criado_em: string;
}

export interface GoalAlert {
  id: number;
  tipo_alerta: string;
  percentual_referencia: string | null;
  mensagem: string | null;
  severidade: string;
  resolvido: boolean;
  gerado_em: string;
  resolvido_em: string | null;
}

export interface Goal {
  id: number;
  tenant_id: number;
  campanha_eleicao_id: number;
  campanha_nome: string;
  tipo_meta_voto_id: number;
  tipo_codigo: string;
  tipo_nome: string;
  periodo_meta_id: number | null;
  periodo_nome: string | null;
  titulo: string;
  quantidade_meta: number;
  quantidade_atual: number;
  quantidade_eleitores_vinculados: number;
  percentual: string;
  situacao_risco: 'normal' | 'atencao' | 'risco' | 'critico';
  em_risco: boolean;
  score_risco: string;
  fatores_risco: Record<string, string | number | boolean>;
  coordenador_id: number | null;
  territorio_id: number | null;
  lideranca_id: number | null;
  status: GoalStatus;
  criado_por: number | null;
  criado_em: string;
  atualizado_em: string;
}

export interface GoalDetail extends Goal {
  alvos: GoalTarget[];
  acompanhamentos: GoalTracking[];
  alertas: GoalAlert[];
}

export interface GoalSummary {
  total_metas: number;
  metas_ativas: number;
  metas_atingidas: number;
  metas_em_risco: number;
  quantidade_meta_total: number;
  quantidade_atual_total: number;
  percentual_geral: string;
  limiar_risco: string;
}

export interface LeadershipRanking {
  id: number;
  campanha_eleicao_id: number;
  lideranca_id: number;
  nome_lideranca: string;
  data_referencia: string;
  posicao: number;
  total_cadastros: number;
  total_confirmacoes: number;
  total_eventos: number;
  total_demandas: number;
  quantidade_meta: number;
  quantidade_atual: number;
  percentual_meta: string;
  pontuacao: string;
  em_risco: boolean;
}

export interface TargetOption {
  id: number;
  nome: string;
  tipo: TargetType;
}

export interface GoalInput {
  tipo_meta_voto_id: number;
  periodo_meta_id?: number;
  titulo: string;
  quantidade_meta: number;
  coordenador_id?: number;
  alvos: Array<{
    tipo_alvo: TargetType;
    alvo_id: number;
    quantidade_atribuida?: number;
  }>;
}
