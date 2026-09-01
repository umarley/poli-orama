export type ContractorType = 'pf' | 'pj';
export type ContractStatus = 'rascunho' | 'ativo' | 'encerrado' | 'cancelado';

export interface ContractorData {
  tipo: ContractorType;
  id: number;
  nome: string;
  documento: string;
  rg: string | null;
  data_nascimento: string | null;
  telefone: string | null;
  cep: string | null;
  logradouro: string | null;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  codigo_municipio_ibge: number | null;
  cidade: string | null;
  latitude: string | null;
  longitude: string | null;
}

export interface PersonOption extends Omit<ContractorData, 'tipo' | 'documento'> {
  cpf: string;
}

export interface CampaignContract {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  campanha_eleicao_id: number;
  tipo_contratado: ContractorType;
  pessoa_id: number | null;
  pessoa_juridica_id: number | null;
  funcao_cargo: string;
  valor_parcela: string;
  quantidade_parcelas: 1 | 2 | 3;
  valor_total: string;
  data_inicio: string;
  data_termino: string;
  dias_trabalho: number;
  valor_diaria: string;
  status: ContractStatus;
  observacoes: string | null;
  criado_em: string;
  atualizado_em: string;
  contratado: ContractorData;
}

export interface LegalEntityInput {
  razao_social: string;
  nome_fantasia?: string;
  cnpj: string;
  telefone?: string;
  cep?: string;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro_texto?: string;
  codigo_municipio_ibge?: number;
  latitude?: number;
  longitude?: number;
}

export interface ContractInput {
  tipo_contratado: ContractorType;
  pessoa_id?: number;
  pessoa_juridica?: LegalEntityInput;
  funcao_cargo: string;
  valor_parcela: number;
  quantidade_parcelas: 1 | 2 | 3;
  data_inicio: string;
  data_termino: string;
  status: ContractStatus;
  observacoes?: string;
}
