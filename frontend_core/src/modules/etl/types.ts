export interface DataSource {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  tipo: string;
  descricao: string | null;
  ativo: boolean;
}

export interface ImportFile {
  id: number;
  arquivo_id: number | null;
  nome_arquivo: string | null;
}

export interface DataImport {
  id: number;
  tenant_id: number;
  fonte_dado_id: number;
  fonte_nome: string;
  descricao: string | null;
  tipo_destino: string | null;
  status: 'pendente' | 'processando' | 'concluida' | 'falha' | 'parcial' | 'cancelada';
  parametros: Record<string, unknown>;
  mapeamento_colunas: Record<string, string>;
  total_linhas: number;
  linhas_validas: number;
  linhas_erro: number;
  linhas_duplicadas: number;
  linhas_pendentes: number;
  linhas_carregadas: number;
  criado_em: string;
  atualizado_em: string;
  arquivo: ImportFile | null;
}

export interface ImportSummary {
  importacao_id: number;
  status: DataImport['status'];
  total: number;
  validas: number;
  invalidas: number;
  duplicadas: number;
  pendentes: number;
  carregadas: number;
  avisos: number;
}

export interface ImportError {
  id: number;
  numero_linha: number | null;
  etapa: string | null;
  campo: string | null;
  valor: string | null;
  mensagem: string;
  severidade: string;
  criado_em: string;
}

export interface ImportDuplicate {
  id: number;
  staging_pessoa_id: number | null;
  pessoa_candidata_id: number | null;
  criterio: string | null;
  score: string | null;
  decisao: string;
  detalhes: Record<string, unknown>;
}
