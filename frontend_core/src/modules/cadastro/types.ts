export type TipoDocumento = 'cpf' | 'rg' | 'titulo_eleitor' | 'cnh' | 'passaporte' | 'outro';
export type TipoContato = 'telefone' | 'celular' | 'whatsapp' | 'email' | 'outro';
export type TipoEndereco = 'residencial' | 'eleitoral' | 'comercial' | 'temporario' | 'outro';
export type TipoLideranca = 'coordenador_geral' | 'coordenador_territorial' | 'lider' | 'sublider';

export interface PessoaListItem {
  id: number;
  nome_completo: string;
  nome_social: string | null;
  apelido: string | null;
  data_nascimento: string | null;
  ativo: boolean;
  cpf: string | null;
  telefone: string | null;
  tipos: string[];
  lideranca_id: number | null;
}

export interface PessoaDocumento {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  tipo_documento: TipoDocumento;
  numero: string;
  orgao_emissor: string | null;
  uf_emissor: string | null;
  data_emissao: string | null;
  criado_em: string;
}

export interface PessoaContato {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  tipo_contato: TipoContato;
  valor: string;
  principal: boolean;
  verificado: boolean;
  observacao: string | null;
  criado_em: string;
}

export interface Endereco {
  id: number;
  tenant_id: number;
  codigo_municipio_ibge: number | null;
  bairro_id: number | null;
  bairro_texto: string | null;
  logradouro: string | null;
  numero: string | null;
  complemento: string | null;
  cep: string | null;
  ponto_referencia: string | null;
  latitude: string | null;
  longitude: string | null;
  geocodificado: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface PessoaEndereco {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  endereco_id: number;
  tipo: TipoEndereco;
  principal: boolean;
  endereco: Endereco;
}

export interface PessoaTipo {
  id: number;
  codigo: string;
  nome: string;
  descricao: string | null;
}

export interface Eleitor {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  titulo_eleitor: string | null;
  zona_eleitoral_id: number | null;
  secao_eleitoral_id: number | null;
  local_votacao_id: number | null;
  codigo_municipio_ibge: number | null;
  situacao_titulo: 'regular' | 'suspenso' | 'cancelado' | 'desconhecido' | null;
  criado_em: string;
  atualizado_em: string;
}

export interface Lideranca {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  tipo_lideranca: TipoLideranca;
  coordenador_id: number | null;
  apelido_campanha: string | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
  pessoa_nome_completo?: string | null;
  coordenador_nome_completo?: string | null;
  territorio_ids?: number[];
  territorios?: Array<{ id: number; nome: string }>;
  tags?: Array<{ id: number; nome: string; cor: string | null }>;
}

export interface LiderancaInput {
  tipo_lideranca: TipoLideranca;
  coordenador_id: number | null;
  apelido_campanha: string | null;
  ativo: boolean;
}

export interface VinculoResumo {
  id: number;
  nome: string;
}

export interface EstadoCivil {
  id: number;
  codigo: string;
  nome: string;
  ordem: number;
}

export interface Religiao {
  id: number;
  nome: string;
}

export type RedeSocial =
  | 'instagram'
  | 'facebook'
  | 'tiktok'
  | 'x'
  | 'youtube'
  | 'linkedin'
  | 'outro';

export interface PessoaRedeSocial {
  id: number;
  rede: RedeSocial;
  usuario_perfil: string | null;
  url: string | null;
  seguidores: number | null;
}

export interface PessoaDetalhe {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  nome_completo: string;
  nome_social: string | null;
  apelido: string | null;
  sexo: 'M' | 'F' | 'O' | 'N' | null;
  data_nascimento: string | null;
  estado_civil: number | null;
  escolaridade_id: number | null;
  profissao_id: number | null;
  religiao_id: number | null;
  observacoes: string | null;
  nivel_engajamento: number | null;
  score_confiabilidade: string | null;
  completude_cadastral: string | null;
  ativo: boolean;
  criado_por: number | null;
  atualizado_por: number | null;
  criado_em: string;
  atualizado_em: string;
  excluido_em: string | null;
  documentos: PessoaDocumento[];
  contatos: PessoaContato[];
  enderecos: PessoaEndereco[];
  eleitor: Eleitor | null;
  lideranca: Lideranca | null;
  redes_sociais: PessoaRedeSocial[];
  tipos: PessoaTipo[];
  indicacoes: Array<{
    id: number;
    pessoa_indicante_id: number | null;
    pessoa_indicada_id: number;
    pessoa_indicada_nome: string | null;
    origem: string | null;
    contexto: string | null;
    data_indicacao: string;
    criado_em: string;
  }>;
  complemento_politico: {
    vinculo_politico: string | null;
    partido_id: number | null;
    cargo_funcao: string | null;
    temas_interesse: string[];
    nivel_engajamento: number | null;
    observacoes: string | null;
  } | null;
  tags: VinculoResumo[];
  comunidades: VinculoResumo[];
  nucleos_familiares: VinculoResumo[];
  hierarquia: Array<{
    id: number;
    lideranca_superior_id: number;
    lideranca_superior_nome: string | null;
    papel_subordinado: string;
    ativo: boolean;
  }>;
}

export interface PessoaFilters {
  page?: number;
  page_size?: number;
  query?: string;
  nome?: string;
  cpf?: string;
  telefone?: string;
  tipo_id?: number;
  lideranca_id?: number;
  territorio_id?: number;
  tag_id?: number;
  incluir_inativos?: boolean;
}

export interface PessoaCreateInput {
  nome_completo: string;
  nome_social?: string;
  apelido?: string;
  sexo?: 'M' | 'F' | 'O' | 'N';
  data_nascimento?: string;
  estado_civil?: number;
  observacoes?: string;
  documentos: Array<{
    tipo_documento: TipoDocumento;
    numero: string;
    orgao_emissor?: string;
    uf_emissor?: string;
  }>;
  contatos: Array<{
    tipo_contato: TipoContato;
    valor: string;
    principal: boolean;
  }>;
  enderecos: Array<{
    tipo: TipoEndereco;
    principal: boolean;
    endereco: {
      cep?: string;
      codigo_municipio_ibge?: number;
      logradouro?: string;
      numero?: string;
      complemento?: string;
      bairro_texto?: string;
      ponto_referencia?: string;
    };
  }>;
  redes_sociais: Array<{
    rede: string;
    usuario_perfil?: string;
    url?: string;
  }>;
  tipo_ids: number[];
  eleitor?: {
    titulo_eleitor?: string;
    zona_eleitoral_id?: number;
    secao_eleitoral_id?: number;
    local_votacao_id?: number;
    codigo_municipio_ibge?: number;
    situacao_titulo: string;
  };
  lideranca?: {
    tipo_lideranca: TipoLideranca;
    coordenador_id?: number;
    apelido_campanha?: string;
    ativo: boolean;
  };
  lideranca_superior_id?: number;
  papel_subordinado?: 'lider' | 'liderado' | 'apoiador' | 'eleitor';
}

export interface Hierarquia {
  id: number;
  tenant_id: number;
  lideranca_superior_id: number;
  lideranca_superior_nome?: string | null;
  pessoa_subordinada_id: number;
  pessoa_subordinada_nome?: string | null;
  papel_subordinado: 'lider' | 'liderado' | 'apoiador' | 'eleitor';
  data_inicio: string;
  data_fim: string | null;
  ativo: boolean;
  criado_em: string;
}

export interface TagCadastro {
  id: number;
  tenant_id: number;
  nome: string;
  cor: string | null;
  categoria: string | null;
  descricao: string | null;
  ativo: boolean;
  criado_em: string;
}

export interface TagPessoa {
  id: number;
  nome_completo: string;
  data_nascimento: string | null;
}

export interface Comunidade {
  id: number;
  tenant_id: number;
  nome: string;
  tipo: string | null;
  descricao: string | null;
  lider_responsavel_id: number | null;
  codigo_municipio_ibge: number | null;
  territorio_id: number | null;
  criado_em: string;
  atualizado_em: string;
}

export interface ComunidadePessoa {
  id: number;
  nome_completo: string;
  data_nascimento: string | null;
  papel: string | null;
}

export interface PapelComunidade {
  codigo: string;
  nome: string;
}

export interface NucleoFamiliar {
  id: number;
  tenant_id: number;
  nome: string | null;
  pessoa_referencia_id: number | null;
  pessoa_referencia_nome: string | null;
  endereco_id: number | null;
  quantidade_membros: number | null;
  criado_em: string;
  atualizado_em: string;
}

export interface NucleoPessoa {
  id: number;
  nome_completo: string;
  data_nascimento: string | null;
  parentesco: string | null;
  observacao: string | null;
}

export interface ParentescoOption {
  codigo: string;
  nome: string;
}

export interface ValidacaoCadastro {
  id: number;
  tenant_id: number;
  pessoa_id: number;
  motivo: string;
  status: 'pendente' | 'aprovado' | 'rejeitado' | 'em_revisao';
  observacao: string | null;
  revisado_por: number | null;
  revisado_em: string | null;
  criado_em: string;
}

export interface BuscaRapidaItem {
  id: number;
  nome_completo: string;
  data_nascimento: string | null;
  documento: string | null;
  telefone: string | null;
}

export interface IndicacaoGraphNode {
  id: number;
  nome: string;
  ativo: boolean;
}

export interface IndicacaoGraphEdge {
  id: number;
  origem_id: number;
  destino_id: number;
  origem: string | null;
  contexto: string | null;
  data_indicacao: string;
}

export interface IndicacaoGraph {
  nodes: IndicacaoGraphNode[];
  edges: IndicacaoGraphEdge[];
  total_edges: number;
  truncated: boolean;
}

export interface IndicacaoGraphFilters {
  pessoa_id?: number;
  origem?: string;
  data_inicial?: string;
  data_final?: string;
  profundidade?: number;
}
