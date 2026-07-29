export interface Estado {
  codigo_ibge: number;
  uf: string;
  nome: string;
  regiao: string | null;
}

export interface Municipio {
  codigo_ibge: number;
  codigo_uf_ibge: number;
  codigo_tse: number | null;
  nome: string;
  latitude: string | null;
  longitude: string | null;
}

export interface Bairro {
  id: number;
  codigo_municipio_ibge: number;
  nome: string;
  origem: string;
}

export interface ZonaEleitoral {
  id: number;
  codigo_uf_ibge: number;
  codigo_municipio_ibge: number | null;
  numero_zona: number;
  descricao: string | null;
}

export interface LocalVotacao {
  id: number;
  codigo_municipio_ibge: number;
  zona_eleitoral_id: number | null;
  bairro_id: number | null;
  codigo_local: number | null;
  nome: string;
  logradouro: string | null;
  numero: string | null;
  cep: string | null;
}

export interface SecaoEleitoral {
  id: number;
  zona_eleitoral_id: number;
  local_votacao_id: number | null;
  numero_secao: number;
  agregada_em: number | null;
}

export interface TipoTerritorio {
  id: number;
  tenant_id: number | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

//t.nome, t.codigo_uf_ibge, t.codigo_municipio_ibge

export interface Territorio {
  id: number;
  tenant_id: number;
  tipo_territorio_id: number;
  tipo_codigo: string;
  tipo_nome: string;
  nome: string;
  codigo_uf_ibge: number | null;
  codigo_municipio_ibge: number | null;
  bairro_id: number | null;
  zona_eleitoral_id: number | null;
  secao_eleitoral_id: number | null;
  territorio_pai_id: number | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface TerritorioTreeNode extends Territorio {
  filhos: TerritorioTreeNode[];
}

export interface TerritorioInput {
  tipo_territorio_id: number;
  nome: string;
  codigo_uf_ibge?: number;
  codigo_municipio_ibge?: number;
  bairro_id?: number;
  zona_eleitoral_id?: number;
  secao_eleitoral_id?: number;
  territorio_pai_id?: number;
}

export type VinculoPessoaTerritorio = 'moradia' | 'atuacao' | 'votacao' | 'responsabilidade';

export interface PessoaTerritorio {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  territorio_id: number;
  vinculo: VinculoPessoaTerritorio;
  territorio_nome: string;
  tipo_nome: string;
  territorio_ativo: boolean;
}

export interface MapMarker {
  latitude: string;
  longitude: string;
  quantidade: number;
  tipo: 'pessoa';
}

export interface MapPerson {
  id: number;
  nome_completo: string;
  apelido: string | null;
  telefone: string | null;
  territorio: string | null;
}
