export interface CatalogoComunicacao {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
  criado_em: string | null;
  atualizado_em: string | null;
}

export interface InteracaoPessoa {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  pessoa_nome: string;
  tipo_interacao_id: number | null;
  tipo_interacao_nome: string | null;
  canal_comunicacao_id: number | null;
  canal_comunicacao_nome: string | null;
  lideranca_id: number | null;
  demanda_id: number | null;
  evento_id: number | null;
  direcao: 'entrada' | 'saida';
  assunto: string | null;
  conteudo: string | null;
  resultado: string | null;
  data_interacao: string;
  registrado_por: number | null;
  registrado_por_nome: string | null;
  criado_em: string;
}

export interface InteracaoInput {
  tipo_interacao_id?: number;
  canal_comunicacao_id?: number;
  direcao: 'entrada' | 'saida';
  assunto?: string;
  conteudo?: string;
  resultado?: string;
  data_interacao?: string;
}
