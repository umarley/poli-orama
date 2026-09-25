export type RouteStatus = 'PLANEJADA' | 'LIBERADA' | 'EM_EXECUCAO' | 'CONCLUIDA' | 'CANCELADA';

export type PointStatus =
  | 'PENDENTE'
  | 'EM_EXECUCAO'
  | 'INSTALADO'
  | 'RECOLHIDO'
  | 'RECOLHIDO_PARCIALMENTE'
  | 'COM_EXTRAVIO'
  | 'NAO_EXECUTADO';

export interface MaterialRecord {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  nome: string;
  descricao: string | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface TeamMember {
  usuario_id: number;
  pessoa_id: number;
  nome: string;
  email: string;
}

export interface TeamRecord {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  nome: string;
  descricao: string | null;
  lideranca_id: number | null;
  territorio_id: number | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
  membros: TeamMember[];
}

export interface PointMaterial {
  id: number;
  material_id: number;
  material_nome: string;
  quantidade_planejada: number;
  quantidade_instalada: number;
  quantidade_recolhida: number;
  quantidade_extraviada: number;
  quantidade_pendente: number;
}

export interface Movement {
  id: number;
  uuid_publico: string;
  material_id: number;
  material_nome: string;
  tipo_movimentacao: 'INSTALACAO' | 'RECOLHIMENTO' | 'EXTRAVIO';
  quantidade: number;
  usuario_id: number;
  usuario_nome: string;
  latitude: string;
  longitude: string;
  observacao: string | null;
  registrado_em: string;
}

export interface ExecutionMedia {
  anexo_id: number;
  preview_url: string;
  download_url: string;
  criado_em: string;
  nome_original: string;
  mime_type: string | null;
  tipo: 'foto' | 'video';
}

export interface ExecutionHistory {
  id: number;
  uuid_publico: string;
  tipo_operacao: 'INSTALACAO' | 'RETIRADA';
  usuario_id: number;
  usuario_nome: string;
  latitude: string;
  longitude: string;
  precisao: string | null;
  observacao: string | null;
  executado_em: string;
  foto: {
    anexo_id: number;
    preview_url: string;
    download_url: string;
    criado_em: string;
  } | null;
  midias: ExecutionMedia[];
  movimentacoes: Movement[];
}

export interface RoutePoint {
  id: number;
  uuid_publico: string;
  ordem: number;
  descricao_local: string;
  endereco: string | null;
  latitude_planejada: string | null;
  longitude_planejada: string | null;
  observacao: string | null;
  status: PointStatus;
  materiais: PointMaterial[];
  historico: ExecutionHistory[];
}

export interface RouteRecord {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  rota_id: number;
  rota_uuid: string;
  nome: string;
  descricao: string | null;
  data_execucao: string;
  status: RouteStatus;
  observacao: string | null;
  equipe_id: number | null;
  equipe_nome: string | null;
  usuario_responsavel_id: number | null;
  usuario_responsavel_nome: string | null;
  territorio_id: number | null;
  territorio_nome: string | null;
  total_pontos: number;
  pontos_concluidos: number;
  pontos_pendentes: number;
  criado_em: string;
  atualizado_em: string;
}

export interface RouteDetail extends RouteRecord {
  pontos: RoutePoint[];
}

export interface PointInput {
  ordem: number;
  descricao_local: string;
  endereco?: string;
  latitude_planejada?: number;
  longitude_planejada?: number;
  observacao?: string;
  materiais: Array<{ material_id: number; quantidade_planejada: number }>;
}

export interface RouteInput {
  rota_id: number;
  data_execucao: string;
  equipe_id?: number;
  usuario_responsavel_id?: number;
  observacao?: string;
  status?: RouteStatus;
}

export interface RouteTemplateMaterial {
  id: number;
  material_id: number;
  material_nome: string;
  quantidade_planejada: number;
}

export interface RouteTemplatePoint extends Omit<RoutePoint, 'status' | 'materiais' | 'historico'> {
  materiais: RouteTemplateMaterial[];
}

export interface RouteTemplateRecord {
  id: number;
  uuid_publico: string;
  tenant_id: number;
  nome: string;
  descricao: string | null;
  territorio_id?: number;
  territorio_nome: string | null;
  ativo: boolean;
  total_pontos: number;
  criado_em: string;
  atualizado_em: string;
}

export interface RouteTemplateDetail extends RouteTemplateRecord {
  pontos: RouteTemplatePoint[];
}

export interface RouteTemplateInput {
  nome: string;
  descricao?: string;
  territorio_id?: number;
  ativo?: boolean;
  pontos: PointInput[];
}

export interface DashboardData {
  totais: {
    rotas_programadas: number;
    rotas_iniciadas: number;
    rotas_concluidas: number;
    pontos_planejados: number;
    pontos_executados: number;
    pontos_pendentes: number;
    materiais_instalados: number;
    materiais_recolhidos: number;
    materiais_extraviados: number;
    taxa_extravio: string;
  };
  por_material: Array<{
    chave: string;
    nome: string;
    instalado: number;
    recolhido: number;
    extraviado: number;
  }>;
  pontos: Array<{
    uuid_publico: string;
    descricao_local: string;
    endereco: string | null;
    latitude_planejada: string | null;
    longitude_planejada: string | null;
    status: PointStatus;
    rota_nome: string;
    equipe_nome: string | null;
    usuario_nome: string | null;
    executor_nome: string | null;
    executado_em: string | null;
    latitude_execucao: string | null;
    longitude_execucao: string | null;
    anexo_id: number | null;
    materiais: string | null;
    instalado: number;
    recolhido: number;
    extraviado: number;
  }>;
}

export interface PollingPlaceMapItem {
  id: number;
  nome: string;
  endereco: string | null;
  latitude: string;
  longitude: string;
  municipio: string;
  numero_zona: number | null;
}

export interface PollingPlaceSectionItem {
  id: number;
  numero_secao: number;
  agregada_em: number | null;
}
