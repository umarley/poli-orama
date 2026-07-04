export interface AgendaCatalog {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

export interface AgendaEvent {
  id: number;
  tenant_id: number;
  tipo_evento_id: number | null;
  tipo_evento_nome: string | null;
  status_evento_id: number | null;
  status_evento_codigo: string | null;
  status_evento_nome: string | null;
  titulo: string;
  descricao: string | null;
  data_inicio: string;
  data_fim: string | null;
  local_nome: string | null;
  endereco_id: number | null;
  municipio_id: number | null;
  bairro_id: number | null;
  zona_eleitoral_id: number | null;
  territorio_id: number | null;
  territorio_nome: string | null;
  latitude: string | null;
  longitude: string | null;
  responsavel_pessoa_id: number;
  responsavel_nome: string;
  motivo_cancelamento: string | null;
  cancelado_em: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface EventParticipant {
  id: number;
  pessoa_id: number;
  nome: string;
  papel: string | null;
  presente: boolean | null;
  observacao: string | null;
}

export interface EventLeadership {
  lideranca_id: number;
  pessoa_id: number;
  nome: string;
  tipo_lideranca: string | null;
  papel: string | null;
}

export interface EventInvitation {
  id: number;
  direcao: string;
  origem: string | null;
  pessoa_indicou_id: number | null;
  pessoa_indicou_nome: string | null;
  arquivo_id: number | null;
  arquivo_nome: string | null;
  status: string;
  descricao: string | null;
  criado_em: string;
}

export interface EventAgendaItem {
  id: number;
  titulo: string;
  descricao: string | null;
  encaminhamento: string | null;
  ordem: number | null;
  criado_em: string;
}

export interface EventAttendance {
  id: number;
  presenca_parlamentar: boolean;
  presenca_representante: boolean;
  nome_representante: string | null;
  numero_lideres_presentes: number | null;
  numero_convidados: number | null;
  numero_estimado_presentes: number | null;
  observacao: string | null;
  registrado_por: number | null;
  registrado_em: string;
}

export interface EventDemand {
  id: number;
  evento_id: number;
  titulo: string | null;
  descricao: string;
  pessoa_solicitante_id: number | null;
  territorio_id: number | null;
  status: string;
  prioridade: string | null;
  criado_em: string;
}

export interface AgendaInsight {
  id: number;
  evento_id: number | null;
  tipo: string;
  tema: string;
  frequencia: number;
  score: string | null;
  detalhes: Record<string, unknown>;
  gerado_em: string;
}

export interface AgendaEventDetail extends AgendaEvent {
  participantes: EventParticipant[];
  liderancas: EventLeadership[];
  convites: EventInvitation[];
  pautas: EventAgendaItem[];
  presenca: EventAttendance | null;
  demandas: EventDemand[];
  lembretes: Array<{
    id: number;
    evento_id: number;
    tipo: string;
    mensagem: string;
    agendado_para: string;
    status: string;
  }>;
  insights: AgendaInsight[];
}

export interface EventInput {
  tipo_evento_id?: number;
  status_evento_id?: number;
  titulo: string;
  descricao?: string;
  data_inicio: string;
  data_fim?: string;
  local_nome?: string;
  territorio_id?: number;
  responsavel_pessoa_id: number;
}

export interface AgendaFilters {
  data_inicio?: string;
  data_fim?: string;
  territorio_id?: number;
  lideranca_id?: number;
  tipo_evento_id?: number;
  status_evento_id?: number;
}
