export interface AccessProfile {
  id: number;
  nome: string;
  codigo: string;
  descricao?: string | null;
  nivel: number;
  permissoes: Permission[];
}

export interface Permission {
  id: number;
  codigo: string;
  modulo: string;
  acao: string;
  descricao?: string | null;
}

export interface TerritorialAccess {
  id: number;
  tenant_id: number;
  usuario_id: number;
  tipo_escopo:
    | 'estado'
    | 'municipio'
    | 'bairro'
    | 'zona_eleitoral'
    | 'secao_eleitoral'
    | 'territorio'
    | 'global';
  codigo_uf_ibge?: number;
  codigo_municipio_ibge?: number;
  bairro_id?: number;
  zona_eleitoral_id?: number;
  secao_eleitoral_id?: number;
  territorio_id?: number;
  pode_administrar: boolean;
  criado_em: string;
}

export interface AuthUser {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  pessoa_id?: number | null;
  nome: string;
  email: string;
  telefone?: string | null;
  status: 'ativo' | 'inativo' | 'bloqueado' | 'pendente';
  deve_alterar_senha: boolean;
  mfa_habilitado: boolean;
  ultimo_login_em?: string;
  criado_em: string;
  atualizado_em: string;
  tenant: TenantRecord;
  perfis: AccessProfile[];
  permissoes: string[];
  acessos_territoriais: TerritorialAccess[];
}

export interface AuthenticationResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  usuario: AuthUser;
}

export interface LoginInput {
  tenant_slug: string;
  email: string;
  senha: string;
  dispositivo?: string;
  codigo_mfa?: string;
}

export interface TenantSwitchInput {
  tenant_id: number;
  dispositivo?: string;
}

export interface UserSession {
  id: number;
  dispositivo?: string | null;
  user_agent?: string | null;
  ip_origem?: string | null;
  criado_em: string;
  ultimo_uso_em: string;
  expira_em: string;
  revogada_em?: string | null;
  atual: boolean;
  status: 'ativa' | 'revogada' | 'expirada' | 'expirada_inatividade';
}

export interface MfaSetup {
  segredo: string;
  uri_configuracao: string;
}
import type { TenantRecord } from '@/modules/tenants/types';
