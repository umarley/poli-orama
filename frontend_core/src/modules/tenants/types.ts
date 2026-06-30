export type TenantStatus =
  | 'pendente'
  | 'ativo'
  | 'suspenso'
  | 'cancelado'
  | 'trial'
  | 'inadimplente';

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
  cor_primaria?: string;
  logo_url?: string;
  fuso_horario: string;
  percentual_alerta_meta: string;
  integracoes: Record<string, unknown>;
  preferencias: Record<string, unknown>;
}

export interface TenantRecord {
  id: number;
  uuid_publico: string;
  nome: string;
  slug: string;
  documento?: string;
  tem_mandato: boolean;
  plano_assinatura_id?: number;
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
