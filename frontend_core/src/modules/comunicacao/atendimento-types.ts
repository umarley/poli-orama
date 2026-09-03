import type { PessoaContato } from '@/modules/cadastro/types';

export type AttendanceStatus =
  | 'em_atendimento'
  | 'concluido'
  | 'sem_resposta'
  | 'numero_invalido'
  | 'interrompido';
export type VoteIntention = 'votara' | 'nao_votara' | 'indeciso' | 'nao_respondeu';

export interface CommunicationChannel {
  id: number;
  codigo: string;
  nome: string;
  descricao: string | null;
}

export interface RejectionReason {
  id: number;
  codigo: string;
  nome: string;
  descricao: string | null;
}

export interface AttendancePerson {
  id: number;
  nome_completo: string;
  nome_social: string | null;
  apelido: string | null;
  sexo: string | null;
  data_nascimento: string | null;
  observacoes: string | null;
  telefone: string | null;
  email: string | null;
  contatos: PessoaContato[];
  tags: string[];
  frentes: string[];
  nucleos_familiares: string[];
  titulo_eleitor: string | null;
  codigo_municipio_ibge: number | null;
  zona_eleitoral_id: number | null;
  zona_eleitoral: string | null;
  secao_eleitoral_id: number | null;
  secao_eleitoral: string | null;
  local_votacao_id: number | null;
  local_votacao: string | null;
}

export interface VoteIntentionHistoryItem {
  id: number;
  intencao_voto: VoteIntention;
  motivo_rejeicao_nome: string | null;
  motivo_observacao: string | null;
  criado_em: string;
  registrado_por_nome: string | null;
}

export interface AttendanceInteraction {
  id: number;
  assunto: string | null;
  conteudo: string | null;
  resultado: string | null;
  data_interacao: string;
  registrado_por_nome: string | null;
}

export interface Attendance {
  id: number;
  pessoa_id: number;
  canal: number;
  canal_codigo: string | null;
  canal_nome: string | null;
  canal_outro: string | null;
  situacao: AttendanceStatus;
  resultado: string | null;
  intencao_voto: VoteIntention | null;
  motivo_rejeicao_id: number | null;
  motivo_rejeicao_nome: string | null;
  motivo_observacao: string | null;
  observacao: string | null;
  motivo_encerramento: string | null;
  motivo_inativacao?: string | null;
  iniciado_em: string;
  finalizado_em: string | null;
  pessoa: AttendancePerson;
  interacoes: AttendanceInteraction[];
  historico_intencao: VoteIntentionHistoryItem[];
}

export interface AttendancePersonUpdate {
  nome_completo?: string;
  data_nascimento?: string | null;
  sexo?: 'M' | 'F' | 'O' | 'N' | null;
  titulo_eleitor?: string | null;
  codigo_municipio_ibge?: number | null;
  zona_eleitoral_id?: number | null;
  secao_eleitoral_id?: number | null;
  local_votacao_id?: number | null;
}

export interface AttendanceUpdate {
  canal?: number;
  canal_outro?: string | null;
  observacao?: string | null;
  intencao_voto?: VoteIntention | null;
  motivo_rejeicao_id?: number | null;
  motivo_observacao?: string | null;
}

export interface AttendanceClosePayload {
  situacao: Exclude<AttendanceStatus, 'em_atendimento'>;
  canal: number;
  canal_outro?: string | null;
  intencao_voto: VoteIntention;
  motivo_rejeicao_id?: number | null;
  motivo_observacao?: string | null;
  observacao?: string | null;
  motivo_encerramento?: string | null;
}

export interface AttendanceIndicators {
  total_atendimentos: number;
  concluidos: number;
  sem_resposta: number;
  votos_confirmados: number;
  indecisos: number;
  respostas_negativas: number;
  tempo_medio_minutos: number;
  percentual_conversao: number;
  por_periodo: Array<{ periodo: string; quantidade: number }>;
  por_telefonista: Array<{ atendente_usuario_id: number; atendente_nome: string; quantidade: number }>;
  por_canal: Array<{ canal_id: number; canal: string; quantidade: number }>;
  principais_motivos_rejeicao: Array<{ motivo: string; quantidade: number }>;
}
