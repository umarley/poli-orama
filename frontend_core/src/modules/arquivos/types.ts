export type AttachmentEntity =
  | 'pessoa'
  | 'evento'
  | 'demanda'
  | 'interacao'
  | 'importacao'
  | 'comunidade'
  | 'lideranca'
  | 'convite';

export interface AttachmentType {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

export interface StoredFile {
  id: number;
  uuid_publico: string;
  nome_original: string;
  mime_type: string | null;
  extensao: string | null;
  tamanho_bytes: number | null;
  hash_sha256: string | null;
  provedor_storage: string;
  criado_em: string;
}

export interface Attachment {
  id: number;
  entidade_tipo: AttachmentEntity;
  entidade_id: number;
  descricao: string | null;
  criado_em: string;
  tipo: AttachmentType | null;
  arquivo: StoredFile;
  download_url: string;
  preview_url: string | null;
}
