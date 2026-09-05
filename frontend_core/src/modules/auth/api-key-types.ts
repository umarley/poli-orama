export interface ApiKeyRecord {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  tenant_nome: string;
  tenant_slug: string;
  nome: string;
  token_prefix: string;
  ativo: boolean;
  ultimo_uso_em: string | null;
  revogada_em: string | null;
  criado_por: number;
  criado_em: string;
  atualizado_em: string;
}

export interface ApiKeyCreated extends ApiKeyRecord {
  token: string;
}

export interface ApiKeyInput {
  tenant_id: number;
  nome: string;
}
