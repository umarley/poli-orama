export type TenantStatus =
  | 'pendente'
  | 'ativo'
  | 'suspenso'
  | 'cancelado'
  | 'trial'
  | 'inadimplente';

export type CommunityTerminology = 'comunidades' | 'frentes';
export type LeadershipTerminology = 'liderancas' | 'coordenadores';

export interface RegistrationDocumentPreferences {
  CPF: boolean;
  RG: boolean;
  CNH: boolean;
}

export interface RegistrationContactPreferences {
  WhatsApp: boolean;
  Celular: boolean;
  Telefone: boolean;
  'E-mail': boolean;
}

export interface RegistrationFormPreferences {
  nome_completo: boolean;
  data_nascimento: boolean;
  sexo: boolean;
  estado_civil: boolean;
  documento: RegistrationDocumentPreferences;
  canal: RegistrationContactPreferences;
  titulo_eleitoral: boolean;
}

export interface TenantPreferences extends Record<string, unknown> {
  nomenclatura_comunidades?: CommunityTerminology;
  nomenclatura_liderancas?: LeadershipTerminology;
  formulario_cadastro?: RegistrationFormPreferences;
}

export interface Plan {
  id: number;
  uuid_publico: string;
  slug: string;
  nome: string;
  descricao?: string;
  preco_mensal: string;
  moeda: string;
  limite_usuarios?: number;
  limite_pessoas?: number;
  limite_armazenamento_mb?: number;
  recursos: Record<string, boolean>;
  ordem_comercial: number;
}

export interface TenantConfiguration {
  nome_publico?: string;
  cor_primaria?: string | null;
  logo_url?: string;
  fuso_horario: string;
  percentual_alerta_meta: string;
  integracoes: Record<string, unknown>;
  preferencias: TenantPreferences;
}

export interface TenantRecord {
  id: number;
  uuid_publico: string;
  nome: string;
  slug: string;
  documento?: string;
  tem_mandato: boolean;
  plano_assinatura_id?: number;
  data_inicio_contrato?: string | null;
  data_fim_contrato?: string | null;
  status: TenantStatus;
  criado_em: string;
  atualizado_em: string;
  plano?: Plan;
  configuracao?: TenantConfiguration;
}

export interface TenantInput {
  nome?: string;
  slug?: string;
  documento?: string;
  tem_mandato?: boolean;
  plano_assinatura_id?: number;
  status?: TenantStatus;
}

export interface PlanUsage {
  plano?: Plan;
  usuarios: number;
  pessoas: number;
  armazenamento_mb: string;
}
